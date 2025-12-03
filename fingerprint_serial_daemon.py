# url=https://github.com/owner/repo/blob/main/fingerprint_serial_daemon.py
"""
Fingerprint serial daemon (updated to avoid Arduino auto-reset / timing issues)
- Waits after opening serial so the Arduino sketch can boot
- Ensures DTR is cleared to avoid triggering reset behavior
- Sends ENROLL commands with CR+LF and logs DEBUG messages
Run with:
  pip install fastapi uvicorn pyserial
  uvicorn fingerprint_serial_daemon:app --host 127.0.0.1 --port 5001
"""
import threading
import time
import uuid
import json
import queue
import re
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

try:
    import serial
except Exception:
    serial = None

# === CONFIG ===
SERIAL_PORT = "COM5"
SERIAL_BAUD = 9600
SERIAL_READ_TIMEOUT = 1
ENROLL_RESPONSE_TIMEOUT = 180
IDENTIFY_TIMEOUT = 30
DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 5001
ALLOWED_ORIGINS = ["http://127.0.0.1:8000", "http://localhost:8000"]
# ==============

app = FastAPI(title="Fingerprint Serial Daemon (SSE + Identify)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

jobs = {}
jobs_lock = threading.Lock()


def open_serial():
    if serial is None:
        raise RuntimeError("pyserial is not installed (pip install pyserial)")
    try:
        # Open port
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=SERIAL_READ_TIMEOUT)
        # Prevent Arduino auto-reset impact:
        # - Clear DTR line immediately after opening to avoid toggling the bootloader/reset
        # - Wait a short time to let the sketch initialize and print its startup text
        try:
            # Clear DTR/RTS to be safe; some boards use these lines
            ser.setDTR(False)
            ser.setRTS(False)
        except Exception:
            # not all pyserial versions/hardware support setRTS/setDTR
            try:
                ser.dtr = False
            except Exception:
                pass
        # Wait for Arduino boot/initialization (1.5..3s depending on board). Conservative default:
        time.sleep(2.5)
        # Flush any initial output
        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except Exception:
            pass
        return ser
    except Exception as e:
        raise RuntimeError(f"cannot open serial port: {e}")


def _enqueue(job_id, line):
    with jobs_lock:
        q = jobs.get(job_id)
    if q:
        q.put(line)


def enroll_job(job_id: str, slot: int):
    """
    Background enrollment job: writes ENROLL <slot>, forwards device lines to the job queue,
    and returns a final 'done' JSON message.
    """
    try:
        ser = open_serial()
    except Exception as e:
        _enqueue(job_id, json.dumps({"type": "error", "text": f"cannot_open_serial:{e}"}))
        _enqueue(job_id, json.dumps({"type": "done", "success": False}))
        return

    try:
        # ensure buffers cleared after the boot wait
        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except Exception:
            pass

        # Use CR+LF as many Arduino sketches expect that; include DEBUG enqueue
        cmd = f"ENROLL {slot}\r\n"
        try:
            ser.write(cmd.encode())
            _enqueue(job_id, json.dumps({"type": "message", "text": f"DEBUG: sent command: {cmd.strip()}"}))
        except Exception as e:
            _enqueue(job_id, json.dumps({"type": "error", "text": f"serial_write_error:{e}"}))
            _enqueue(job_id, json.dumps({"type": "done", "success": False}))
            try:
                ser.close()
            except Exception:
                pass
            return

        end_time = time.time() + ENROLL_RESPONSE_TIMEOUT
        while time.time() < end_time:
            try:
                raw = ser.readline().decode(errors="ignore").strip()
            except Exception:
                raw = ""
            if not raw:
                continue
            _enqueue(job_id, json.dumps({"type": "message", "text": raw}))
            up = raw.upper()

            # success messages
            if up.startswith("ENROLLED:"):
                try:
                    rslot = int(raw.split(":", 1)[1].strip())
                    _enqueue(job_id, json.dumps({"type": "done", "success": True, "slot": rslot}))
                    try:
                        ser.close()
                    except Exception:
                        pass
                    return
                except Exception:
                    _enqueue(job_id, json.dumps({"type": "error", "text": "malformed_enrolled_response"}))
                    _enqueue(job_id, json.dumps({"type": "done", "success": False}))
                    try:
                        ser.close()
                    except Exception:
                        pass
                    return
            if "STORED ID #" in up:
                try:
                    part = raw.split("#")[-1].strip()
                    rslot = int(part)
                    _enqueue(job_id, json.dumps({"type": "done", "success": True, "slot": rslot}))
                    try:
                        ser.close()
                    except Exception:
                        pass
                    return
                except Exception:
                    pass

            # device error
            if up.startswith("ERROR:"):
                msg = raw.split(":", 1)[1].strip() if ":" in raw else raw
                _enqueue(job_id, json.dumps({"type": "error", "text": msg}))
                _enqueue(job_id, json.dumps({"type": "done", "success": False}))
                try:
                    ser.close()
                except Exception:
                    pass
                return

        # timeout
        _enqueue(job_id, json.dumps({"type": "error", "text": "timeout_waiting_for_device"}))
        _enqueue(job_id, json.dumps({"type": "done", "success": False}))
        try:
            ser.close()
        except Exception:
            pass
    except Exception as e:
        try:
            ser.close()
        except Exception:
            pass
        _enqueue(job_id, json.dumps({"type": "error", "text": f"internal_error:{e}"}))
        _enqueue(job_id, json.dumps({"type": "done", "success": False}))


@app.post("/enroll_start")
def enroll_start(slot: Optional[int] = None):
    chosen_slot = slot if slot else 1
    job_id = str(uuid.uuid4())
    q = queue.Queue()
    with jobs_lock:
        jobs[job_id] = q
    th = threading.Thread(target=enroll_job, args=(job_id, chosen_slot), daemon=True)
    th.start()
    events_url = f"http://{DAEMON_HOST}:{DAEMON_PORT}/events/{job_id}"
    return JSONResponse({"job_id": job_id, "events_url": events_url})


@app.get("/events/{job_id}")
def events(job_id: str):
    with jobs_lock:
        q = jobs.get(job_id)
    if q is None:
        raise HTTPException(status_code=404, detail="job_not_found")

    def event_generator():
        done = False
        while not done:
            try:
                item = q.get(timeout=1.0)
            except queue.Empty:
                yield ":\n\n"
                continue
            yield f"data: {item}\n\n"
            try:
                parsed = json.loads(item)
                if parsed.get("type") == "done":
                    done = True
            except Exception:
                pass
        with jobs_lock:
            jobs.pop(job_id, None)
        return

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/identify")
def identify():
    try:
        ser = open_serial()
    except Exception as e:
        return JSONResponse({"success": False, "error": f"cannot_open_serial:{e}"}, status_code=500)

    try:
        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except Exception:
            pass

        cmds_to_try = ["SEARCH\r\n", "IDENTIFY\r\n", "VERIFY\r\n"]
        sent = False
        for cmd in cmds_to_try:
            try:
                ser.write(cmd.encode())
                sent = True
                break
            except Exception:
                sent = False
        if not sent:
            ser.close()
            return JSONResponse({"success": False, "error": "serial_write_failed"}, status_code=500)

        end_time = time.time() + IDENTIFY_TIMEOUT
        matched_slot = None
        while time.time() < end_time:
            try:
                raw = ser.readline().decode(errors="ignore").strip()
            except Exception:
                raw = ""
            if not raw:
                continue
            up = raw.upper()
            if any(token in up for token in ("FOUND ID", "STORED ID", "MATCHED", "ID #", "ID:")):
                m = re.search(r"#\s*(\d+)|ID[:#]?\s*(\d+)|MATCHED[:#]?\s*(\d+)|FOUND[:#]?\s*(\d+)", raw, re.IGNORECASE)
                if m:
                    for g in m.groups():
                        if g:
                            try:
                                matched_slot = int(g)
                                break
                            except Exception:
                                continue
                if matched_slot is not None:
                    ser.close()
                    return JSONResponse({"success": True, "slot": matched_slot})
            if "NO MATCH" in up or "NOT FOUND" in up or "NOT MATCH" in up:
                ser.close()
                return JSONResponse({"success": False, "error": "no_match"})
        ser.close()
        return JSONResponse({"success": False, "error": "timeout_no_match"})
    except Exception as e:
        try:
            ser.close()
        except Exception:
            pass
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/status")
def status():
    try:
        ser = open_serial()
        try:
            ser.close()
        except Exception:
            pass
        return {"ok": True, "port": SERIAL_PORT, "baud": SERIAL_BAUD}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
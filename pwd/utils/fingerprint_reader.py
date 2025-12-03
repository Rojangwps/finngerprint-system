# pwd/utils/fingerprint_reader.py
import time
from django.conf import settings

try:
    import serial
except Exception:
    serial = None

SERIAL_TIMEOUT = 60  # seconds to wait for ENROLLED reply


def _open_serial():
    port = getattr(settings, "FINGERPRINT_SERIAL_PORT", None)
    baud = getattr(settings, "FINGERPRINT_BAUD", 9600)
    if not port:
        return None, "FINGERPRINT_SERIAL_PORT not set in settings"
    if serial is None:
        return None, "pyserial not installed (pip install pyserial)"
    try:
        s = serial.Serial(port, baud, timeout=1)
        # small delay to allow Arduino to reset if connecting
        time.sleep(0.5)
        s.reset_input_buffer()
        s.reset_output_buffer()
        return s, None
    except Exception as e:
        return None, f"cannot open serial port: {e}"


def _find_free_slot():
    """
    Find first free slot between 1..200 not already assigned to a PWDProfile.fingerprint_slot.
    Import the model here (inside the function) to avoid import-time errors during Django startup.
    """
    try:
        # import here to avoid circular import / app registry issues at module import time
        from pwd.models import PWDProfile
    except Exception as e:
        # If models cannot be imported (startup), raise a clear error to logs
        return None

    used = set(
        PWDProfile.objects
        .exclude(fingerprint_slot__isnull=True)
        .values_list("fingerprint_slot", flat=True)
    )
    for i in range(1, 201):
        if i not in used:
            return i
    return None


def register_fingerprint():
    """
    Orchestrates remote enrollment:
    - picks a free slot (1..200)
    - sends "ENROLL <slot>\n" to Arduino on configured serial port
    - waits up to SERIAL_TIMEOUT seconds for "ENROLLED:<slot>" line
    Returns (True, slot) on success, or (False, error_message) on failure.
    """
    slot = _find_free_slot()
    if slot is None:
        return False, "no_free_slots_or_models_unavailable"

    ser, err = _open_serial()
    if ser is None:
        return False, err

    try:
        cmd = f"ENROLL {slot}\n"
        ser.write(cmd.encode())
    except Exception as e:
        try:
            ser.close()
        except Exception:
            pass
        return False, f"serial_write_error:{e}"

    # wait for response
    start = time.time()
    try:
        while time.time() - start < SERIAL_TIMEOUT:
            try:
                line = ser.readline().decode(errors="ignore").strip()
            except Exception:
                line = ""
            if not line:
                continue
            # Accept lines like ENROLLED:10 or Stored ID #10 or ERROR:...
            up = line.upper()
            if up.startswith("ENROLLED:"):
                try:
                    rslot = int(line.split(":", 1)[1].strip())
                    ser.close()
                    # if device returned different slot we still return it
                    return True, rslot
                except Exception:
                    ser.close()
                    return False, "malformed_enrolled_response"
            if "STORED ID #" in up:
                # parse numeric after '#'
                try:
                    part = line.split("#")[-1].strip()
                    rslot = int(part)
                    ser.close()
                    return True, rslot
                except Exception:
                    pass
            if up.startswith("ERROR:"):
                err_msg = line.split(":", 1)[1].strip()
                ser.close()
                return False, f"device_error:{err_msg}"
        # timeout
        ser.close()
        return False, "timeout_waiting_for_device"
    except Exception as e:
        try:
            ser.close()
        except Exception:
            pass
        return False, f"serial_read_error:{e}"
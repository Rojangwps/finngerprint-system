import serial
import time

ARDUINO_PORT = 'COM5'  # change if different
BAUD_RATE = 9600
TIMEOUT = 5  # seconds

def send_command(command):
    """Send command to Arduino and return response"""
    try:
        arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=TIMEOUT)
        time.sleep(2)  # wait for Arduino reset
        arduino.flushInput()
        arduino.write(f"{command}\n".encode())

        while True:
            if arduino.in_waiting > 0:
                line = arduino.readline().decode().strip()
                if line:
                    arduino.close()
                    return line
    except Exception as e:
        return f"ERROR: {e}"

def register_fingerprint():
    """Enroll a new fingerprint"""
    result = send_command("REGISTER")
    return result == "SUCCESS"

def scan_fingerprint():
    """Scan fingerprint and return matched ID, or None"""
    result = send_command("SCAN")
    if result.startswith("MATCH:"):
        return int(result.split(":")[1])
    elif result == "NO_MATCH":
        return None
    else:
        return None

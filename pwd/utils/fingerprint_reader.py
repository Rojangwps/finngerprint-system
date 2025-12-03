import serial
import time

# Configure your Arduino COM port and baud rate
ARDUINO_PORT = 'COM5'  # Change if needed
BAUD_RATE = 9600

def register_fingerprint(timeout=15):
    """
    Registers a fingerprint using Arduino.
    Returns True if registration succeeds, False otherwise.
    """
    try:
        with serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=timeout) as ser:
            time.sleep(2)  # wait for Arduino to initialize

            # Send register command
            ser.write(b'REGISTER\n')

            # Wait for response from Arduino
            start_time = time.time()
            while True:
                if ser.in_waiting:
                    response = ser.readline().decode().strip()
                    if response == "SUCCESS":
                        return True
                    else:
                        return False

                if time.time() - start_time > timeout:
                    return False

    except serial.SerialException as e:
        print(f"[Fingerprint Error] Serial connection failed: {e}")
        return False
    except Exception as e:
        print(f"[Fingerprint Error] Unexpected error: {e}")
        return False

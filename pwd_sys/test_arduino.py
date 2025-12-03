import serial
import time

ARDUINO_PORT = 'COM5'   # <-- update to COM5
BAUD_RATE = 9600

try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=5)
    time.sleep(2)  # wait for Arduino to reset
    print("Connected successfully to Arduino on COM5!")
    arduino.close()
except Exception as e:
    print("Error connecting to Arduino:", e)

import serial
import time
import random

# Sample words to build a paragraph
words = [
    "vehicle", "system", "sensor", "encryption", "network", "message", "CAN", "bus",
    "protocol", "ESP32", "data", "transmit", "secure", "communication", "broadcast",
    "control", "alert", "alarm", "keyless", "entry", "firmware", "monitor", "decode",
    "hardware", "software", "packet", "frame", "logic", "signal", "authentication"
]

# Generate a paragraph of words under 1024 bytes
paragraph = ""
while len(paragraph.encode()) < 1024:
    next_word = random.choice(words)
    if len((paragraph + " " + next_word).encode()) > 1024:
        break
    paragraph += " " + next_word if paragraph else next_word

# Convert to bytes
data_to_send = paragraph.encode()

# Setup serial connection
ser = serial.Serial(port='COM13', baudrate=115200, timeout=1)
time.sleep(2)  # Wait for device to reset

# Send data
ser.write(data_to_send)
ser.write(b'\r\n')  # Optional: mark end of message

print(f"Sent paragraph with {len(data_to_send)} bytes.")

ser.close()

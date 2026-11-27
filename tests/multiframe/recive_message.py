import serial
import json
import textwrap
import shutil

# Adjust these to your serial port and baud rate
SERIAL_PORT = 'COM13'
BAUD_RATE    = 115200
TIMEOUT      = 1  # seconds

def wrap(text):
    cols = shutil.get_terminal_size().columns or 80
    return textwrap.fill(text, width=cols)

def main():
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT) as ser:
        print(f"Listening on {SERIAL_PORT} at {BAUD_RATE} baud...\nPress Ctrl-C to exit.\n")
        while True:
            try:
                raw = ser.readline().decode('utf-8', errors='ignore').strip()
                if not raw:
                    continue

                # 1) Show the raw JSON (wrapped if too long)
                print("Message Recived via COM serial port")
                print(wrap(raw))

                # 2) Parse and decode
                msg = json.loads(raw)
                hex_data = msg.get('data', '')
                decoded = bytes.fromhex(hex_data).decode('utf-8', errors='replace')

                # 3) Show the decoded payload
                print("decoded string")
                print(decoded)
                print()  # blank line between messages

            except json.JSONDecodeError:
                print(f"[!] Invalid JSON received: {raw}\n")
            except KeyboardInterrupt:
                print("\nExiting.")
                break

if __name__ == '__main__':
    main()

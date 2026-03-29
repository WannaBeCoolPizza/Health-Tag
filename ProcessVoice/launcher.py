"""
launcher.py

Lightweight always-on listener.
When the GPIO 35 button on the ESP32 is pressed, it sends LAUNCH_APP over
serial and this script spawns processvoice.py.

Run on Windows startup:
    pythonw ProcessVoice\launcher.py COM7

Or with the venv:
    .venv\Scripts\pythonw ProcessVoice\launcher.py COM7
"""

import serial
import subprocess
import sys
import os
import time

BAUD_RATE = 460800

def main():
    if len(sys.argv) < 2:
        print("Usage: python launcher.py COM7")
        sys.exit(1)

    port = sys.argv[1]
    project_root = os.path.join(os.path.dirname(__file__), "..")
    project_root = os.path.abspath(project_root)

    python_exe = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable  # fallback to current interpreter

    script = os.path.join(project_root, "ProcessVoice", "processvoice.py")
    active_process = None

    print(f"Launcher ready on {port}. Press GPIO 35 button to start processvoice.")

    while True:
        try:
            with serial.Serial(port, BAUD_RATE, timeout=1) as ser:
                while True:
                    line = ser.readline().decode("utf-8", errors="replace").strip()
                    if not line:
                        continue

                    if line == "LAUNCH_APP":
                        # Don't launch a second instance if one is already running
                        if active_process and active_process.poll() is None:
                            print("processvoice.py is already running — ignoring.")
                            continue

                        print("LAUNCH_APP received — starting processvoice.py...")
                        active_process = subprocess.Popen(
                            [python_exe, "-u", script, port],
                            cwd=project_root,
                        )

        except serial.SerialException as e:
            print(f"Serial error: {e} — retrying in 3s...")
            time.sleep(3)
        except KeyboardInterrupt:
            print("Launcher stopped.")
            if active_process and active_process.poll() is None:
                active_process.terminate()
            break

if __name__ == "__main__":
    main()

"""
read_rfid_and_speak.py

What this does:
    1. Sends 'r' to the ESP32 over Serial to trigger an RFID read
    2. Captures the patient data printed back by the ESP32
    3. Sends it to Gemini AI for a clinical briefing
    4. Speaks the response out loud using pyttsx3
    5. Loops — ready for the next patient immediately

Usage:
    python read_rfid_and_speak.py COM7
"""

import serial
import time
import sys
import os
import pyttsx3
from google import genai

# ---------- SETTINGS ----------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL   = "gemini-2.0-flash"
BAUD_RATE      = 115200
READ_TIMEOUT   = 20       # seconds to wait for ESP32 to finish reading tag

AI_INSTRUCTIONS = """You are a clinical briefing assistant built into smart glasses
that a doctor wears. When given patient data, give a quick spoken briefing that
covers the most important things first.

Rules:
- Talk like a human, not a robot. This will be read out loud.
- Keep it under 30 seconds of speaking.
- Lead with the urgent stuff: severity, allergies, conditions, medications.
- Don't use bullet points or markdown. Just speak naturally.
- Start with the patient's name and ID."""


# ---------- CAPTURE SERIAL OUTPUT ----------

def read_patient_from_esp32(ser) -> str:
    """
    Sends 'r' to the ESP32 and captures everything it prints
    until the closing line (════) or timeout.
    """
    ser.reset_input_buffer()
    ser.write(b'r\n')
    print("Sent 'r'  waiting for ESP32 to scan tag...\n")

    captured = []
    deadline = time.time() + READ_TIMEOUT
    reading  = False

    while time.time() < deadline:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            if not line:
                continue

            print(f"ESP32: {line}")

            if "PATIENT RECORD" in line:
                reading = True

            if reading:
                captured.append(line)

            if reading and line.startswith("════"):
                break

    if not captured:
        print("No patient data received — did you place the tag on the reader?")
        return ""

    return "\n".join(captured)


# ---------- ASK GEMINI ----------

def ask_gemini(patient_text: str) -> str:
    """Send patient data to Gemini and get a spoken briefing back."""
    print("\nAsking Gemini for a briefing...")
    brain  = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"Here is the patient data read from their RFID tag:\n\n{patient_text}\n\nGive me a spoken clinical briefing."

    response = brain.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "system_instruction": AI_INSTRUCTIONS,
            "max_output_tokens": 500,
        }
    )
    return response.text


# ---------- SPEAK ----------

def speak(text: str):
    """Read text aloud using pyttsx3."""
    print(f"\nGemini says:\n\"{text}\"\n")
    print("Speaking...")
    mouth = pyttsx3.init()
    mouth.setProperty('rate', 165)
    mouth.setProperty('volume', 0.9)
    mouth.say(text)
    mouth.runAndWait()


# ---------- MAIN ----------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python read_rfid_and_speak.py <COM_PORT>")
        print("Example: python read_rfid_and_speak.py COM7")
        sys.exit(1)

    if not GEMINI_API_KEY:
        print("ERROR: Set the GEMINI_API_KEY environment variable before running.")
        sys.exit(1)

    port = sys.argv[1]
    print(f"=== RFID → AI Voice Briefing ===")
    print(f"Connecting to ESP32 on {port}...\n")

    with serial.Serial(port, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)  # wait for ESP32 reset after opening port
        print("Ready — place an RFID tag on the reader.\n")

        while True:
            patient_text = read_patient_from_esp32(ser)

            if patient_text:
                briefing = ask_gemini(patient_text)
                speak(briefing)
                print("\n--- Ready for next patient ---\n")
            else:
                # No tag detected this round, pause before retrying
                time.sleep(1)

"""
processvoice.py

Unified script — voice assistant + RFID card writer.

Voice mode (default):
    python ProcessVoice/processvoice.py COM7
    Hold the button on the ESP32 to record from your laptop mic.
    Scan a card to get an automatic patient briefing.

Write mode (program RFID cards):
    python ProcessVoice/processvoice.py COM7 --write
    Iterates through all patient .txt files and writes each one to a card.

Patient files: RFID Code/patients/
"""

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import whisper
from google import genai
import pyttsx3
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import serial
import struct
import glob
import threading
import tempfile
import time
import sys
import re


# ---------- SETTINGS ----------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable not set")
GEMINI_MODEL   = "gemini-2.0-flash"
WHISPER_MODEL  = "base"
SAMPLE_RATE    = 16000
BAUD_RATE      = 460800

PATIENT_FILES_FOLDER = os.path.join(os.path.dirname(__file__), "..", "RFID Code", "patients")

AI_INSTRUCTIONS = """You are a clinical briefing assistant built into smart glasses
that a doctor wears. When the doctor asks about a patient, give a quick spoken
briefing that covers the most important things first.

Rules:
- Talk like a human, not a robot. This will be read out loud.
- Keep it under 30 seconds of speaking.
- Lead with the urgent stuff: severity, allergies, conditions, medications.
- Don't use bullet points or markdown. Just speak naturally.
- If the doctor asks a follow-up question, answer it directly and briefly."""

MAGIC = bytes([0xA5, 0x5A])


# ---------- PATIENT FILE PARSING (shared with RFID Code/RFID.py) ----------

def pad(s: str, length: int) -> bytes:
    encoded = s.encode('utf-8')[:length]
    return encoded.ljust(length, b'\x00')

def xor_checksum(data: bytes) -> int:
    result = 0
    for b in data:
        result ^= b
    return result

def parse_patient_file(filepath: str) -> dict:
    patient = {
        'id': 0, 'name': '', 'dob': 0, 'visit': 0,
        'severity': 0, 'gender': 'U', 'height': 0.0,
        'weight': 0.0, 'bp': 0.0,
        'conditions': '', 'medications': '', 'family': '',
        'allergies': []
    }
    current_allergy = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or ':' not in line:
                continue
            key, _, val = line.partition(':')
            key = key.strip().lower()
            val = val.strip()

            if   key == 'id':          patient['id']         = int(val)
            elif key == 'name':        patient['name']        = val
            elif key == 'dob':         patient['dob']         = int(val)
            elif key == 'visit':       patient['visit']       = int(val)
            elif key == 'severity':    patient['severity']    = int(val)
            elif key == 'gender':      patient['gender']      = val[0].upper()
            elif key == 'height':      patient['height']      = float(val)
            elif key == 'weight':      patient['weight']      = float(val)
            elif key == 'bp':          patient['bp']          = float(val)
            elif key == 'conditions':  patient['conditions']  = val
            elif key == 'medications': patient['medications'] = val
            elif key == 'family':      patient['family']      = val
            elif key == 'allergy':
                name, _, sev = val.partition(',')
                current_allergy = {
                    'name': name.strip(),
                    'severity': int(sev.strip()) if sev.strip() else 0,
                    'symptoms': []
                }
                patient['allergies'].append(current_allergy)
            elif key == 'symptom' and current_allergy:
                current_allergy['symptoms'].append(val)

    return patient

def format_patient_for_gemini(p: dict) -> str:
    lines = [
        f"Patient ID: {p['id']}",
        f"Name: {p['name']}",
        f"DOB: {p['dob']}",
        f"Visit date: {p['visit']}",
        f"Severity: {p['severity']} / 5",
        f"Gender: {p['gender']}",
        f"Height: {p['height']} cm",
        f"Weight: {p['weight']} kg",
        f"Blood pressure: {p['bp']} mmHg",
        f"Conditions: {p['conditions']}",
        f"Medications: {p['medications']}",
        f"Family history: {p['family']}",
    ]
    if p['allergies']:
        lines.append("Allergies:")
        for a in p['allergies']:
            lines.append(f"  - {a['name']} (severity {a['severity']})"
                         + (f": {', '.join(a['symptoms'])}" if a['symptoms'] else ""))
    else:
        lines.append("Allergies: None on record")
    return "\n".join(lines)


# ---------- RFID CARD WRITING (from RFID Code/RFID.py) ----------

def encode_patient(p: dict) -> bytes:
    buf = bytearray()
    buf += MAGIC
    buf += struct.pack('>H', p['id'])
    buf += struct.pack('>I', p['dob'])
    buf += struct.pack('>I', p['visit'])
    buf += p['gender'].encode('ascii')[:1]
    buf += struct.pack('>H', int(p['height'] * 10))
    buf += struct.pack('>H', int(p['weight'] * 10))

    h_m = p['height'] / 100.0
    bmi = (p['weight'] / (h_m * h_m)) if h_m > 0 else 0.0
    buf += struct.pack('>H', int(bmi * 100))

    buf += struct.pack('>H', int(p['bp'] * 10))
    buf += struct.pack('B', p['severity'])
    buf += pad(p['name'],        32)
    buf += pad(p['conditions'],  32)
    buf += pad(p['medications'], 32)
    buf += pad(p['family'],      32)

    allergies = p['allergies'][:5]
    buf += struct.pack('B', len(allergies))
    for a in allergies:
        buf += pad(a['name'], 16)
        buf += struct.pack('B', a['severity'])
        symptoms = a['symptoms'][:5]
        buf += struct.pack('B', len(symptoms))
        for s in symptoms:
            buf += pad(s, 16)
        for _ in range(5 - len(symptoms)):
            buf += b'\x00' * 16
    for _ in range(5 - len(allergies)):
        buf += b'\x00' * (16 + 1 + 1 + 5 * 16)

    buf += struct.pack('B', xor_checksum(buf))
    return bytes(buf)

def send_to_esp32(packet: bytes, port: str):
    with serial.Serial(port, BAUD_RATE, timeout=5) as ser:
        time.sleep(2)
        frame = struct.pack('>I', len(packet)) + packet
        ser.write(frame)
        print(f"  Sent {len(frame)} bytes")
        deadline = time.time() + 10
        while time.time() < deadline:
            if ser.in_waiting:
                response = ser.readline().decode('utf-8', errors='replace').strip()
                print(f"  ESP32: {response}")
                if response.startswith("ACK") or response.startswith("ERR"):
                    break

def write_all_cards(port: str):
    files = sorted(glob.glob(os.path.join(PATIENT_FILES_FOLDER, '*.txt')))
    if not files:
        print(f"No .txt files found in {os.path.abspath(PATIENT_FILES_FOLDER)}")
        return

    print(f"Found {len(files)} patient file(s).\n")
    for filepath in files:
        patient = parse_patient_file(filepath)
        packet  = encode_patient(patient)
        print(f"Patient ID {patient['id']} — {patient['name']}  ({len(packet)} bytes)")
        print("  >>> Place RFID tag on reader, then press Enter...")
        input()
        send_to_esp32(packet, port)

    print("\nAll cards written.")


# ---------- RECORD WHILE BUTTON HELD ----------

def record_from_mic(ser) -> str:
    frames = []
    stop_event = threading.Event()

    def capture():
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16') as stream:
            while not stop_event.is_set():
                data, _ = stream.read(1024)
                frames.append(data.copy())

    print("Recording...")
    t = threading.Thread(target=capture, daemon=True)
    t.start()

    while True:
        line = ser.readline().decode('utf-8', errors='replace').strip()
        if line == "RECORD_STOP":
            break

    stop_event.set()
    t.join()
    print("Recording stopped.")

    if not frames:
        return None

    audio = np.concatenate(frames, axis=0)
    wav_path = os.path.join(tempfile.gettempdir(), "doctor_recording.wav")
    wav.write(wav_path, SAMPLE_RATE, audio)
    return wav_path


# ---------- FIND PATIENT FILE ----------

def figure_out_which_patient(text: str) -> str:
    numbers = re.findall(r'\b\d+\b', text)
    for number in numbers:
        file_path = os.path.join(PATIENT_FILES_FOLDER, f"{number}.txt")
        if os.path.exists(file_path):
            print(f"Matched: {number} → {file_path}")
            return file_path

    text_lower = text.lower()
    if os.path.exists(PATIENT_FILES_FOLDER):
        for filename in os.listdir(PATIENT_FILES_FOLDER):
            if not filename.endswith(".txt"):
                continue
            file_path = os.path.join(PATIENT_FILES_FOLDER, filename)
            try:
                p = parse_patient_file(file_path)
                if p['name'] and any(
                    word in p['name'].lower()
                    for word in text_lower.split()
                    if len(word) > 2
                ):
                    print(f"Matched: name '{p['name']}' → {file_path}")
                    return file_path
            except Exception:
                continue

    print("No patient matched — treating as a follow-up question.")
    return None


# ---------- ASK GEMINI ----------

def ask_gemini(what_you_said: str, patient_file: str) -> str:
    brain = genai.Client(api_key=GEMINI_API_KEY)

    if patient_file:
        p = parse_patient_file(patient_file)
        patient_data = format_patient_for_gemini(p)
        message = f'The doctor said: "{what_you_said}"\n\nHere is the patient info:\n\n{patient_data}'
    else:
        message = f'The doctor said: "{what_you_said}"\n\n(Follow-up question about the same patient.)'

    response = brain.models.generate_content(
        model=GEMINI_MODEL,
        contents=message,
        config={
            "system_instruction": AI_INSTRUCTIONS,
            "max_output_tokens": 500,
        }
    )
    return response.text


# ---------- SPEAK ----------

def speak(text: str, ser=None):
    mouth = pyttsx3.init()
    mouth.setProperty('rate', 165)
    mouth.setProperty('volume', 0.9)
    mouth.say(text)
    mouth.runAndWait()


# ---------- MAIN ----------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Voice mode:  python ProcessVoice/processvoice.py COM7")
        print("  Write cards: python ProcessVoice/processvoice.py COM7 --write")
        sys.exit(1)

    port       = sys.argv[1]
    write_mode = "--write" in sys.argv

    print(f"=== Healthcare Badge ===")
    print(f"Patient files: {os.path.abspath(PATIENT_FILES_FOLDER)}")
    print(f"Port: {port}\n")

    if write_mode:
        print("=== WRITE MODE: programming RFID cards ===\n")
        write_all_cards(port)
    else:
        print("=== VOICE MODE: clinical assistant ===")
        ear = whisper.load_model(WHISPER_MODEL)
        print("Whisper loaded.\n")

        with serial.Serial(port, BAUD_RATE, timeout=1) as ser:
            print("Connected. Hold the button to ask a question | Scan a card for a briefing.\n")


            while True:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if not line:
                    continue

                # ── Button pressed: record voice question ──────────────────
                if line == "RECORD_START":
                    wav_path = record_from_mic(ser)
                    if not wav_path:
                        print("No audio captured.\n")
                        continue

                    print("Transcribing...")
                    result = ear.transcribe(wav_path, language="en")
                    what_you_said = result["text"].strip()
                    if not what_you_said:
                        print("Didn't catch anything.\n")
                        continue
                    print(f'You said: "{what_you_said}"\n')

                    patient_file = figure_out_which_patient(what_you_said)

                    print("Asking Gemini...")
                    briefing = ask_gemini(what_you_said, patient_file)
                    print(f'Gemini says: "{briefing}"\n')
                    speak(briefing, ser)

                # ── RFID card scanned: speak patient summary ───────────────
                elif line.startswith("PATIENT_ID:"):
                    patient_id = line.split(":", 1)[1].strip()
                    patient_file = os.path.join(PATIENT_FILES_FOLDER, f"{patient_id}.txt")
                    if not os.path.exists(patient_file):
                        print(f"No patient file found for ID {patient_id}\n")
                        continue

                    print(f"Card scanned — patient {patient_id}. Asking Gemini for briefing...")
                    briefing = ask_gemini("Give me a quick briefing on this patient.", patient_file)
                    print(f'Gemini says: "{briefing}"\n')
                    speak(briefing, ser)

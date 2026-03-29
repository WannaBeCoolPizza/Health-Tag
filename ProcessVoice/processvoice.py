"""
processvoice.py

Hold ENTER to record from your laptop mic, release to stop.
The AI figures out which patient you're asking about and speaks a briefing.

Usage:
    python ProcessVoice/processvoice.py

Patient files live in PatientFiles/ at the root of the repo.
Name them room1.txt, room2.txt, etc.

Install dependencies:
    pip install -r requirements.txt
"""

import whisper
from google import genai
import pyttsx3
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import threading
import tempfile
import os


# ---------- SETTINGS ----------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyC49mQtHi8bwhV1HhgBun6nncvCvpn7VY8")
GEMINI_MODEL   = "gemini-2.0-flash"
WHISPER_MODEL  = "base"
SAMPLE_RATE    = 16000

PATIENT_FILES_FOLDER = os.path.join(os.path.dirname(__file__), "..", "RFID Code", "Patients")

AI_INSTRUCTIONS = """You are a clinical briefing assistant built into smart glasses
that a doctor wears. When the doctor asks about a patient, give a quick spoken
briefing that covers the most important things first.

Rules:
- Talk like a human, not a robot. This will be read out loud.
- Keep it under 30 seconds of speaking.
- Lead with the urgent stuff: severity, allergies, conditions, medications.
- Don't use bullet points or markdown. Just speak naturally.
- If the doctor asks a follow-up question, answer it directly and briefly."""


# ---------- RECORD FROM LAPTOP MIC ----------

def record_from_mic() -> str:
    """
    Press ENTER to start recording, press ENTER again to stop.
    Returns path to a saved .wav file.
    """
    frames = []
    stop_event = threading.Event()

    def capture():
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16') as stream:
            while not stop_event.is_set():
                data, _ = stream.read(1024)
                frames.append(data.copy())

    input("Press ENTER to start recording...")
    print("Recording — press ENTER to stop.")

    t = threading.Thread(target=capture, daemon=True)
    t.start()
    input()
    stop_event.set()
    t.join()

    if not frames:
        return None

    audio = np.concatenate(frames, axis=0)
    wav_path = os.path.join(tempfile.gettempdir(), "doctor_recording.wav")
    wav.write(wav_path, SAMPLE_RATE, audio)
    return wav_path


# ---------- FIND PATIENT FILE ----------

def figure_out_which_patient(text: str) -> str:
    """
    Looks for any number spoken in the transcript and matches it to
    a file named {number}.txt in RFID_Code/Patients/.

    'Tell me about 1313'  → RFID_Code/Patients/1313.txt
    'Brief me on patient 42' → RFID_Code/Patients/42.txt
    'Tell me about Jane'  → searches all files for the name Jane
    """
    import re

    # Extract all digit sequences from the transcript
    numbers = re.findall(r'\b\d+\b', text)
    for number in numbers:
        file_path = os.path.join(PATIENT_FILES_FOLDER, f"{number}.txt")
        if os.path.exists(file_path):
            print(f"Matched: {number} → {file_path}")
            return file_path

    # Fall back to searching by patient name
    text_lower = text.lower()
    if os.path.exists(PATIENT_FILES_FOLDER):
        for filename in os.listdir(PATIENT_FILES_FOLDER):
            if not filename.endswith(".txt"):
                continue
            file_path = os.path.join(PATIENT_FILES_FOLDER, filename)
            with open(file_path, "r") as f:
                contents = f.read().lower()
            for word in text_lower.split():
                if len(word) > 2 and word in contents:
                    for line in contents.split("\n"):
                        if line.startswith("name:") and word in line:
                            print(f"Matched: name '{word}' → {file_path}")
                            return file_path

    print("No patient matched — treating as a follow-up question.")
    return None


# ---------- ASK GEMINI ----------

def ask_gemini(what_you_said: str, patient_file: str) -> str:
    brain = genai.Client(api_key=GEMINI_API_KEY)

    if patient_file:
        with open(patient_file, "r") as f:
            patient_data = f.read()
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

def speak(text: str):
    print(f'\nGemini says:\n"{text}"\n')
    mouth = pyttsx3.init()
    mouth.setProperty('rate', 165)
    mouth.setProperty('volume', 0.9)
    mouth.say(text)
    mouth.runAndWait()


# ---------- MAIN LOOP ----------

if __name__ == "__main__":
    print("=== Clinical Voice Assistant ===")
    print(f"Patient files: {os.path.abspath(PATIENT_FILES_FOLDER)}\n")

    ear = whisper.load_model(WHISPER_MODEL)
    print("Whisper loaded. Ready.\n")

    while True:
        wav_path = record_from_mic()
        if not wav_path:
            print("No audio captured, try again.\n")
            continue

        print("Transcribing...")
        result = ear.transcribe(wav_path, language="en")
        what_you_said = result["text"].strip()
        if not what_you_said:
            print("Didn't catch anything, try again.\n")
            continue
        print(f'You said: "{what_you_said}"\n')

        patient_file = figure_out_which_patient(what_you_said)

        print("Asking Gemini...")
        briefing = ask_gemini(what_you_said, patient_file)

        speak(briefing)
        print()

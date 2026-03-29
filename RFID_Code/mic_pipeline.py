"""
mic_pipeline.py

What this does:
    1. Listens on the mic ESP32's COM port
    2. When you hold the button, receives raw PCM audio
    3. Saves it as a .wav file
    4. Runs it through Whisper (speech-to-text)
    5. Sends transcript + patient context to Gemini
    6. Speaks the response aloud with pyttsx3

Usage:
    python mic_pipeline.py <MIC_COM_PORT> [PATIENT_FILE]

Examples:
    python mic_pipeline.py COM8
    python mic_pipeline.py COM8 Patients/room1.txt
"""

import serial
import wave
import struct
import sys
import os
import time
import tempfile
import whisper
import pyttsx3
from google import genai

# ---------- SETTINGS ----------
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "AIzaSyC49mQtHi8bwhV1HhgBun6nncvCvpn7VY8")
GEMINI_MODEL    = "gemini-2.0-flash"
WHISPER_MODEL   = "base"
BAUD_RATE       = 921600   # must match mic_sender.ino
SAMPLE_RATE     = 16000
CHANNELS        = 1
SAMPLE_WIDTH    = 2        # 16-bit = 2 bytes

START_MARKER    = bytes([0xAA, 0xBB, 0xCC, 0xDD])
END_MARKER      = bytes([0xDD, 0xCC, 0xBB, 0xAA])

AI_INSTRUCTIONS = """You are a clinical briefing assistant built into smart glasses
that a doctor wears. Answer the doctor's question using the patient data provided.

Rules:
- Talk like a human, not a robot. This will be read out loud.
- Keep it under 30 seconds of speaking.
- Lead with the urgent stuff: severity, allergies, conditions, medications.
- Don't use bullet points or markdown. Just speak naturally.
- If no patient file is provided, answer the question as a general medical assistant."""


# ---------- RECEIVE AUDIO FROM ESP32 ----------

def receive_audio(port: str) -> bytes:
    """
    Opens serial port and waits for the button to be pressed on the ESP32.
    Returns raw 16-bit PCM audio bytes.
    """
    print(f"Listening on {port} @ {BAUD_RATE} baud...")
    print("Hold the button on the ESP32 to record. Release when done.\n")

    with serial.Serial(port, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)
        ser.reset_input_buffer()

        # Wait for start marker
        print("Waiting for button press...")
        buf = bytearray()
        while True:
            byte = ser.read(1)
            if not byte:
                continue
            buf.extend(byte)

            # Keep only last 4 bytes for marker detection
            if len(buf) > 4:
                buf = buf[-4:]

            if bytes(buf) == START_MARKER:
                print("Recording... (release button to stop)")
                break

        # Collect audio until end marker
        audio_buf  = bytearray()
        check_tail = bytearray()

        while True:
            chunk = ser.read(64)
            if not chunk:
                continue

            audio_buf.extend(chunk)
            check_tail.extend(chunk)

            # Only need to check the last few bytes for the end marker
            if len(check_tail) > 8:
                check_tail = check_tail[-8:]

            if END_MARKER in check_tail:
                # Trim the end marker from audio data
                end_idx = audio_buf.rfind(END_MARKER)
                audio_buf = audio_buf[:end_idx]
                print(f"Recording complete — {len(audio_buf)} bytes received")
                break

        return bytes(audio_buf)


# ---------- SAVE AS WAV ----------

def save_wav(pcm_data: bytes, filepath: str):
    """Save raw 16-bit PCM bytes as a proper .wav file."""
    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)
    print(f"Saved audio to {filepath}")


# ---------- WHISPER ----------

def transcribe(wav_path: str) -> str:
    """Run Whisper on the wav file and return the transcript."""
    print("Transcribing with Whisper...")
    model  = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(wav_path, language="en")
    text   = result["text"].strip()
    print(f"You said: \"{text}\"")
    return text


# ---------- GEMINI ----------

def ask_gemini(transcript: str, patient_file: str = None) -> str:
    """Send transcript + optional patient data to Gemini."""
    print("\nAsking Gemini...")

    if patient_file and os.path.exists(patient_file):
        with open(patient_file, 'r') as f:
            patient_data = f.read()
        prompt = f'The doctor said: "{transcript}"\n\nPatient data:\n{patient_data}'
    else:
        prompt = f'The doctor said: "{transcript}"'

    brain    = genai.Client(api_key=GEMINI_API_KEY)
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
        print("Usage: python mic_pipeline.py <MIC_COM_PORT> [PATIENT_FILE]")
        print("Example: python mic_pipeline.py COM8 Patients/room1.txt")
        sys.exit(1)

    mic_port     = sys.argv[1]
    patient_file = sys.argv[2] if len(sys.argv) > 2 else None

    print("=== Mic → Whisper → Gemini → Voice ===\n")

    # Step 1: Record
    pcm_data = receive_audio(mic_port)
    if not pcm_data:
        print("No audio received.")
        sys.exit(1)

    # Step 2: Save as WAV
    wav_path = os.path.join(tempfile.gettempdir(), "doctor_recording.wav")
    save_wav(pcm_data, wav_path)

    # Step 3: Transcribe
    transcript = transcribe(wav_path)
    if not transcript:
        print("Nothing recognized in the recording.")
        sys.exit(1)

    # Step 4: Ask Gemini
    briefing = ask_gemini(transcript, patient_file)

    # Step 5: Speak
    speak(briefing)

    print("\nDone!")

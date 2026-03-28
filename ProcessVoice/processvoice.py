"""
Clinical Briefing Glasses — Voice Pipeline (MongoDB Edition)
 
What this does:
    1. You give it an audio file (WAV or M4A)
    2. It figures out what you said (speech-to-text)
    3. It looks up the patient in MongoDB
    4. It sends your question + patient data to Gemini AI
    5. Your computer reads the response out loud
 
Install dependencies:
    pip install openai-whisper google-genai pyttsx3 torch pymongo
 
Setup:
    1. Install MongoDB and make sure it's running
    2. Run setup_database.py ONCE to populate the database
    3. Set your Gemini API key below
    4. Run: python processvoice.py recording.wav
"""
 
# ---------- IMPORTS ----------
import whisper
from google import genai
import pyttsx3
import sys
import os
from pymongo import MongoClient
 
 
# ---------- SETTINGS ----------
GEMINI_API_KEY = "AIzaSyC49mQtHi8bwhV1HhgBun6nncvCvpn7VY8"
GEMINI_MODEL = "gemini-2.0-flash"
WHISPER_MODEL = "base"
 
 
# ---------- CONNECT TO MONGODB ----------
# MongoClient connects to the database running on your computer
# "clinical_glasses" is the database name
# "patients" is the collection (like a table) inside it
 
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["clinical_glasses"]
patients_collection = db["patients"]
 
 
# ---------- AI INSTRUCTIONS ----------
AI_INSTRUCTIONS = """You are a clinical briefing assistant built into smart glasses
that a doctor wears. When the doctor asks about a patient, give a quick spoken
briefing that covers the most important things first.
 
Rules:
- Talk like a human, not a robot. This will be read out loud.
- Keep it under 30 seconds of speaking.
- Lead with the urgent stuff: overdue screenings, bad lab trends, red flags.
- Don't use bullet points or markdown. Just speak naturally.
- If the doctor asks a follow-up question, answer it directly and briefly."""
 
 
# ---------- HELPER FUNCTIONS ----------
 
def figure_out_which_patient(text):
    """
    Look at what the doctor said and search MongoDB for the matching patient.
 
    Checks for room numbers (including spoken words like "one")
    and patient names.
    """
    text_lower = text.lower()
 
    # Whisper sometimes writes "one" instead of "1", so handle both
    word_to_number = {
        "one": "1", "two": "2", "three": "3",
        "four": "4", "five": "5",
    }
 
    # Replace spoken numbers with digits
    for word, digit in word_to_number.items():
        text_lower = text_lower.replace(f"room {word}", f"room {digit}")
 
    # Search by room number
    # Example: "Brief me on room 1" → search for {"room": "room 1"}
    for i in range(1, 10):
        if f"room {i}" in text_lower:
            patient = patients_collection.find_one({"room": f"room {i}"})
            if patient:
                print(f"Matched: room {i} → {patient['name']} - processvoice.py:86")
                return patient
 
    # Search by patient name
    # MongoDB's $regex lets us search case-insensitively
    all_patients = patients_collection.find()
    for patient in all_patients:
        first_name = patient["name"].split()[0].lower()
        last_name = patient["name"].split()[1].lower()
        if first_name in text_lower or last_name in text_lower:
            print(f"Matched: {patient['name']} - processvoice.py:96")
            return patient
 
    print("No patient matched. Treating as a followup question. - processvoice.py:99")
    return None
 
 
def format_patient_info(patient):
    """
    Take a patient document from MongoDB and turn it into a readable
    summary for Gemini.
    """
    return f"""
Patient: {patient['name']}, {patient['age']} year old {patient['sex']}
Visit type: {patient['visit']}
Allergies: {', '.join(patient['allergies'])}
Medications: {', '.join(patient['medications'])}
Conditions: {', '.join(patient['conditions'])}
Recent vitals: {patient['vitals']}
Recent labs: {patient['labs']}
Overdue screenings: {patient['overdue_screenings']}
Last visit: {patient['last_visit']}
"""
 
 
# ---------- MAIN PIPELINE ----------
 
def process_audio(audio_file_path):
    """
    Takes an audio file and runs the full pipeline:
    listen → find patient in DB → ask Gemini → speak response
    """
 
    if not os.path.exists(audio_file_path):
        print(f"ERROR: File not found: {audio_file_path} - processvoice.py:130")
        return
 
    # Check that MongoDB has patients
    patient_count = patients_collection.count_documents({})
    if patient_count == 0:
        print("ERROR: No patients in the database! - processvoice.py:136")
        print("Run setup_database.py first to populate it. - processvoice.py:137")
        return
 
    print(f"\n{'='*50} - processvoice.py:140")
    print(f"Processing: {audio_file_path} - processvoice.py:141")
    print(f"Patients in database: {patient_count} - processvoice.py:142")
    print(f"{'='*50}\n - processvoice.py:143")
 
    # --- SPEECH TO TEXT ---
    print("Step 1: Listening to your recording... - processvoice.py:146")
    ear = whisper.load_model(WHISPER_MODEL)
    result = ear.transcribe(audio_file_path, language="en")
    what_you_said = result["text"].strip()
    print(f"You said: \"{what_you_said}\"\n - processvoice.py:150")
 
    if not what_you_said:
        print("Didn't catch anything. Try speaking louder. - processvoice.py:153")
        return
 
    # --- FIND THE PATIENT IN MONGODB ---
    print("Step 2: Searching the database for the patient... - processvoice.py:157")
    patient = figure_out_which_patient(what_you_said)
 
    # Build the message to send to Gemini
    if patient:
        message_to_ai = f'The doctor said: "{what_you_said}"\n\nHere is the patient info:\n{format_patient_info(patient)}'
    else:
        message_to_ai = f'The doctor said: "{what_you_said}"\n\n(This is a follow-up question about the same patient as before.)'
 
    # --- ASK GEMINI ---
    print("Step 3: Asking Gemini for a briefing...\n - processvoice.py:167")
    brain = genai.Client(api_key=GEMINI_API_KEY)
 
    response = brain.models.generate_content(
        model=GEMINI_MODEL,
        contents=message_to_ai,
        config={
            "system_instruction": AI_INSTRUCTIONS,
            "max_output_tokens": 500,
        }
    )
 
    ai_answer = response.text
    print(f"Gemini says:\n - processvoice.py:180")
    print(f"\"{ai_answer}\"\n - processvoice.py:181")
 
    # --- SPEAK IT OUT LOUD ---
    print("Step 4: Speaking the response out loud... - processvoice.py:184")
    mouth = pyttsx3.init()
    mouth.setProperty('rate', 165)
    mouth.setProperty('volume', 0.9)
    mouth.say(ai_answer)
    mouth.runAndWait()
 
    print("\nDone!\n - processvoice.py:191")
 
 
# ---------- RUN IT ----------
 
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print()
        print("Usage:  python  <your_recording.wav> - processvoice.py:199")
        print()
        print("Make sure you've run setup_database.py first! - processvoice.py:201")
        print()
    else:
        audio_path = sys.argv[1]
        process_audio(audio_path)
"""
Database Setup — Run this ONCE to create and populate the patient database.

This creates a MongoDB database called "clinical_glasses" with a 
"patients" collection containing our mock patient data.

Make sure MongoDB is running first, then run:
    python setup_database.py
"""

from pymongo import MongoClient

# Connect to MongoDB (default: localhost:27017)
client = MongoClient("mongodb://localhost:27017/")

# Create (or connect to) our database
db = client["clinical_glasses"]

# Create (or connect to) our patients collection
patients = db["patients"]

# Clear any existing data so we start fresh
patients.delete_many({})
print("Cleared existing patient data. - setup_database.py:24")

# Our mock patient records
patient_records = [
    {
        "room": "room 1",
        "name": "Sarah Chen",
        "age": 52,
        "sex": "Female",
        "visit": "Annual wellness exam",
        "allergies": ["Penicillin"],
        "medications": ["Metformin 500mg twice daily", "Lisinopril 10mg daily"],
        "conditions": ["Type 2 Diabetes", "High blood pressure"],
        "vitals": "BP trending up: 124/80 → 128/82 → 132/84 over past year. Weight up 6 lbs.",
        "labs": "A1C rose from 6.8% to 7.2%. Fasting glucose 142. LDL 130 (high). HDL 48 (low).",
        "overdue_screenings": "Mammogram (2 years overdue). Colonoscopy (never done, due at 50).",
        "last_visit": "January 2026 — had a cold, given azithromycin, resolved.",
        "captured_images": [],
    },
    {
        "room": "room 2",
        "name": "Michael Torres",
        "age": 67,
        "sex": "Male",
        "visit": "Annual wellness exam",
        "allergies": ["Sulfa drugs", "Iodine contrast dye"],
        "medications": ["Amlodipine 5mg daily", "Atorvastatin 40mg daily", "Aspirin 81mg daily"],
        "conditions": ["High blood pressure (Stage 2)", "High cholesterol", "Knee arthritis (both knees)"],
        "vitals": "BP 148/92 (high). Weight 210 lbs, stable.",
        "labs": "Creatinine 1.3 (mildly elevated, kidney function declining). PSA jumped from 2.1 to 3.8 (needs attention).",
        "overdue_screenings": "Lung CT screening (former smoker, 20+ pack-year history).",
        "last_visit": "February 2026 — knee pain worsening, referred to orthopedics.",
        "captured_images": [
            {"date": "2026-02-01", "location": "right knee", "note": "Mild swelling observed"},
        ],
    },
    {
        "room": "room 3",
        "name": "Emily Nakamura",
        "age": 34,
        "sex": "Female",
        "visit": "Annual wellness exam",
        "allergies": ["None"],
        "medications": ["Sertraline 50mg daily"],
        "conditions": ["Anxiety disorder"],
        "vitals": "BP 118/76 (normal). Weight 135 lbs. All good.",
        "labs": "Vitamin D low at 22 (should be 30+). Everything else normal.",
        "overdue_screenings": "Pap smear (3 years overdue).",
        "last_visit": "March 2025 — anxiety well managed, no medication changes.",
        "captured_images": [],
    },
]

# Insert all patients into the database
result = patients.insert_many(patient_records)
print(f"Inserted {len(result.inserted_ids)} patients into the database.\n - setup_database.py:79")

# Verify by reading them back
print("Patients in database: - setup_database.py:82")
print("" * 40)
for patient in patients.find():
    print(f"{patient['room']}: {patient['name']}, {patient['age']} {patient['sex']}  {patient['visit']} - setup_database.py:85")

print(f"\nDatabase: clinical_glasses - setup_database.py:87")
print(f"Collection: patients - setup_database.py:88")
print(f"\nSetup complete! You can now run processvoice.py - setup_database.py:89")
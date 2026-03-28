export const mockPatients = [
  {
    id: "PT-1001",
    rfid: "DR-SMITH",
    doctor: "Dr. Smith",
    roomId: "ROOM-1",
    patient: {
      name: "Sarah Chen",
      age: 42,
      sex: "Female",
      dob: "1983-07-18",
      mrn: "MRN-48219",
      allergies: ["None reported"],
      medications: ["Ibuprofen as needed"],
      history: "History of pleuritis 2 years ago"
    },
    conversationSummary: {
      chiefComplaint: "Sharp left-sided chest pain worsening with inhalation since this morning",
      visitType: "Urgent Care",
      onset: "This morning (~5 hours ago)",
      severity: "Moderate",
      symptoms: ["Sharp chest pain (left-sided)", "Shortness of breath", "Pain worsens with deep breathing"],
      patientQuestions: ["Could this be my heart?", "Can I get an EKG?"],
      requestedTreatment: "EKG / cardiac evaluation",
      keyNotes: "Patient is worried about a cardiac cause. Prior pleuritis may be relevant, but cardiac causes should be ruled out first."
    },
    previousDoctorNotes: [
      "Prior urgent care visit documented pleuritic chest pain with improvement on anti-inflammatory treatment.",
      "No prior cardiac history listed in the chart.",
      "Recommend reviewing previous imaging and discharge paperwork if available."
    ]
  },
  {
    id: "PT-1002",
    rfid: "DR-JONES",
    doctor: "Dr. Jones",
    roomId: "ROOM-2",
    patient: {
      name: "Michael Torres",
      age: 55,
      sex: "Male",
      dob: "1970-10-03",
      mrn: "MRN-59201",
      allergies: ["No known drug allergies"],
      medications: ["Lisinopril"],
      history: "Known hypertension"
    },
    conversationSummary: {
      chiefComplaint: "Annual physical with elevated home BP readings and recent insomnia",
      visitType: "Routine Checkup",
      onset: "Insomnia for about 1 month; recent elevated BP readings at home",
      severity: "Mild",
      symptoms: ["Early morning waking", "Blood pressure around 148/92 at home"],
      patientQuestions: ["Am I up to date on vaccines?"],
      requestedTreatment: "Vaccine review and blood pressure follow-up",
      keyNotes: "Patient feels mostly well but home readings suggest blood pressure may need closer review."
    },
    previousDoctorNotes: [
      "Last primary care follow-up noted controlled blood pressure on lisinopril.",
      "Counseled on home BP monitoring and reducing sodium intake.",
      "Vaccines were reviewed last year but records should be rechecked."
    ]
  },
  {
    id: "PT-1003",
    rfid: "A1B2C3D4",
    doctor: "Dr. Patel",
    roomId: "ROOM-3",
    patient: {
      name: "Emily Carter",
      age: 29,
      sex: "Female",
      dob: "1996-04-11",
      mrn: "MRN-77340",
      allergies: ["None reported"],
      medications: ["Acetaminophen", "Ibuprofen"],
      history: "Family history of migraines"
    },
    conversationSummary: {
      chiefComplaint: "Recurring right-sided throbbing headaches with light sensitivity and nausea",
      visitType: "Specialist Consult",
      onset: "2 months, around 3 to 4 times per week",
      severity: "Severe",
      symptoms: ["Right-sided throbbing headache", "Photophobia", "Nausea"],
      patientQuestions: ["Is this migraine?", "Is there a prescription medication that works better?"],
      requestedTreatment: "Migraine medication evaluation",
      keyNotes: "Pattern is consistent with migraine and OTC medications have not helped much."
    },
    previousDoctorNotes: [
      "Previous note mentioned headache diary was recommended.",
      "No neurologic deficits documented at last visit.",
      "Consider discussing abortive therapy and possible preventive treatment."
    ]
  }
];

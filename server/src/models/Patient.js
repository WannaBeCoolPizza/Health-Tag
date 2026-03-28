import mongoose from "mongoose";

const patientSchema = new mongoose.Schema(
  {
    id: { type: String, required: true, unique: true },
    rfid: { type: String, required: true, unique: true, uppercase: true, trim: true },
    doctor: { type: String, required: true },
    roomId: { type: String, required: true },
    patient: {
      name: { type: String, required: true },
      age: { type: Number, required: true },
      sex: { type: String, required: true },
      dob: { type: String, required: true },
      mrn: { type: String, required: true },
      allergies: { type: [String], default: [] },
      medications: { type: [String], default: [] },
      history: { type: String, default: "" }
    },
    conversationSummary: {
      chiefComplaint: { type: String, default: "" },
      visitType: { type: String, default: "" },
      onset: { type: String, default: "" },
      severity: { type: String, default: "" },
      symptoms: { type: [String], default: [] },
      patientQuestions: { type: [String], default: [] },
      requestedTreatment: { type: String, default: "" },
      keyNotes: { type: String, default: "" }
    },
    previousDoctorNotes: { type: [String], default: [] }
  },
  { timestamps: true }
);

export const Patient = mongoose.model("Patient", patientSchema);

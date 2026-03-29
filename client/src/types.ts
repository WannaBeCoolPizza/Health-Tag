export interface QuickRfidEntry {
  id: string;
  name: string;
  rfid: string;
}

export interface PatientInfo {
  name: string;
  age: number;
  sex: string;
  dob: string;
  mrn: string;
  allergies: string[];
  medications: string[];
  history: string;
}

export interface ConversationSummary {
  chiefComplaint: string;
  visitType: string;
  onset: string;
  severity: string;
  symptoms: string[];
  patientQuestions: string[];
  requestedTreatment: string;
  keyNotes: string;
}

export interface PatientRecord {
  id: string;
  rfid: string;
  doctor: string;
  roomId: string;
  patient: PatientInfo;
  conversationSummary: ConversationSummary;
  previousDoctorNotes: string[];
}

export interface WriterAllergy {
  name: string;
  severity: string;
  symptoms: string;
}

export interface PatientTxtPayload {
  id: string;
  rfid: string;
  name: string;
  dob: string;
  visit: string;
  severity: string;
  gender: string;
  height: string;
  weight: string;
  bp: string;
  conditions: string;
  medications: string;
  family: string;
  allergies: WriterAllergy[];
}

export interface PatientTxtResult {
  fileName: string;
  filePath: string;
  content: string;
}

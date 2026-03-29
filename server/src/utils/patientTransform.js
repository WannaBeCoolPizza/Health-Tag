function splitCsv(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function calculateAgeFromDob(dob) {
  const raw = String(dob || "").trim();
  if (!/^\d{8}$/.test(raw)) return 0;

  const year = Number(raw.slice(0, 4));
  const month = Number(raw.slice(4, 6));
  const day = Number(raw.slice(6, 8));
  const now = new Date();
  let age = now.getFullYear() - year;
  const hasBirthdayPassed =
    now.getMonth() + 1 > month ||
    (now.getMonth() + 1 === month && now.getDate() >= day);

  if (!hasBirthdayPassed) age -= 1;
  return Number.isFinite(age) && age > 0 ? age : 0;
}

export function buildPatientDocument(input) {
  const id = String(input.id || "").trim();
  const rfid = String(input.rfid || id).trim().toUpperCase();
  const name = String(input.name || "").trim();
  const dobRaw = String(input.dob || "").trim();
  const age = calculateAgeFromDob(dobRaw);
  const medications = splitCsv(input.medications);
  const conditions = splitCsv(input.conditions);
  const allergies = Array.isArray(input.allergies)
    ? input.allergies
        .map((entry) => String(entry?.name || "").trim())
        .filter(Boolean)
    : [];

  return {
    id,
    rfid,
    doctor: String(input.doctor || "Unassigned"),
    roomId: String(input.roomId || "UNASSIGNED"),
    patient: {
      name,
      age,
      sex: String(input.gender || input.sex || "").trim() || "Unknown",
      dob: dobRaw,
      mrn: String(input.mrn || `MRN-${id}`),
      allergies,
      medications,
      history: String(input.family || input.history || "").trim()
    },
    conversationSummary: {
      chiefComplaint: String(input.chiefComplaint || "").trim(),
      visitType: String(input.visitType || "RFID Intake").trim(),
      onset: String(input.onset || "").trim(),
      severity: String(input.severity || "").trim(),
      symptoms: splitCsv(input.symptoms),
      patientQuestions: splitCsv(input.patientQuestions),
      requestedTreatment: String(input.requestedTreatment || "").trim(),
      keyNotes:
        String(input.keyNotes || "").trim() ||
        (conditions.length ? `Conditions: ${conditions.join(", ")}` : "")
    },
    previousDoctorNotes: Array.isArray(input.previousDoctorNotes) ? input.previousDoctorNotes : []
  };
}

export function parseRfidTxtContent(content) {
  const fields = {};
  const allergyRows = [];
  let currentAllergy = null;

  String(content || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .forEach((line) => {
      const separator = line.indexOf(":");
      if (separator < 0) return;

      const key = line.slice(0, separator).trim().toLowerCase();
      const value = line.slice(separator + 1).trim();

      if (key === "allergy") {
        const [name, severity] = value.split(",").map((part) => part.trim());
        currentAllergy = { name: name || "", severity: severity || "", symptoms: [] };
        allergyRows.push(currentAllergy);
        return;
      }

      if (key === "symptom") {
        if (!currentAllergy) {
          currentAllergy = { name: "", severity: "", symptoms: [] };
          allergyRows.push(currentAllergy);
        }
        currentAllergy.symptoms.push(value);
        return;
      }

      fields[key] = value;
    });

  return {
    id: fields.id || "",
    rfid: fields.rfid || fields.id || "",
    name: fields.name || "",
    dob: fields.dob || "",
    visit: fields.visit || "",
    severity: fields.severity || "",
    gender: fields.gender || "",
    height: fields.height || "",
    weight: fields.weight || "",
    bp: fields.bp || "",
    conditions: fields.conditions || "",
    medications: fields.medications || "",
    family: fields.family || "",
    allergies: allergyRows,
    symptoms: "",
    doctor: fields.doctor || "",
    roomId: fields.room_id || fields.roomid || "",
    mrn: fields.mrn || ""
  };
}

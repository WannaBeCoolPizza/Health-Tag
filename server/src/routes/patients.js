import { Router } from "express";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Patient } from "../models/Patient.js";
import { mockPatients } from "../data/mockPatients.js";
import { syncTxtPatientsToMongo } from "../services/rfidTxtSync.js";
import { buildPatientDocument } from "../utils/patientTransform.js";

const router = Router();
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const txtOutputDir = path.resolve(__dirname, "../../../PatientFiles");

function isMongoConnected() {
  return Patient.db.readyState === 1;
}

function parseCsvInput(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .join(", ");
}

function buildPatientTxtContent(body) {
  const lines = [
    `id:${String(body.id || "").trim()}`,
    `name:${String(body.name || "").trim()}`,
    `dob:${String(body.dob || "").trim()}`,
    `visit:${String(body.visit || "").trim()}`,
    `severity:${String(body.severity || "").trim()}`,
    `gender:${String(body.gender || "").trim()}`,
    `height:${String(body.height || "").trim()}`,
    `weight:${String(body.weight || "").trim()}`,
    `bp:${String(body.bp || "").trim()}`,
    `conditions:${parseCsvInput(body.conditions)}`,
    `medications:${parseCsvInput(body.medications)}`,
    `family:${String(body.family || "").trim()}`
  ];

  const allergyRows = Array.isArray(body.allergies) ? body.allergies : [];
  allergyRows.forEach((row) => {
    const allergyName = String(row?.name || "").trim();
    const allergySeverity = String(row?.severity || "").trim();
    const symptoms = String(row?.symptoms || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    if (!allergyName && !allergySeverity && symptoms.length === 0) {
      return;
    }

    lines.push(`allergy:${allergyName},${allergySeverity}`);
    symptoms.forEach((symptom) => {
      lines.push(`symptom:${symptom}`);
    });
  });

  return lines.join("\n");
}

function normalizePatient(document) {
  if (!document) return null;
  const raw = typeof document.toObject === "function" ? document.toObject() : document;
  return {
    id: raw.id,
    rfid: raw.rfid,
    doctor: raw.doctor,
    roomId: raw.roomId,
    patient: raw.patient,
    conversationSummary: raw.conversationSummary,
    previousDoctorNotes: raw.previousDoctorNotes
  };
}

async function getAllPatients() {
  if (isMongoConnected()) {
    const rows = await Patient.find({}).lean();
    return rows.map(normalizePatient);
  }

  try {
    const rows = await Patient.find({}).lean();
    if (rows.length > 0) {
      return rows.map(normalizePatient);
    }
  } catch (error) {
    // Fallback to mock data when Mongo is unavailable.
  }
  return mockPatients;
}

async function getPatientByRfid(rfid) {
  const key = (rfid || "").trim().toUpperCase();
  if (!key) return null;

  if (isMongoConnected()) {
    const found = await Patient.findOne({ rfid: key }).lean();
    return found ? normalizePatient(found) : null;
  }

  try {
    const found = await Patient.findOne({ rfid: key }).lean();
    if (found) return normalizePatient(found);
  } catch (error) {
    // Fallback to mock data when Mongo is unavailable.
  }

  return mockPatients.find((record) => record.rfid.toUpperCase() === key) || null;
}

router.get("/", async (_req, res) => {
  const patients = await getAllPatients();
  const quickList = patients.map((p) => ({
    id: p.id,
    name: p.patient?.name,
    rfid: p.rfid
  }));

  res.json({ ok: true, data: quickList });
});

router.get("/rfid/:rfid", async (req, res) => {
  const patient = await getPatientByRfid(req.params.rfid);
  if (!patient) {
    res.status(404).json({ ok: false, message: `RFID \"${req.params.rfid}\" was not found.` });
    return;
  }

  res.json({ ok: true, data: patient });
});

router.post("/txt", async (req, res) => {
  const body = req.body || {};
  const patientId = String(body.id || "").trim();
  const patientName = String(body.name || "").trim();
  const rfid = String(body.rfid || patientId || "").trim().toUpperCase();

  const requiredFields = [
    "id",
    "name",
    "dob",
    "visit",
    "severity",
    "gender",
    "height",
    "weight",
    "bp",
    "conditions",
    "medications",
    "family"
  ];

  const missingFields = requiredFields.filter((field) => !String(body[field] || "").trim());
  if (missingFields.length > 0) {
    res.status(400).json({
      ok: false,
      message: `Missing required fields: ${missingFields.join(", ")}.`
    });
    return;
  }

  if (!patientId || !patientName || !rfid) {
    res.status(400).json({ ok: false, message: "Patient id and name are required." });
    return;
  }

  const safeId = patientId.replace(/[^a-zA-Z0-9_-]/g, "_");
  const fileName = `${safeId}.txt`;
  const outputPath = path.join(txtOutputDir, fileName);
  const content = buildPatientTxtContent(body);
  const patientDoc = buildPatientDocument({ ...body, rfid });

  try {
    await mkdir(txtOutputDir, { recursive: true });
    await writeFile(outputPath, content, "utf8");
    await Patient.findOneAndUpdate(
      { $or: [{ rfid }, { id: patientId }] },
      patientDoc,
      { upsert: true, new: true, runValidators: true, setDefaultsOnInsert: true }
    );
  } catch (error) {
    res.status(500).json({ ok: false, message: "Failed to write txt file and patient record." });
    return;
  }

  res.status(201).json({
    ok: true,
    data: {
      fileName,
      filePath: outputPath,
      content
    }
  });
});

router.post("/sync-txt", async (_req, res) => {
  const result = await syncTxtPatientsToMongo();
  res.json({ ok: true, data: result });
});

export default router;

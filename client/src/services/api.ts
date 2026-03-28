import type {
  PatientRecord,
  PatientTxtPayload,
  PatientTxtResult,
  QuickRfidEntry
} from "../types";

interface ApiResponse<T> {
  ok: boolean;
  message?: string;
  data: T;
}

async function readJson<T>(response: Response): Promise<ApiResponse<T>> {
  return (await response.json()) as ApiResponse<T>;
}

export async function fetchQuickRfids(): Promise<QuickRfidEntry[]> {
  const response = await fetch("/api/patients");
  const payload = await readJson<QuickRfidEntry[]>(response);

  if (!response.ok || !payload.ok) {
    throw new Error(payload.message || "Failed to load patient list.");
  }

  return payload.data;
}

export async function fetchPatientByRfid(rfid: string): Promise<PatientRecord> {
  const response = await fetch(`/api/patients/rfid/${encodeURIComponent(rfid)}`);
  const payload = await readJson<PatientRecord>(response);

  if (!response.ok || !payload.ok) {
    throw new Error(payload.message || "Patient record was not found.");
  }

  return payload.data;
}

export async function createPatientTxt(payloadBody: PatientTxtPayload): Promise<PatientTxtResult> {
  const response = await fetch("/api/patients/txt", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payloadBody)
  });

  const payload = await readJson<PatientTxtResult>(response);

  if (!response.ok || !payload.ok) {
    throw new Error(payload.message || "Failed to create patient txt file.");
  }

  return payload.data;
}

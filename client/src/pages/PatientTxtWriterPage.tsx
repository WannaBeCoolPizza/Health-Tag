import { useState, type FormEvent } from "react";
import { createPatientTxt } from "../services/api";
import type { PatientTxtPayload, WriterAllergy } from "../types";

interface WriterMessage {
  type: "" | "error" | "success";
  text: string;
}

function todayYyyymmdd() {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}${m}${day}`;
}

const emptyAllergy = (): WriterAllergy => ({
  name: "",
  severity: "",
  symptoms: ""
});

const defaultForm: PatientTxtPayload = {
  id: "",
  rfid: "",
  name: "",
  dob: "",
  visit: todayYyyymmdd(),
  severity: "3",
  gender: "",
  height: "",
  weight: "",
  bp: "",
  conditions: "",
  medications: "",
  family: "",
  allergies: [emptyAllergy()]
};

export default function PatientTxtWriterPage() {
  const [form, setForm] = useState<PatientTxtPayload>(defaultForm);
  const [message, setMessage] = useState<WriterMessage>({ type: "", text: "" });
  const [resultText, setResultText] = useState<string>("");

  function updateField(field: keyof PatientTxtPayload, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function updateAllergy(index: number, field: keyof WriterAllergy, value: string) {
    setForm((prev) => ({
      ...prev,
      allergies: prev.allergies.map((row, rowIndex) =>
        rowIndex === index ? { ...row, [field]: value } : row
      )
    }));
  }

  function addAllergyRow() {
    setForm((prev) => ({ ...prev, allergies: [...prev.allergies, emptyAllergy()] }));
  }

  function removeAllergyRow(index: number) {
    setForm((prev) => {
      const next = prev.allergies.filter((_row, rowIndex) => rowIndex !== index);
      return { ...prev, allergies: next.length ? next : [emptyAllergy()] };
    });
  }

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage({ type: "", text: "" });

    if (!form.id.trim() || !form.name.trim() || !form.rfid.trim()) {
      setMessage({ type: "error", text: "Patient ID, RFID, and Name are required." });
      return;
    }

    try {
      const result = await createPatientTxt(form);
      setResultText(result.content);
      setMessage({
        type: "success",
        text: `Saved ${result.fileName} in RFID Code/patients.`
      });
    } catch (error) {
      const text = error instanceof Error ? error.message : "Failed to write txt file.";
      setMessage({ type: "error", text });
    }
  }

  return (
    <main className="writer-main">
      <section className="writer-card">
        <h1 className="writer-title">Patient TXT Writer</h1>
        <p className="writer-subtitle">
          Create an ESP32-friendly patient text file (same format as your RFID workflow).
        </p>

        <form className="writer-form" onSubmit={submitForm}>
          <div className="writer-grid">
            <label>
              ID
              <input value={form.id} onChange={(e) => updateField("id", e.target.value)} placeholder="1042" />
            </label>
            <label>
              RFID
              <input
                value={form.rfid}
                onChange={(e) => updateField("rfid", e.target.value.toUpperCase())}
                placeholder="A1B2C3D4"
              />
            </label>
            <label>
              Name
              <input value={form.name} onChange={(e) => updateField("name", e.target.value)} placeholder="Jane Doe" />
            </label>
            <label>
              DOB (YYYYMMDD)
              <input value={form.dob} onChange={(e) => updateField("dob", e.target.value)} placeholder="19900315" />
            </label>
            <label>
              Visit Date (YYYYMMDD)
              <input value={form.visit} onChange={(e) => updateField("visit", e.target.value)} />
            </label>
            <label>
              Severity (1-5)
              <input value={form.severity} onChange={(e) => updateField("severity", e.target.value)} />
            </label>
            <label>
              Gender
              <input value={form.gender} onChange={(e) => updateField("gender", e.target.value)} placeholder="F" />
            </label>
            <label>
              Height
              <input value={form.height} onChange={(e) => updateField("height", e.target.value)} placeholder="165.0" />
            </label>
            <label>
              Weight
              <input value={form.weight} onChange={(e) => updateField("weight", e.target.value)} placeholder="68.5" />
            </label>
            <label>
              BP
              <input value={form.bp} onChange={(e) => updateField("bp", e.target.value)} placeholder="120.5" />
            </label>
            <label>
              Conditions (comma-separated)
              <input
                value={form.conditions}
                onChange={(e) => updateField("conditions", e.target.value)}
                placeholder="Asthma, Hypertension"
              />
            </label>
            <label>
              Medications (comma-separated)
              <input
                value={form.medications}
                onChange={(e) => updateField("medications", e.target.value)}
                placeholder="Albuterol, Lisinopril"
              />
            </label>
            <label>
              Family History
              <input
                value={form.family}
                onChange={(e) => updateField("family", e.target.value)}
                placeholder="Diabetes (father)"
              />
            </label>
          </div>

          <div className="allergy-wrap">
            <div className="allergy-head">
              <h2>Allergies</h2>
              <button className="rbtn" type="button" onClick={addAllergyRow}>
                Add Allergy
              </button>
            </div>

            {form.allergies.map((row, index) => (
              <div className="allergy-row" key={`${index}-${row.name}`}>
                <input
                  value={row.name}
                  onChange={(e) => updateAllergy(index, "name", e.target.value)}
                  placeholder="Allergen"
                />
                <input
                  value={row.severity}
                  onChange={(e) => updateAllergy(index, "severity", e.target.value)}
                  placeholder="Severity"
                />
                <input
                  value={row.symptoms}
                  onChange={(e) => updateAllergy(index, "symptoms", e.target.value)}
                  placeholder="Symptoms (comma-separated)"
                />
                <button className="rbtn" type="button" onClick={() => removeAllergyRow(index)}>
                  Remove
                </button>
              </div>
            ))}
          </div>

          <button className="rbtn writer-submit" type="submit">
            Save TXT File
          </button>
        </form>

        {message.type === "error" ? <div className="rerr">{message.text}</div> : null}
        {message.type === "success" ? <div className="rok">{message.text}</div> : null}
      </section>

      <section className="writer-output">
        <div className="panel-title">Generated TXT Preview</div>
        <pre>{resultText || "Your generated .txt content will appear here after save."}</pre>
      </section>
    </main>
  );
}

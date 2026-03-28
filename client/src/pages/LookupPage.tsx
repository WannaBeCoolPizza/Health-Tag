import { useEffect, useState } from "react";
import InfoField from "../components/InfoField";
import { fetchPatientByRfid, fetchQuickRfids } from "../services/api";
import type { PatientRecord, QuickRfidEntry } from "../types";

interface MessageState {
  type: "" | "error" | "success";
  text: string;
}

function normalizeKey(value: string) {
  return value.trim().toUpperCase();
}

export default function LookupPage() {
  const [rfidInput, setRfidInput] = useState<string>("");
  const [quickRfids, setQuickRfids] = useState<QuickRfidEntry[]>([]);
  const [patientRecord, setPatientRecord] = useState<PatientRecord | null>(null);
  const [message, setMessage] = useState<MessageState>({ type: "", text: "" });

  useEffect(() => {
    let isMounted = true;

    fetchQuickRfids()
      .then((rows) => {
        if (isMounted) setQuickRfids(rows);
      })
      .catch((error: Error) => {
        if (isMounted) {
          setMessage({ type: "error", text: error.message || "Failed to load quick RFIDs." });
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  async function runLookup(value?: string) {
    const key = normalizeKey(value ?? rfidInput);

    if (!key) {
      setMessage({ type: "error", text: "Enter an RFID first." });
      return;
    }

    setMessage({ type: "", text: "" });

    try {
      const record = await fetchPatientByRfid(key);
      setPatientRecord(record);
      setRfidInput(key);
      setMessage({ type: "success", text: `Patient record loaded for ${record.patient.name}` });
    } catch (error) {
      const text = error instanceof Error ? error.message : "RFID lookup failed.";
      setPatientRecord(null);
      setMessage({ type: "error", text });
    }
  }

  const summary = patientRecord?.conversationSummary;
  const patient = patientRecord?.patient;

  return (
    <main className="main">
      <section className="lookup">
        <div className="lookup-card">
          <div className="lookup-hero">
            <div className="lookup-icon">♥</div>
            <div className="lookup-title">RFID Search</div>
            <div className="lookup-sub">
              Enter the RFID first. The dashboard will load the conversation summary,
              previous doctor notes, and patient information from the backend API.
            </div>
          </div>

          <div className="rform">
            <label className="rlabel" htmlFor="rfidInput">
              RFID Input
            </label>
            <input
              id="rfidInput"
              className="rinput"
              placeholder="Enter RFID, e.g. DR-SMITH"
              value={rfidInput}
              onChange={(event) => setRfidInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") runLookup();
              }}
            />
            <button className="rbtn" type="button" onClick={() => runLookup()}>
              Load Patient Record
            </button>
          </div>
        </div>

        {message.type === "error" ? <div className="rerr">{message.text}</div> : null}
        {message.type === "success" ? <div className="rok">{message.text}</div> : null}

        <div className="lookup-card">
          <div className="panel-title">Quick Test RFIDs</div>
          <div className="quick">
            {quickRfids.map((entry) => (
              <button key={entry.id} type="button" onClick={() => runLookup(entry.rfid)}>
                <strong>{entry.name}</strong>
                <br />
                <code>{entry.rfid}</code>
              </button>
            ))}
          </div>
        </div>

        <div className="lookup-card side-note">
          ESP32 readers can continue posting RFID scans to your backend while this page stays focused on
          rapid clinician lookup.
        </div>
      </section>

      <section className="content">
        {!patientRecord || !summary || !patient ? (
          <div className="empty">
            <div className="empty-ico">♡</div>
            <div className="empty-title">Enter an RFID to load a patient</div>
            <div className="empty-subtitle">
              The lookup will show the conversation summary, previous doctor notes,
              and patient information.
            </div>
          </div>
        ) : (
          <>
            <div className="content-top">
              <div className="patient-head">
                <div>
                  <div className="patient-name">{patient.name}</div>
                  <div className="patient-meta">
                    <span className="chip">RFID: {patientRecord.rfid}</span>
                    <span className="chip">Doctor: {patientRecord.doctor}</span>
                    <span className="chip">MRN: {patient.mrn}</span>
                    <span className="chip">DOB: {patient.dob}</span>
                  </div>
                </div>
                <div className="room-pill">{patientRecord.roomId}</div>
              </div>
            </div>

            <div className="sections">
              <div className="col">
                <div className="panel">
                  <div className="panel-title">Conversation Summary</div>
                  <div className="box">
                    <InfoField label="Chief Complaint" value={summary.chiefComplaint} />
                    <InfoField label="Visit Type" value={summary.visitType} />
                    <InfoField label="Onset" value={summary.onset} />
                    <InfoField label="Severity" value={summary.severity} />
                    <InfoField label="Symptoms" value={summary.symptoms} isList />
                    <InfoField label="Patient Questions" value={summary.patientQuestions} isList />
                    <InfoField label="Requested Treatment" value={summary.requestedTreatment} />
                    <InfoField label="Key Notes" value={summary.keyNotes} />
                  </div>
                </div>
              </div>

              <div className="col">
                <div className="panel">
                  <div className="panel-title">Previous Doctor Notes</div>
                  <div className="box">
                    <InfoField label="Chart Notes" value={patientRecord.previousDoctorNotes} isList />
                  </div>
                </div>

                <div className="panel">
                  <div className="panel-title">Patient Information</div>
                  <div className="box">
                    <InfoField label="Age" value={String(patient.age)} />
                    <InfoField label="Sex" value={patient.sex} />
                    <InfoField label="Medical History" value={patient.history} />
                    <InfoField label="Current Medications" value={patient.medications} isList />
                    <InfoField label="Allergies" value={patient.allergies} isList />
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </section>
    </main>
  );
}

import { readdir, readFile } from "node:fs/promises";
import { watch } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Patient } from "../models/Patient.js";
import { buildPatientDocument, parseRfidTxtContent } from "../utils/patientTransform.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const baseRfidDir = path.resolve(__dirname, "../../../RFID Code");
const patientFilesDir = path.resolve(__dirname, "../../../PatientFiles");
const txtSourceDirs = [baseRfidDir, path.join(baseRfidDir, "patients"), patientFilesDir];

async function collectTxtFiles() {
  const fileSet = new Set();

  for (const dir of txtSourceDirs) {
    try {
      const entries = await readdir(dir, { withFileTypes: true });
      entries
        .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".txt"))
        .forEach((entry) => fileSet.add(path.join(dir, entry.name)));
    } catch (error) {
      // Ignore missing directories so startup remains resilient.
    }
  }

  return Array.from(fileSet);
}

export async function syncTxtPatientsToMongo() {
  if (Patient.db.readyState !== 1) {
    return { synced: 0, skipped: 0, errors: ["Mongo is not connected."] };
  }

  const files = await collectTxtFiles();
  let synced = 0;
  let skipped = 0;
  const errors = [];

  for (const filePath of files) {
    try {
      const content = await readFile(filePath, "utf8");
      const parsed = parseRfidTxtContent(content);
      const id = String(parsed.id || "").trim();
      const rfid = String(parsed.rfid || "").trim().toUpperCase();

      if (!id || !rfid) {
        skipped += 1;
        continue;
      }

      const patientDoc = buildPatientDocument(parsed);
      await Patient.findOneAndUpdate(
        { $or: [{ rfid }, { id }] },
        patientDoc,
        { upsert: true, new: true, runValidators: true, setDefaultsOnInsert: true }
      );
      synced += 1;
    } catch (error) {
      errors.push(`${filePath}: ${error.message}`);
    }
  }

  return { synced, skipped, errors };
}

export function startRfidTxtAutoSync() {
  let timer = null;

  const scheduleSync = () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(async () => {
      const result = await syncTxtPatientsToMongo();
      if (result.errors.length > 0) {
        console.warn("TXT sync completed with errors:", result.errors);
      }
    }, 400);
  };

  // Initial import at startup so existing txt records become Mongo patients.
  scheduleSync();

  // File watchers keep Mongo updated whenever txt files are created/edited.
  const watchers = txtSourceDirs.map((dir) => {
    try {
      return {
        dir,
        watcher: watch(dir, (_eventType, fileName) => {
          if (String(fileName || "").toLowerCase().endsWith(".txt")) {
            scheduleSync();
          }
        })
      };
    } catch (error) {
      return null;
    }
  });

  // Interval fallback catches any missed file system events.
  const intervalId = setInterval(scheduleSync, 30000);

  return {
    stop: () => {
      if (timer) clearTimeout(timer);
      clearInterval(intervalId);
      watchers.forEach((item) => {
        if (item && item.watcher) {
          item.watcher.close();
        }
      });
    }
  };
}

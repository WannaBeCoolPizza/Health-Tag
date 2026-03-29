import dotenv from "dotenv";
import mongoose from "mongoose";
import { syncTxtPatientsToMongo } from "../src/services/rfidTxtSync.js";

dotenv.config();

async function run() {
  const mongoUri = process.env.MONGODB_URI;
  if (!mongoUri) {
    console.error("MONGODB_URI is not set. Configure server/.env first.");
    process.exit(1);
  }

  try {
    await mongoose.connect(mongoUri);
    console.log("MongoDB connected");

    const result = await syncTxtPatientsToMongo();
    console.log(`TXT sync completed. Synced: ${result.synced}, Skipped: ${result.skipped}`);
    if (result.errors.length > 0) {
      console.warn("Sync errors:");
      result.errors.forEach((line) => console.warn(`- ${line}`));
    }
  } catch (error) {
    console.error("TXT sync failed:", error.message);
    process.exitCode = 1;
  } finally {
    await mongoose.disconnect();
  }
}

run();

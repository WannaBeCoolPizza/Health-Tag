import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import mongoose from "mongoose";
import patientRoutes from "./routes/patients.js";
import { startRfidTxtAutoSync } from "./services/rfidTxtSync.js";

dotenv.config();

const app = express();
const port = Number(process.env.PORT || 5000);
const mongoUri = process.env.MONGODB_URI;

app.use(cors());
app.use(express.json());

app.get("/api/health", (_req, res) => {
  const mongoState = mongoose.connection.readyState === 1 ? "connected" : "disconnected";
  res.json({ ok: true, service: "heart-tag-api", mongo: mongoState });
});

app.use("/api/patients", patientRoutes);

async function startServer() {
  let autoSync = null;

  if (mongoUri) {
    try {
      await mongoose.connect(mongoUri);
      // Keep server available even if Mongo is temporarily down by using fallback data in routes.
      console.log("MongoDB connected");
      autoSync = startRfidTxtAutoSync();
    } catch (error) {
      console.warn("MongoDB connection failed, using mock fallback:", error.message);
    }
  } else {
    console.warn("MONGODB_URI is not set. Running with mock fallback data.");
  }

  app.listen(port, () => {
    console.log(`API listening at http://localhost:${port}`);
  });

  const shutdown = () => {
    if (autoSync) {
      autoSync.stop();
    }
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

startServer();

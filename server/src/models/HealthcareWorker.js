import mongoose from "mongoose";

const healthcareWorkerSchema = new mongoose.Schema(
  {
    username: {
      type: String,
      required: true,
      unique: true,
      trim: true,
      lowercase: true,
      minlength: 3
    },
    password: {
      type: String,
      required: true,
      minlength: 6
    },
    name: {
      type: String,
      required: true
    },
    email: {
      type: String,
      trim: true,
      lowercase: true
    },
    role: {
      type: String,
      enum: ["healthcare_worker", "doctor", "nurse", "admin"],
      default: "healthcare_worker"
    },
    isActive: {
      type: Boolean,
      default: true
    }
  },
  { timestamps: true, collection: "healthcare_workers" }
);

export const HealthcareWorker = mongoose.model("HealthcareWorker", healthcareWorkerSchema);

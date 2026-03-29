/**
 * Authentication Controller
 * 
 * Handles healthcare worker authentication against MongoDB.
 * In a production environment, passwords should be hashed using bcrypt.
 */

import { HealthcareWorker } from "../models/HealthcareWorker.js";

/**
 * Verify healthcare worker credentials against MongoDB
 * @param {string} username - Healthcare worker username
 * @param {string} password - Healthcare worker password (plain text - should be hashed in production)
 * @returns {Object} { success: boolean, user: Object|null, message: string }
 */
export async function verifyCredentials(username, password) {
  try {
    if (!username || !password) {
      return {
        success: false,
        user: null,
        message: "Username and password are required"
      };
    }

    // Query MongoDB for healthcare worker
    const worker = await HealthcareWorker.findOne({ username: username.toLowerCase() });

    if (!worker) {
      return {
        success: false,
        user: null,
        message: "Invalid username or password"
      };
    }

    // Check if worker is active
    if (!worker.isActive) {
      return {
        success: false,
        user: null,
        message: "This account has been deactivated"
      };
    }

    // Compare passwords (in production, use bcrypt.compare())
    if (worker.password !== password) {
      return {
        success: false,
        user: null,
        message: "Invalid username or password"
      };
    }

    // Credentials are valid
    return {
      success: true,
      user: {
        id: worker._id.toString(),
        username: worker.username,
        name: worker.name,
        email: worker.email,
        role: worker.role
      },
      message: "Authentication successful"
    };
  } catch (error) {
    console.error("Auth verification error:", error);
    return {
      success: false,
      user: null,
      message: "Authentication service error"
    };
  }
}

/**
 * Register a new healthcare worker
 * @param {Object} data - { username, password, name, email, role }
 * @returns {Object} { success: boolean, user: Object|null, message: string }
 */
export async function registerHealthcareWorker(data) {
  try {
    const { username, password, name, email, role = "healthcare_worker" } = data;

    // Validate input
    if (!username || !password || !name) {
      return {
        success: false,
        user: null,
        message: "Username, password, and name are required"
      };
    }

    if (password.length < 6) {
      return {
        success: false,
        user: null,
        message: "Password must be at least 6 characters"
      };
    }

    // Check if username already exists
    const existingWorker = await HealthcareWorker.findOne({ username: username.toLowerCase() });
    if (existingWorker) {
      return {
        success: false,
        user: null,
        message: "Username already taken"
      };
    }

    // Create new healthcare worker
    const newWorker = new HealthcareWorker({
      username: username.toLowerCase(),
      password, // In production, hash with bcrypt
      name,
      email: email?.toLowerCase() || "",
      role: role || "healthcare_worker",
      isActive: true
    });

    const savedWorker = await newWorker.save();

    return {
      success: true,
      user: {
        id: savedWorker._id.toString(),
        username: savedWorker.username,
        name: savedWorker.name,
        email: savedWorker.email,
        role: savedWorker.role
      },
      message: "Healthcare worker registered successfully"
    };
  } catch (error) {
    console.error("Registration error:", error);
    return {
      success: false,
      user: null,
      message: error.message || "Registration failed"
    };
  }
}

/**
 * Get all healthcare workers (admin only - should add auth check in production)
 * @returns {Array} List of healthcare workers
 */
export async function getAllHealthcareWorkers() {
  try {
    const workers = await HealthcareWorker.find({}, "-password");
    return workers;
  } catch (error) {
    console.error("Error fetching workers:", error);
    return [];
  }
}

/**
 * Seed default healthcare worker if database is empty
 */
export async function seedDefaultWorker() {
  try {
    const count = await HealthcareWorker.countDocuments();
    
    if (count === 0) {
      const defaultWorker = new HealthcareWorker({
        username: "healthcare",
        password: "worker123",
        name: "Healthcare Worker",
        email: "healthcare@hospital.local",
        role: "healthcare_worker",
        isActive: true
      });

      await defaultWorker.save();
      console.log("✓ Default healthcare worker created: healthcare/worker123");
    }
  } catch (error) {
    if (error.code !== 11000) { // Ignore duplicate key error
      console.error("Error seeding default worker:", error);
    }
  }
}

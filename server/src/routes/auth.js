/**
 * Authentication Routes
 * 
 * API endpoints for healthcare worker authentication.
 */

import express from "express";
import { verifyCredentials, registerHealthcareWorker, getAllHealthcareWorkers } from "../controllers/authController.js";

const router = express.Router();

/**
 * POST /api/auth/login
 * Verify healthcare worker credentials
 * 
 * Request body:
 * {
 *   "username": "healthcare",
 *   "password": "worker123"
 * }
 * 
 * Response:
 * {
 *   "success": true,
 *   "user": { "id": "...", "username": "healthcare", "name": "Healthcare Worker", "role": "healthcare_worker" },
 *   "message": "Authentication successful"
 * }
 */
router.post("/login", async (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.status(400).json({
      success: false,
      message: "Username and password are required"
    });
  }

  const result = await verifyCredentials(username, password);
  const statusCode = result.success ? 200 : 401;

  res.status(statusCode).json(result);
});

/**
 * POST /api/auth/register
 * Register a new healthcare worker (should be protected in production)
 * 
 * Request body:
 * {
 *   "username": "newworker",
 *   "password": "password123",
 *   "name": "Jane Doe",
 *   "email": "jane@hospital.local",
 *   "role": "nurse"
 * }
 */
router.post("/register", async (req, res) => {
  const result = await registerHealthcareWorker(req.body);
  const statusCode = result.success ? 201 : 400;

  res.status(statusCode).json(result);
});

/**
 * GET /api/auth/workers
 * Get all healthcare workers (should be protected in production)
 */
router.get("/workers", async (req, res) => {
  const workers = await getAllHealthcareWorkers();
  res.json(workers);
});

export default router;

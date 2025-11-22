// src/routes/PlacementPrediction.js
import express from "express";
import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const router = express.Router();

// Fix for __dirname in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Project root (one level up from src/)
const PROJECT_ROOT = path.join(__dirname, "..");

// Path to PlacementPrediction.py (relative to project root)
const SCRIPT_RELATIVE = path.join("ml", "PlacementPrediction.py");
const SCRIPT_PATH = path.join(PROJECT_ROOT, SCRIPT_RELATIVE);

router.post("/predict", (req, res) => {
  const { collegeName } = req.body;

  if (!collegeName || typeof collegeName !== "string" || collegeName.trim().length === 0) {
    return res.status(400).json({ error: "Missing or invalid collegeName in request body" });
  }

  // Detect OS-specific python command
  const isWin = process.platform === "win32";
  const pythonCmd = isWin ? "python" : "python3";

  // Spawn Python process with college name as argument
  // Use cwd = PROJECT_ROOT so relative paths in the Python script resolve properly
  const python = spawn(pythonCmd, [SCRIPT_PATH, collegeName], { cwd: PROJECT_ROOT });

  let stdout = "";
  let stderr = "";

  python.stdout.on("data", (data) => {
    stdout += data.toString();
  });

  python.stderr.on("data", (data) => {
    stderr += data.toString();
    // Also log to server console for debugging (do not expose secrets)
    console.error("[PlacementPrediction.py stderr]", data.toString());
  });

  python.on("error", (err) => {
    console.error("Failed to start Python process:", err);
    return res.status(500).json({ error: "Failed to start Python process", details: err.message });
  });

  python.on("close", (code) => {
    if (code !== 0) {
      // Try to send stderr back (trimmed), but avoid exposing secrets if present
      const errMsg = stderr ? stderr.trim().split("\n").slice(-10).join("\n") : `Python exited with code ${code}`;
      return res.status(500).json({ error: "Python script failed", details: errMsg });
    }

    if (!stdout || stdout.trim().length === 0) {
      return res.status(500).json({ error: "Python script returned no output" });
    }

    // The Python script prints JSON (predictions only). Parse and return it.
    try {
      const parsed = JSON.parse(stdout);
      return res.json(parsed);
    } catch (err) {
      console.error("Failed to parse Python output:", err);
      console.error("Raw stdout:", stdout);
      return res.status(500).json({ error: "Invalid Python response", details: "Unable to parse JSON from script output" });
    }
  });
});

export default router;

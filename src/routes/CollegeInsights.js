// src/routes/CollegeInsights.js
import express from "express";
import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const router = express.Router();

// Fix for __dirname in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

router.post("/insights", (req, res) => {
  const { collegeName } = req.body;

  if (!collegeName) {
    return res.status(400).json({ error: "Missing collegeName in request body" });
  }

  // Detect OS-specific python command
  const isWin = process.platform === "win32";
  const pythonCmd = isWin ? "python" : "python3";

  // Path to CollegeInsights.py (adjust if script is elsewhere)
  const scriptPath = path.join(__dirname, "../ml/CollegeInsights.py");

  // Spawn Python process with college name as argument
  const python = spawn(pythonCmd, [scriptPath, collegeName]);

  let result = "";

  python.stdout.on("data", (data) => {
    result += data.toString();
  });

  python.stderr.on("data", (data) => {
    console.error(` Python error: ${data}`);
  });

  python.on("close", (code) => {
    if (code !== 0) {
      return res.status(500).json({ error: "Python script failed" });
    }

    try {
      res.json(JSON.parse(result));
    } catch (err) {
      console.error(" Failed to parse Python output:", result);
      res.status(500).json({ error: "Invalid Python response" });
    }
  });
});

export default router;

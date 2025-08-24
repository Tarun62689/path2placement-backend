// src/routes/CollegeGrowth.js
import express from "express";
import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const router = express.Router();

// Fix for __dirname in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

router.post("/growth", (req, res) => {
  const { topN } = req.body || {};
  const topNumber = parseInt(topN) || 5; // default 5

  // OS-specific Python command
  const isWin = process.platform === "win32";
  const pythonCmd = isWin ? "python" : "python3";

  // Path to Python script
  const scriptPath = path.join(__dirname, "../ml/CollegeGrowth.py");

  const args = [scriptPath, String(topNumber)];

  const python = spawn(pythonCmd, args, { encoding: "utf-8" });

  let output = "";
  let errorOutput = "";

  python.stdout.on("data", (data) => {
    output += data.toString();
  });

  python.stderr.on("data", (data) => {
    errorOutput += data.toString();
  });

  python.on("close", (code) => {
    if (code !== 0) {
      console.error("Python script error:", errorOutput);
      return res.status(500).json({ error: "Python script failed", details: errorOutput });
    }

    try {
      // Parse JSON output from Python script
      const jsonResult = JSON.parse(output);
      res.json(jsonResult); // send as proper JSON
    } catch (err) {
      console.error("Failed to parse Python output:", output, err);
      res.status(500).json({ error: "Invalid Python response", details: output });
    }
  });
});

export default router;

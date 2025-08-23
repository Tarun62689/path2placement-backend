// src/routes/Collegefinder.js
import express from "express";
import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const router = express.Router();

// Fix for __dirname in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

router.post("/finder", (req, res) => {
  const { location = "all", course, topN = 5 } = req.body;

  if (!course) {
    return res.status(400).json({ error: "Missing required field: course" });
  }

  // OS-specific Python command
  const isWin = process.platform === "win32";
  const pythonCmd = isWin ? "python" : "python3";

  // Path to Python script
  const scriptPath = path.join(__dirname, "../ml/CollegeFinder.py");

  // Use "null" for empty locations so Python script handles it
  const locationArg = location.trim() === "" ? "null" : location.trim();
  const topNArg = String(topN);

  const args = [scriptPath, locationArg, course, topNArg];

  const python = spawn(pythonCmd, args);

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
      const jsonResult = JSON.parse(output);
      res.json(jsonResult);
    } catch (err) {
      console.error("Failed to parse Python output:", output);
      res.status(500).json({ error: "Invalid Python response", details: output });
    }
  });
});

export default router;

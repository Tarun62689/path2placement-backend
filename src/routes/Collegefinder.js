// src/routes/CollegeFinder.js
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

  // Arguments to pass to Python
  const args = [scriptPath, location || "null", course, String(topN)];

  console.log("Running Python script:", pythonCmd, args);

  const pythonProcess = spawn(pythonCmd, args);

  let output = "";
  let errorOutput = "";

  pythonProcess.stdout.on("data", (data) => {
    output += data.toString();
  });

  pythonProcess.stderr.on("data", (data) => {
    errorOutput += data.toString();
  });

  pythonProcess.on("close", (code) => {
    console.log("Python process exited with code:", code);
    if (errorOutput) console.error("Python stderr:", errorOutput);
    if (!output) {
      return res.status(500).json({ error: "No output from Python script" });
    }

    try {
      const jsonResult = JSON.parse(output);
      res.json(jsonResult);
    } catch (err) {
      console.error("Failed to parse JSON:", err);
      console.log("Raw Python output:", output);
      res.status(500).json({ error: "Invalid JSON output from Python script", rawOutput: output });
    }
  });

  pythonProcess.on("error", (err) => {
    console.error("Failed to start Python process:", err);
    res.status(500).json({ error: "Failed to start Python script", details: err.message });
  });
});

export default router;

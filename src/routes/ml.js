// src/routes/ml.js
import express from "express";
import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const router = express.Router();

// Fix for __dirname in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

router.post("/predict", (req, res) => {
  const { features } = req.body;

  // Run Python script
const isWin = process.platform === "win32";
const pythonCmd = isWin ? "python" : "python3";

const python = spawn(pythonCmd, [path.join(__dirname, "../ml/model.py")]);


  // Send input to Python
  python.stdin.write(JSON.stringify({ features }));
  python.stdin.end();

  let result = "";

  python.stdout.on("data", (data) => {
    result += data.toString();
  });

  python.stderr.on("data", (data) => {
    console.error(`❌ Python error: ${data}`);
  });

  python.on("close", () => {
    try {
      res.json(JSON.parse(result));
    } catch {
      res.status(500).json({ error: "Failed to parse Python output" });
    }
  });
});

export default router;

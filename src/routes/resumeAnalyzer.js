// src/routes/resumeAnalyzer.js
import express from "express";
import { spawn } from "child_process";
import path from "path";
import { supabase } from "../services/supabaseClient.js";

const router = express.Router();

router.post("/resume-analyzer", async (req, res) => {
  try {
    const { resume_path, job_role } = req.body;

    if (!resume_path || !job_role) {
      return res.status(400).json({ error: "resume_path and job_role are required" });
    }

    // ✅ Extract user_id from JWT token
    const token = req.headers.authorization?.split(" ")[1];
    if (!token) return res.status(401).json({ error: "No token provided" });

    const { data: { user }, error: userError } = await supabase.auth.getUser(token);
    if (userError || !user) return res.status(401).json({ error: "Invalid token" });

    const user_id = user.id;

    const isWin = process.platform === "win32";
    const pythonCmd = isWin ? "python" : "python3";
    const scriptPath = path.join(process.cwd(), "src/ml/Main_Resume.py");

    const pythonProcess = spawn(pythonCmd, [scriptPath]);

    let result = "";
    let errorMsg = "";

    pythonProcess.stdout.on("data", (data) => {
      result += data.toString();
    });

    pythonProcess.stderr.on("data", (data) => {
      errorMsg += data.toString();
    });

    pythonProcess.on("close", async (code) => {
      if (code !== 0) {
        return res.status(500).json({
          error: "Python script failed",
          details: errorMsg || result || `Exited with code ${code}`,
        });
      }

      let parsed;
      try {
        parsed = JSON.parse(result);
      } catch (err) {
        return res.status(500).json({
          error: "Failed to parse Python output",
          details: err.message,
        });
      }

      try {
        // --- Insert analysis into Supabase with RLS-safe user_id ---
        const { data, error } = await supabase
          .from("resume_analysis")
          .insert([
            {
              user_id,
              resume_path,
              job_role,
              result: parsed, // JSON column
            },
          ])
          .select() // return inserted row including created_at
          .single();

        if (error) {
          console.error("Supabase insert error:", error);
          return res.status(500).json({
            error: "Failed to save analysis in database",
            details: error.message,
          });
        }

        res.json({
          analysis: parsed,
          saved: true,
          record: data, // contains created_at timestamp
        });
      } catch (err) {
        res.status(500).json({
          error: "Unexpected error while saving analysis",
          details: err.message,
        });
      }
    });

    // Send JSON input to Python script
    pythonProcess.stdin.write(JSON.stringify({ resume_path, job_role }));
    pythonProcess.stdin.end();
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;

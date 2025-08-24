// src/routes/resume.js
import express from "express";
import multer from "multer";
import { supabase } from "../services/supabaseClient.js";

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

// UPLOAD resume to Supabase (keeps original filename)
router.post("/upload", upload.single("resume"), async (req, res) => {
  const { user_id } = req.body;

  if (!req.file) {
    return res.status(400).json({ error: "No file uploaded" });
  }
  if (!user_id) {
    return res.status(400).json({ error: "user_id is required" });
  }

  try {
    // File path: user_id/originalFileName.pdf
    const filePath = `${user_id}/${req.file.originalname}`;

    // Upload file buffer to Supabase
    const { data, error } = await supabase.storage
      .from("resumes")
      .upload(filePath, req.file.buffer, {
        contentType: req.file.mimetype,
        upsert: true, // replace old file if exists
      });

    if (error) throw error;

    // Get public URL (if bucket is public)
    const { data: publicUrl } = supabase.storage
      .from("resumes")
      .getPublicUrl(filePath);

    res.json({
      message: "Resume uploaded successfully",
      filePath,
      originalName: req.file.originalname,
      publicUrl: publicUrl.publicUrl,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;

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
    // Step 1: List existing files for the user
    const { data: existingFiles, error: listError } = await supabase.storage
      .from("resumes")
      .list(user_id);

    if (listError) throw listError;

    // Step 2: Check if the same file already exists
    if (existingFiles.find((f) => f.name === req.file.originalname)) {
      return res.status(400).json({
        error: "File already exists. Please rename your file and try again.",
      });
    }

    // Step 3: Upload file buffer to Supabase
    const filePath = `${user_id}/${req.file.originalname}`;
    const { data, error } = await supabase.storage
      .from("resumes")
      .upload(filePath, req.file.buffer, {
        contentType: req.file.mimetype,
        upsert: false, // do not overwrite existing file
      });

    if (error) throw error;

    // Step 4: Get public URL
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

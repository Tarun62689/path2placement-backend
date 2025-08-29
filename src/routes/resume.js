// src/routes/resume.js
import express from "express";
import multer from "multer";
import { supabase } from "../services/supabaseClient.js";

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

// --------------------
// UPLOAD resume to Supabase
// --------------------
router.post("/upload", upload.single("resume"), async (req, res) => {
  const { user_id } = req.body;

  if (!req.file) {
    return res.status(400).json({ error: "No file uploaded" });
  }
  if (!user_id) {
    return res.status(400).json({ error: "user_id is required" });
  }

  try {
    // List existing files for the user
    const { data: existingFiles, error: listError } = await supabase.storage
      .from("resumes")
      .list(user_id);

    if (listError) throw listError;

    // Prevent duplicate uploads
    if (existingFiles.find((f) => f.name === req.file.originalname)) {
      return res.status(400).json({
        error: "File already exists. Please rename your file and try again.",
      });
    }

    // Upload file
    const filePath = `${user_id}/${req.file.originalname}`;
    const { error: uploadError } = await supabase.storage
      .from("resumes")
      .upload(filePath, req.file.buffer, {
        contentType: req.file.mimetype,
        upsert: false,
      });

    if (uploadError) throw uploadError;

    // Create signed URL (valid 1 hour)
    const { data: signedData, error: signedError } = await supabase.storage
      .from("resumes")
      .createSignedUrl(filePath, 3600, { transform: { download: false } });

    if (signedError) throw signedError;

    res.json({
      message: "Resume uploaded successfully",
      filePath,
      originalName: req.file.originalname,
      signedUrl: signedData.signedUrl,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// --------------------
// FETCH resumes for a user
// --------------------
router.get("/:user_id", async (req, res) => {
  const { user_id } = req.params;

  if (!user_id) return res.status(400).json({ error: "user_id is required" });

  try {
    // List files in user's folder
    const { data: files, error: listError } = await supabase.storage
      .from("resumes")
      .list(user_id);

    if (listError) throw listError;

    if (!files || files.length === 0) {
      return res.status(404).json({ message: "No resumes found for this user" });
    }

    // Create signed URLs for each file
    const filesWithUrls = await Promise.all(
      files.map(async (file) => {
        const { data: signedData, error: signedError } = await supabase.storage
          .from("resumes")
          .createSignedUrl(`${user_id}/${file.name}`, 3600);

        if (signedError) throw signedError;

        return {
          filePath: `${user_id}/${file.name}`,
          originalName: file.name,
          signedUrl: signedData.signedUrl,
          updatedAt: file.updated_at,
          size: file.size,
        };
      })
    );

    res.json(filesWithUrls);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

export default router;

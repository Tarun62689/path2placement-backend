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

    // Step 2: Prevent duplicate uploads
    if (existingFiles.find((f) => f.name === req.file.originalname)) {
      return res.status(400).json({
        error: "File already exists. Please rename your file and try again.",
      });
    }

    // Step 3: Upload file
    const filePath = `${user_id}/${req.file.originalname}`;
    const { error: uploadError } = await supabase.storage
      .from("resumes")
      .upload(filePath, req.file.buffer, {
        contentType: req.file.mimetype,
        upsert: false,
      });

    if (uploadError) throw uploadError;

    // Step 4: Create signed URL (inline view, 1 hour expiry)
    const { data: signedData, error: signedError } =
      await supabase.storage.from("resumes").createSignedUrl(filePath, 3600, {
        transform: {
          // ensures the browser treats it inline if possible
          download: false,
        },
      });

    if (signedError) throw signedError;

    res.json({
      message: "Resume uploaded successfully",
      filePath,
      originalName: req.file.originalname,
      signedUrl: signedData.signedUrl, // open this in new tab
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;

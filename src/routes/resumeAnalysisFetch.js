// src/routes/resumeAnalysisFetch.js
import express from "express";
import { supabase } from "../services/supabaseClient.js";

const router = express.Router();

// GET all resume analyses for the logged-in user
router.get("/fetch-analysis", async (req, res) => {
  try {
    // Extract JWT token
    const token = req.headers.authorization?.split(" ")[1];
    if (!token) return res.status(401).json({ error: "No token provided" });

    const { data: { user }, error: userError } = await supabase.auth.getUser(token);
    if (userError || !user) return res.status(401).json({ error: "Invalid token" });

    const user_id = user.id;

    // Fetch all analyses for this user
    const { data, error } = await supabase
      .from("resume_analysis")
      .select("*")
      .eq("user_id", user_id)
      .order("created_at", { ascending: false }); // newest first

    if (error) {
      return res.status(500).json({ error: error.message });
    }

    res.json({ analyses: data });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;

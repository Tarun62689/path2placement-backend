// src/routes/resumeAnalysisFetch.js
import express from "express";
import { supabase } from "../services/supabaseClient.js";

const router = express.Router();

/**
 * ✅ GET all resume analyses for the logged-in user
 */
router.get("/fetch-analysis", async (req, res) => {
  try {
    const token = req.headers.authorization?.split(" ")[1];
    if (!token) return res.status(401).json({ error: "No token provided" });

    const { data: { user }, error: userError } = await supabase.auth.getUser(token);
    if (userError || !user) return res.status(401).json({ error: "Invalid token" });

    const { data, error } = await supabase
      .from("resume_analysis")
      .select("id, type, data, created_at") // 🔒 return only useful fields
      .eq("user_id", user.id)
      .order("created_at", { ascending: false });

    if (error) return res.status(500).json({ error: error.message });

    res.status(200).json({
      success: true,
      count: data.length,
      analyses: data,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * ✅ PUT update a resume analysis by ID
 */
router.put("/update-analysis/:id", async (req, res) => {
  try {
    const token = req.headers.authorization?.split(" ")[1];
    if (!token) return res.status(401).json({ error: "No token provided" });

    const { data: { user }, error: userError } = await supabase.auth.getUser(token);
    if (userError || !user) return res.status(401).json({ error: "Invalid token" });

    const { id } = req.params;
    const { type, data } = req.body;

    if (!type && !data) {
      return res.status(400).json({ error: "Nothing to update" });
    }

    const updateFields = {};
    if (type) updateFields.type = type;
    if (data) updateFields.data = data;

    const { data: updatedAnalysis, error } = await supabase
      .from("resume_analysis")
      .update(updateFields)
      .eq("id", id)
      .eq("user_id", user.id)
      .select("id, type, data, created_at") // 🔒 return only safe fields
      .single();

    if (error) return res.status(400).json({ error: error.message });

    res.status(200).json({
      success: true,
      message: "Analysis updated successfully",
      analysis: updatedAnalysis,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;

// src/routes/auth.js
import express from "express";
import { supabase } from "../services/supabaseClient.js";

const router = express.Router();

/**
 * REGISTER
 * - Creates a new user in Supabase Auth
 * - Inserts an entry into profiles table with user_id
 */
router.post("/register", async (req, res) => {
  const { email, password, name, role } = req.body;

  try {
    // 1. Sign up user in Supabase Auth
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
    });

    if (error) return res.status(400).json({ error: error.message });
    const user = data.user;

    // 2. Insert into profiles table
    if (user) {
      const { error: profileError } = await supabase
        .from("profiles")
        .insert([
          {
            user_id: user.id,
            name: name || "",
            role: role || "user", // default role
          },
        ]);

      if (profileError) {
        return res.status(400).json({ error: profileError.message });
      }
    }

    res.json({ user });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * LOGIN
 * - Signs user in with email/password
 * - Returns session & user
 */
router.post("/login", async (req, res) => {
  const { email, password } = req.body;

  try {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) return res.status(400).json({ error: error.message });

    res.json({
      session: data.session,
      user: data.user,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * PROFILE
 * - Requires Bearer token
 * - Fetches user & profile info
 */
router.get("/profile", async (req, res) => {
  const token = req.headers.authorization?.split(" ")[1]; // Bearer <token>
  if (!token) return res.status(401).json({ error: "No token provided" });

  try {
    // 1. Get user from token
    const {
      data: { user },
      error,
    } = await supabase.auth.getUser(token);

    if (error || !user) {
      return res.status(401).json({ error: error?.message || "Invalid token" });
    }

    // 2. Fetch profile info
    const { data: profile, error: profileError } = await supabase
      .from("profiles")
      .select("*")
      .eq("user_id", user.id)
      .single();

    if (profileError) {
      return res.status(400).json({ error: profileError.message });
    }

    res.json({ user, profile });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * UPDATE PROFILE
 * - Requires Bearer token
 * - Updates profile fields (name, role, etc.)
 */
router.put("/profile", async (req, res) => {
  const token = req.headers.authorization?.split(" ")[1]; // Bearer <token>
  if (!token) return res.status(401).json({ error: "No token provided" });

  const { name, role } = req.body;

  try {
    // 1. Get user from token
    const {
      data: { user },
      error: userError,
    } = await supabase.auth.getUser(token);

    if (userError || !user) {
      return res.status(401).json({ error: userError?.message || "Invalid token" });
    }

    // 2. Update profile
    const { data: updatedProfile, error: updateError } = await supabase
      .from("profiles")
      .update({ name, role })
      .eq("user_id", user.id)
      .select()
      .single();

    if (updateError) {
      return res.status(400).json({ error: updateError.message });
    }

    res.json({ profile: updatedProfile });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;



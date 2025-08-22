// src/routes/auth.js
import express from "express";
import { supabase } from "../services/supabaseClient.js";

const router = express.Router();

/**
 * REGISTER
 * - Creates a new user in Supabase Auth
 * - Inserts an entry into profiles table with user_id, name, phone, role, terms acceptance
 */
router.post("/register", async (req, res) => {
  const { fullName, email, phone, password, confirmPassword, agreed } = req.body;

  try {
    // 1. Validate password match
    if (password !== confirmPassword) {
      return res.status(400).json({ error: "Passwords do not match" });
    }

    // 2. Check terms acceptance
    if (!agreed) {
      return res.status(400).json({ error: "You must accept the Terms & Conditions" });
    }

    // 3. Sign up user in Supabase Auth
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      phone, // optional, Supabase Auth supports phone if enabled
    });

    if (error) return res.status(400).json({ error: error.message });
    const user = data.user;

    // 4. Insert into profiles table
    if (user) {
      const { error: profileError } = await supabase
        .from("profiles")
        .insert([
          {
            user_id: user.id,
            name: fullName,
            phone: phone || "",
            role: "student",        // default role
            terms_accepted: agreed, // true
          },
        ]);

      if (profileError) {
        return res.status(400).json({ error: profileError.message });
      }
    }

    res.json({ user, message: "Registration successful" });
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
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
      return res.status(401).json({ error: error?.message || "Invalid token" });
    }

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
 * - Updates profile fields (name, role, phone, etc.)
 */
router.put("/profile", async (req, res) => {
  const token = req.headers.authorization?.split(" ")[1];
  if (!token) return res.status(401).json({ error: "No token provided" });

  const { name, role, phone } = req.body;

  try {
    const { data: { user }, error: userError } = await supabase.auth.getUser(token);

    if (userError || !user) {
      return res.status(401).json({ error: userError?.message || "Invalid token" });
    }

    const { data: updatedProfile, error: updateError } = await supabase
      .from("profiles")
      .update({ name, role, phone })
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

/**
 * LOGOUT
 * - Requires Bearer token
 * - Signs user out (revokes refresh token)
 */
router.post("/logout", async (req, res) => {
  const token = req.headers.authorization?.split(" ")[1]; // Bearer <token>
  if (!token) return res.status(401).json({ error: "No token provided" });

  try {
    const { error } = await supabase.auth.signOut();

    if (error) {
      return res.status(400).json({ error: error.message });
    }

    res.json({ message: "Successfully logged out" });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});


export default router;

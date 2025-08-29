// src/routes/auth.js
import express from "express";
import { supabase } from "../services/supabaseClient.js";

const router = express.Router();

/**
 * REGISTER
 * - Creates a new user in Supabase Auth
 * - Inserts a profile using Service Role (bypassing RLS)
 */
router.post("/register", async (req, res) => {
  const { fullName, email, phone, password, confirmPassword, agreed } = req.body;

  try {
    if (password !== confirmPassword) {
      return res.status(400).json({ error: "Passwords do not match" });
    }
    if (!agreed) {
      return res.status(400).json({ error: "You must accept the Terms & Conditions" });
    }

    // 1️⃣ Create user in Supabase Auth
    const { data: authData, error: authError } = await supabase.auth.admin.createUser({
      email,
      password,
      user_metadata: { phone },
      email_confirm: true, // auto-confirm email
    });

    if (authError) return res.status(400).json({ error: authError.message });
    const user = authData.user;
    if (!user?.id) return res.status(400).json({ error: "User creation failed" });

    // 2️⃣ Insert profile using Service Role key (bypassing RLS)
    // Note: This uses your server-side supabase client initialized with SERVICE_ROLE_KEY
    const { data: profileData, error: profileError } = await supabase
      .from("profiles")
      .insert([
        {
          user_id: user.id,
          name: fullName,
          phone: phone || "",
          role: "student",
          terms_accepted: agreed,
        },
      ])
      .select()
      .single();

    if (profileError) return res.status(400).json({ error: profileError.message });

    res.json({ user, profile: profileData, message: "Registration successful" });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});


/**
 * LOGIN
 */
router.post("/login", async (req, res) => {
  const { email, password } = req.body;

  try {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) return res.status(400).json({ error: error.message });

    // ✅ Return access_token so frontend can use it in Authorization header
    res.json({
      token: data.session?.access_token,
      refreshToken: data.session?.refresh_token,
      user: data.user,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * GET PROFILE
 */
router.get("/profile", async (req, res) => {
  const token = req.headers.authorization?.split(" ")[1];
  if (!token) return res.status(401).json({ error: "No token provided" });

  try {
    // ✅ Validate token & get user
    const { data: { user }, error: userError } = await supabase.auth.getUser(token);
    if (userError || !user) {
      return res.status(401).json({ error: userError?.message || "Invalid token" });
    }

    // ✅ Fetch user profile from profiles table
    const { data: profile, error: profileError } = await supabase
      .from("profiles")
      .select("*")
      .eq("user_id", user.id)
      .single();

    if (profileError) return res.status(400).json({ error: profileError.message });

    res.json({ user, profile });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * UPDATE PROFILE
 */
router.put("/profile", async (req, res) => {
  const token = req.headers.authorization?.split(" ")[1];
  if (!token) return res.status(401).json({ error: "No token provided" });

  const { name, role, phone } = req.body;

  try {
    const { data: { user }, error: userError } = await supabase.auth.getUser(token);
    if (userError || !user) return res.status(401).json({ error: userError?.message || "Invalid token" });

    const { data: updatedProfile, error: updateError } = await supabase
      .from("profiles")
      .update({ name, role, phone })
      .eq("user_id", user.id)
      .select()
      .single();

    if (updateError) return res.status(400).json({ error: updateError.message });

    res.json({ profile: updatedProfile });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * LOGOUT
 */
router.post("/logout", async (req, res) => {
  try {
    const { error } = await supabase.auth.signOut();
    if (error) return res.status(400).json({ error: error.message });

    res.json({ message: "Successfully logged out" });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;

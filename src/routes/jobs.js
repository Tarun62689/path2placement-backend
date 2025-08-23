import express from "express";
import axios from "axios";
import dotenv from "dotenv";

dotenv.config(); // Load .env file

const router = express.Router();

// Fetch from env
const APP_ID = process.env.ADZUNA_APP_ID;
const APP_KEY = process.env.ADZUNA_APP_KEY;

// Example route: GET /api/jobs?what=Java&where=Bangalore
router.get("/", async (req, res) => {
  try {
    const { what, where } = req.query;

    const url = `https://api.adzuna.com/v1/api/jobs/in/search/1?app_id=${APP_ID}&app_key=${APP_KEY}&what=${encodeURIComponent(
      what || ""
    )}&where=${encodeURIComponent(where || "")}`;

    const response = await axios.get(url);

    res.json(response.data); // send Adzuna response to frontend
  } catch (error) {
    console.error("Error fetching jobs:", error.message);
    res.status(500).json({ error: "Failed to fetch jobs" });
  }
});

export default router;

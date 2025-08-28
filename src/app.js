import express from "express";
import bodyParser from "body-parser";
import cors from "cors";
import dotenv from "dotenv";
import mlRoutes from "./routes/PlacementPrediction.js";
import CollegeInsightsRoutes from "./routes/CollegeInsights.js";
import CollegeFinderRoutes from "./routes/Collegefinder.js";
import jobsRoutes from "./routes/jobs.js";
import resumeAnalyzerRoutes from "./routes/resumeAnalyzer.js";
import resumeRoutes from "./routes/resume.js";
import resumeAnalysisFetchRoutes from "./routes/resumeAnalysisFetch.js";
import CollegeGrowthRoutes from "./routes/CollegeGrowth.js";
import authRoutes from "./routes/auth.js";

const app = express();

dotenv.config();

// ✅ CORS Configuration
const allowedOrigins = [
  "http://localhost:5173", // React dev
  "http://localhost:3000", // in case you run React on 3000
  "https://path2placement-frontend.onrender.com", // your deployed frontend
];

app.use(
  cors({
    origin: function (origin, callback) {
      if (!origin || allowedOrigins.includes(origin)) {
        callback(null, true);
      } else {
        callback(new Error("Not allowed by CORS"));
      }
    },
    credentials: true, // allow cookies/auth headers
  })
);

// Middlewares
app.use(bodyParser.json());

// Routes
app.use("/api/ml", mlRoutes);
app.use("/api/college-insights", CollegeInsightsRoutes);
app.use("/api/college-finder", CollegeFinderRoutes);
app.use("/api/jobs", jobsRoutes);
app.use("/api/resume-analyzer", resumeAnalyzerRoutes);
app.use("/api/resume", resumeRoutes);
app.use("/api/resume-analysis", resumeAnalysisFetchRoutes);
app.use("/api/college-growth", CollegeGrowthRoutes);
app.use("/api/auth", authRoutes);

// Health check
app.get("/", (req, res) => res.send("🚀 Path2Placement Backend Running 🚀"));

export default app;

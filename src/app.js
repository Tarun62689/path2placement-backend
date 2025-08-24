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

// Middlewares
app.use(cors());
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

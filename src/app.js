import express from "express";
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

dotenv.config();

const app = express();

// ✅ CORS Configuration
const allowedOrigins = [
  "http://localhost:5173", // React dev
  "http://localhost:3000", // fallback React dev port
  "https://path2placement-frontend.onrender.com",
  "https://path2placement.netlify.app", // deployed frontend
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
    credentials: true,
  })
);

// ✅ Middlewares
app.use(express.json()); // replace bodyParser.json()
app.use(express.urlencoded({ extended: true })); // parse URL-encoded bodies

// ✅ Routes
app.use("/api/ml", mlRoutes);
app.use("/api/college-insights", CollegeInsightsRoutes);
app.use("/api/college-finder", CollegeFinderRoutes);
app.use("/api/jobs", jobsRoutes);
app.use("/api/resume-analyzer", resumeAnalyzerRoutes);
app.use("/api/resume", resumeRoutes);
app.use("/api/resume-analysis", resumeAnalysisFetchRoutes);
app.use("/api/college-growth", CollegeGrowthRoutes);
app.use("/api/auth", authRoutes);

// ✅ Health check
app.get("/", (req, res) => res.send("🚀 Path2Placement Backend Running 🚀"));

// ✅ 404 handler
app.use((req, res, next) => {
  res.status(404).json({ error: "Route not found" });
});

// ✅ Error-handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: err.message || "Internal Server Error" });
});

export default app;

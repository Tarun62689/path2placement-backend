import express from "express";
import bodyParser from "body-parser";
import cors from "cors";
import dotenv from "dotenv";
import mlRoutes from "./routes/ml.js";
import authRoutes from "./routes/auth.js";

const app = express();

dotenv.config();

// Middlewares
app.use(cors());
app.use(bodyParser.json());

// Routes
app.use("/api/ml", mlRoutes);
app.use("/api/auth", authRoutes);

// Health check
app.get("/", (req, res) => res.send("🚀 Path2Placement Backend Running 🚀"));

export default app;

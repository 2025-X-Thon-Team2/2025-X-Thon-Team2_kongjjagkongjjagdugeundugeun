const express = require('express');
const router = express.Router();
const fs = require('fs/promises');
const path = require('path');
const { callGpt } = require('../services/openAiService');
const { callGemini } = require('../services/geminiService');

const dbPath = path.join(__dirname, '../../project_db.json');

// Function to read the database
const readDb = async () => {
    try {
        const data = await fs.readFile(dbPath, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        if (error.code === 'ENOENT') {
            // If file doesn't exist, initialize with empty array
            return [];
        }
        throw error;
    }
};

// Function to write to the database
const writeDb = async (data) => {
    await fs.writeFile(dbPath, JSON.stringify(data, null, 2));
};

/**
 * Main debate endpoint
 * POST /api/ask
 * body: { question: string, projectId?: string }
 */
router.post('/ask', async (req, res) => {
    // Implementation will follow
    res.status(501).json({ message: "Not Implemented" });
});

/**
 * Verification loop endpoint
 * POST /api/verify
 */
router.post('/verify', async (req, res) => {
    // Implementation will follow
    res.status(501).json({ message: "Not Implemented" });
});

/**
 * Finalize debate endpoint
 * POST /api/finalize
 */
router.post('/finalize', async (req, res) => {
    // Implementation will follow
    res.status(501).json({ message: "Not Implemented" });
});

/**
 * Get scores endpoint
 * GET /api/score/:projectId
 */
router.get('/score/:projectId', async (req, res) => {
    // Implementation will follow
    res.status(501).json({ message: "Not Implemented" });
});

/**
 * Get history list endpoint
 * GET /api/history/list
 */
router.get('/history/list', async (req, res) => {
    // Implementation will follow
    res.status(501).json({ message: "Not Implemented" });
});


module.exports = router;

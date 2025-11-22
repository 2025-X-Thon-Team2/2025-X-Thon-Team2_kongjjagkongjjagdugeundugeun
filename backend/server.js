require('dotenv').config();
const express = require('express');
const cors = require('cors');

const app = express();
const port = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.status(200).json({ status: 'ok', message: 'Server is running' });
});

// Placeholder for future API routes
// const debateRoutes = require('./src/api/routes/debate');
// app.use('/api', debateRoutes);

app.listen(port, () => {
  console.log(`Backend server listening at http://localhost:${port}`);
});

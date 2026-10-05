const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

// Test route - Vercel check ke liye
app.get('/', (req, res) => {
  res.json({ message: 'VidSwift Backend Working on Vercel!' });
});

// Yahan aapke baaki routes honge
// app.use('/api/download', ...)

module.exports = app;

const express = require("express");

const app = express();
const PORT = 8080;

// JSON-Body lesen
app.use(express.json());

// Alle Requests loggen
app.use((req, res, next) => {
  console.log("---- Incoming Request ----");
  console.log("Method:", req.method);
  console.log("URL:", req.originalUrl);
  console.log("Headers:", req.headers);
  console.log("Body:", req.body);
  console.log("--------------------------");
  next();
});

// Test-Endpunkt
app.all('/PM', (req, res) => {
  res.json({ status: "ok" });
});

app.listen(PORT, () => {
  console.log(`Server läuft auf http://localhost:${PORT}`);
});

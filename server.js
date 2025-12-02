const express = require('express');
const app = express();
const port = process.env.PORT || 3000; // Menggunakan variabel PORT dari Koyeb

app.get('/', (req, res) => {
  res.send('Bot Discord Fish-it is Running!');
});

app.listen(port, () => {
  console.log(`Keep-alive server berjalan di port ${port}`);
});

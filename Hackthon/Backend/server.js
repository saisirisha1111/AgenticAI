// // server.js
// const WebSocket = require('ws');
// const http = require('http');

// // Use Gitpod's port
// const PORT = process.env.PORT || 4000;

// // Create HTTP server
// const server = http.createServer((req, res) => {
//   res.writeHead(200);
//   res.end('WebSocket server is running');
// });

// // Create WebSocket server, bound to HTTP server
// const wss = new WebSocket.Server({ noServer: true });

// wss.on('connection', (ws) => {
//   console.log('Client connected');

//   ws.on('message', (message) => {
//     console.log('Received:', message);
//     ws.send(`Server received: ${message}`);
//   });

//   ws.on('close', () => {
//     console.log('Client disconnected');
//   });
// });

// // Handle WebSocket upgrade
// server.on('upgrade', (request, socket, head) => {
//   wss.handleUpgrade(request, socket, head, (ws) => {
//     wss.emit('connection', ws, request);
//   });
// });

// server.listen(PORT, () => {
//   console.log(`Server running on port ${PORT}`);
// });

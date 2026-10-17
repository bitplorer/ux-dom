// Client for examples/standalone/ws.py. Loaded from a file, so a nonce CSP
// allows it (the CSP runtime stamps the <script> tag).
(() => {
  const button = document.getElementById("bump");
  const output = document.getElementById("n");
  const scheme = location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${scheme}//${location.host}${button.dataset.socket}`);

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.event === "hello" || message.event === "update") {
      output.textContent = String(message.data.n);
    }
  });
  button.addEventListener("click", () => {
    socket.send(JSON.stringify({ event: "bump", data: { delta: 1 } }));
  });
})();

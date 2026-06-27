const BRIDGE_URL = "ws://127.0.0.1:9229";

const statusEl = document.getElementById("status");

chrome.runtime.sendMessage({ type: "status" }, (resp) => {
  if (!resp) {
    statusEl.textContent = "Background unavailable";
    statusEl.className = "bad";
    return;
  }
  if (resp.connected) {
    statusEl.textContent = "Connected to Engine bridge";
    statusEl.className = "ok";
  } else {
    statusEl.textContent = "Not connected — start ./engine serve and reload";
    statusEl.className = "bad";
  }
});

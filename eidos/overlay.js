// Visible cursor + click ripple, injected into recordings.
// Screen-recording tools (Loom, Screen Studio, OBS plugins) draw the same kind
// of overlay, so tutorial videos usually show where the pointer is and when it
// clicks. EIDOS reads these cues from pixels; it never sees this script.
(() => {
  if (window.__eidosOverlay) return;
  window.__eidosOverlay = true;
  const color = window.__EIDOS_CURSOR_COLOR || "#ff2d6f";
  const cur = document.createElement("div");
  cur.id = "__eidos_cursor";
  cur.innerHTML =
    '<svg width="26" height="30" viewBox="0 0 26 30"><path d="M2 2 L2 24 L8 18.5 L12.5 28 L16.5 26.2 L12 17 L20 17 Z" fill="' +
    color + '" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>';
  Object.assign(cur.style, {
    position: "fixed", left: "-50px", top: "-50px", zIndex: 2147483647,
    pointerEvents: "none", transform: "translate(-2px,-2px)",
    filter: "drop-shadow(0 1px 2px rgba(0,0,0,.35))",
  });
  const add = () => document.body && document.body.appendChild(cur);
  if (document.body) add(); else document.addEventListener("DOMContentLoaded", add);
  document.addEventListener("mousemove", e => {
    cur.style.left = e.clientX + "px"; cur.style.top = e.clientY + "px";
  }, true);
  document.addEventListener("mousedown", e => {
    const r = document.createElement("div");
    Object.assign(r.style, {
      position: "fixed", left: e.clientX - 18 + "px", top: e.clientY - 18 + "px",
      width: "36px", height: "36px", borderRadius: "50%",
      border: "4px solid " + color, zIndex: 2147483646, pointerEvents: "none",
      opacity: "1", transition: "transform .45s ease-out, opacity .45s ease-out",
    });
    document.body.appendChild(r);
    requestAnimationFrame(() => { r.style.transform = "scale(1.6)"; r.style.opacity = "0"; });
    setTimeout(() => r.remove(), 500);
  }, true);
})();

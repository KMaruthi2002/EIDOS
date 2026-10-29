// Interruption condition: a "What's new" dialog appears partway through the
// task (?popup=SECONDS). While open it blocks all pointer and keyboard input.
// It closes with its button or Escape, as most product tours do.
(() => {
  const q = new URLSearchParams(location.search);
  const after = parseFloat(q.get("popup"));
  if (!(after >= 0)) return;
  setTimeout(() => {
    const shade = document.createElement("div");
    shade.id = "whatsnew";
    shade.innerHTML = `<div style="background:#fff;color:#1b2430;border-radius:12px;padding:22px 24px;width:340px;box-shadow:0 20px 60px rgba(0,0,0,.35);font:14px system-ui">
      <div style="font-weight:700;font-size:17px;margin-bottom:6px">What's new</div>
      <div style="color:#55606e;margin-bottom:16px">Comments and version history are now in the sidebar.</div>
      <button id="whatsnew-ok" style="font:inherit;font-weight:600;padding:8px 14px;border-radius:8px;border:0;background:#2d5bff;color:#fff">Got it</button></div>`;
    Object.assign(shade.style, { position: "fixed", inset: "0", background: "rgba(10,16,24,.35)", display: "grid",
      placeItems: "center", zIndex: 2147483000 });
    const close = () => { shade.remove(); window.removeEventListener("keydown", trap, true); };
    const trap = (e) => {
      if (e.key === "Escape") close();
      e.stopPropagation(); e.preventDefault();
    };
    ["mousedown", "mouseup", "click"].forEach(t => shade.addEventListener(t, e => {
      e.stopPropagation();
      if (t === "click" && e.target.id === "whatsnew-ok") close();
    }));
    window.addEventListener("keydown", trap, true);
    document.body.appendChild(shade);
  }, after * 1000);
})();

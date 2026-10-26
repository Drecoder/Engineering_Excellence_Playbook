// Builds one carousel PDF per point from content.json: 5 square slides each (cover, problem,
// what we did, result, lesson), rendered as HTML and printed to PDF with headless Edge.
//   node build.js
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const here = __dirname;
const outDir = path.join(here, "pdf");
const htmlDir = path.join(here, "html");
fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(htmlDir, { recursive: true });

const points = JSON.parse(fs.readFileSync(path.join(here, "content.json"), "utf8"));
const SERIES = "The Self-Governing Platform";
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const css = `
  @page { size: 1080px 1080px; margin: 0; }
  :root { --bg:#0f172a; --panel:#1e293b; --ink:#f1f5f9; --muted:#94a3b8; --accent:#38bdf8; --ok:#4ade80; --warn:#fbbf24; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { background: var(--bg); }
  body { font-family: "Segoe UI", system-ui, sans-serif; color: var(--ink); -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .slide { width:1080px; height:1080px; padding:96px 92px; position:relative; display:flex; flex-direction:column;
    break-after: page; page-break-after: always; overflow: hidden;
    background: radial-gradient(circle at 88% 8%, #1e3a5f 0, transparent 46%), var(--bg); }
  .slide:last-child { break-after: auto; page-break-after: auto; }
  .kicker { font-size:26px; letter-spacing:3px; text-transform:uppercase; color:var(--accent); font-weight:600; }
  .cover h1 { font-size:76px; line-height:1.1; font-weight:700; margin-top:auto; }
  .cover .sub { font-size:34px; line-height:1.35; color:var(--muted); margin-top:30px; margin-bottom:120px; }
  h2 { font-size:58px; line-height:1.12; font-weight:700; margin-top:20px; }
  .para { font-size:36px; line-height:1.45; margin-top:40px; color:var(--ink); }
  .para + .para { color: var(--muted); }
  ul { list-style:none; margin-top:44px; display:flex; flex-direction:column; gap:26px; }
  li { font-size:33px; line-height:1.38; padding-left:44px; position:relative; }
  li::before { content:""; position:absolute; left:0; top:16px; width:18px; height:18px; border-radius:5px; background:var(--accent); }
  .stats { display:flex; flex-direction:column; gap:26px; margin-top:48px; }
  .stat { background:var(--panel); border-radius:24px; padding:30px 36px; display:flex; align-items:center; gap:36px; }
  .stat .n { font-size:72px; font-weight:700; color:var(--accent); line-height:1; min-width:210px; }
  .stat .l { font-size:32px; color:var(--ink); line-height:1.3; }
  .lesson { margin-top:52px; background:var(--panel); border-left:10px solid var(--warn); border-radius:16px; padding:40px 42px; font-size:44px; line-height:1.35; font-weight:600; }
  .cta { margin-top:auto; margin-bottom:70px; font-size:28px; color:var(--muted); line-height:1.4; }
  .foot { position:absolute; left:92px; right:92px; bottom:56px; display:flex; justify-content:space-between; font-size:22px; color:var(--muted); }
`;

function carousel(p, index, total) {
  const n = `${String(index + 1).padStart(2, "0")} / ${String(total).padStart(2, "0")}`;
  const foot = (i) => `<div class="foot"><span>${esc(SERIES)}</span><span>${i} / 5${i < 5 ? "  →" : ""}</span></div>`;
  const slides = [
    `<section class="slide cover"><div class="kicker">${esc(p.kicker)} · Part ${n}</div>
       <h1>${esc(p.title)}</h1><p class="sub">${esc(p.sub)}</p>${foot(1)}</section>`,
    `<section class="slide"><div class="kicker">The problem</div><h2>Where we started</h2>
       ${p.problem.map((t) => `<p class="para">${esc(t)}</p>`).join("")}${foot(2)}</section>`,
    `<section class="slide"><div class="kicker">What we did</div><h2>The changes</h2>
       <ul>${p.did.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>${foot(3)}</section>`,
    `<section class="slide"><div class="kicker">The result</div><h2>By the numbers</h2>
       <div class="stats">${p.stats.map(([v, l]) => `<div class="stat"><div class="n">${esc(v)}</div><div class="l">${esc(l)}</div></div>`).join("")}</div>${foot(4)}</section>`,
    `<section class="slide"><div class="kicker">The lesson</div><h2>What we'd tell another team</h2>
       <div class="lesson">${esc(p.lesson)}</div>
       <p class="cta">${esc(SERIES)}, part ${n}: building a cost-aware AI development platform that governs itself.</p>${foot(5)}</section>`,
  ];
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${esc(p.kicker)}</title><style>${css}</style></head><body>${slides.join("\n")}</body></html>`;
}

const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

// Headless Edge can return before the PDF is on disk, so wait for it, and retry once.
function printPdf(html, pdf) {
  for (let attempt = 1; attempt <= 2; attempt++) {
    fs.rmSync(pdf, { force: true });
    // A separate profile keeps headless Edge from attaching to an Edge window that is already open.
    const profile = fs.mkdtempSync(path.join(require("os").tmpdir(), "carousel-edge-"));
    try {
      execFileSync(EDGE, ["--headless=new", "--disable-gpu", "--no-first-run", `--user-data-dir=${profile}`, "--no-pdf-header-footer", `--print-to-pdf=${pdf}`, "file:///" + html.replace(/\\/g, "/")], { stdio: "ignore", timeout: 120000 });
    } catch {
      // checked below
    }
    for (let i = 0; i < 60 && !(fs.existsSync(pdf) && fs.statSync(pdf).size > 0); i++) sleep(500);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch { /* Edge may still hold it briefly */ }
    if (fs.existsSync(pdf) && fs.statSync(pdf).size > 0) return;
  }
  throw new Error(`could not print ${pdf}`);
}

points.forEach((p, i) => {
  const html = path.join(htmlDir, `${p.slug}.html`);
  const pdf = path.join(outDir, `${p.slug}.pdf`);
  fs.writeFileSync(html, carousel(p, i, points.length));
  printPdf(html, pdf);
  console.log(`${p.slug}.pdf ${fs.statSync(pdf).size} bytes`);
});

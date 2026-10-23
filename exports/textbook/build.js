// Builds the Engineering Excellence textbook from the playbook's own Markdown plus book.json
// (parts, chapters, learning objectives, takeaways, review questions, glossary), then prints it
// to PDF with headless Edge.   node build.js
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = __dirname;
// The containerized build (Dockerfile here) sets BROWSER to Chromium; a host build falls back to Edge.
const BROWSER = process.env.BROWSER || "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const BROWSER_FLAGS = (process.env.BROWSER_FLAGS || "").split(" ").filter(Boolean);
const MarkdownIt = require(findMarkdownIt());
const md = new MarkdownIt({ html: false, linkify: false, typographer: true });
const book = JSON.parse(fs.readFileSync(path.join(OUT, "book.json"), "utf8"));

/** Docs whose $...$ is LaTeX math (everywhere else a dollar sign is just a dollar sign). */
const MATH_FILES = new Set(["docs/PHYSICS_OF_FLOW.md", "00_UniversalStandards/04_CONCURRENCY_GOVERNORS.md"]);

function findMarkdownIt() {
  try {
    return require.resolve("markdown-it");
  } catch {
    // host build without a local install: fall back to the npx cache
  }
  const cache = path.join(process.env.LOCALAPPDATA || "", "npm-cache", "_npx");
  for (const dir of fs.readdirSync(cache)) {
    const candidate = path.join(cache, dir, "node_modules", "markdown-it");
    if (fs.existsSync(path.join(candidate, "package.json"))) return candidate;
  }
  throw new Error("markdown-it not found in the npx cache");
}

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
/** Drop emoji keycaps and decorative symbols from the front of a heading, and "1." numbering. */
const cleanHeading = (t) =>
  t
    .replace(/^([0-9]\uFE0F?\u20E3|\u{1F51F})+[a-z]?\s*/u, "")
    .replace(/^[\p{Extended_Pictographic}\uFE0F\u200D]+\s*/u, "")
    .replace(/^\d+\.\s+/, "")
    .trim();

// ---- numbering and cross-references ----
const chapters = [];
book.parts.forEach((part, p) => part.chapters.forEach((ch) => chapters.push({ ...ch, part: p })));
chapters.forEach((ch, i) => (ch.number = i + 1));
const appendixLetter = (i) => String.fromCharCode(65 + i);

const xref = new Map(); // basename -> label
for (const ch of chapters) for (const src of ch.sources) xref.set(path.basename(src), `Chapter ${ch.number}, ${ch.title}`);
book.appendices.forEach((a, i) => a.source && xref.set(path.basename(a.source), `Appendix ${appendixLetter(i)}, ${a.title}`));
const contractsLabel = `Appendix ${appendixLetter(book.appendices.findIndex((a) => a.contracts))}, Contracts`;

/** Turn `path/to/doc.md` (optionally followed by §n) into a readable chapter reference. */
function crossReference(html) {
  return html.replace(/<code>([^<]*?\.(md|json))<\/code>/g, (whole, p) => {
    const base = path.basename(p.replace(/^\.playbook\//, ""));
    if (p.endsWith(".json") && /schemas\//.test(p)) return `<span class="xref">${esc(contractsLabel)}</span>`;
    const label = xref.get(base);
    return label ? `<span class="xref">${esc(label)}</span>` : whole;
  });
}

/** Render one playbook document as a numbered section of a chapter. */
function renderSource(rel, sectionNumber) {
  let text = fs.readFileSync(path.join(ROOT, rel), "utf8").replace(/\r\n/g, "\n");
  const lines = text.split("\n");
  const h1 = lines.findIndex((l) => /^# /.test(l));
  const title = h1 >= 0 ? cleanHeading(lines[h1].slice(2)) : path.basename(rel, ".md");
  if (h1 >= 0) lines.splice(h1, 1);
  text = lines
    .filter((l) => !/^---\s*$/.test(l))
    .map((l) => (/^#{2,5} /.test(l) ? l.replace(/^(#+) (.*)$/, (_, h, t) => `${h}# ${cleanHeading(t)}`) : l))
    .join("\n");

  const math = [];
  if (MATH_FILES.has(rel)) {
    text = text
      .replace(/\$\$([\s\S]+?)\$\$/g, (_, m) => `@@MATH${math.push(`\\[${m}\\]`) - 1}@@`)
      .replace(/\$([^$\n]+?)\$/g, (_, m) => `@@MATH${math.push(`\\(${m}\\)`) - 1}@@`);
  }
  let html = md.render(text).replace(/@@MATH(\d+)@@/g, (_, i) => esc(math[Number(i)]));
  html = crossReference(html);
  return `<section class="source" id="s-${sectionNumber.replace(".", "-")}">
    <h2><span class="num">${sectionNumber}</span> ${esc(title)}</h2>
    <div class="from">From <code>${esc(rel)}</code></div>
    ${html}
  </section>`;
}

const list = (items, cls) => `<ul class="${cls}">${items.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>`;

function renderChapter(ch) {
  const sections = ch.sources.map((src, i) => renderSource(src, `${ch.number}.${i + 1}`)).join("\n");
  return `<article class="chapter" id="ch-${ch.number}">
    <div class="chapter-label">Chapter ${ch.number}</div>
    <h1>${esc(ch.title)}</h1>
    <div class="box objectives"><div class="box-title">In this chapter you will learn to</div>${list(ch.objectives, "")}</div>
    ${sections}
    <div class="box takeaways"><div class="box-title">Key takeaways</div>${list(ch.takeaways, "")}</div>
    <div class="box questions"><div class="box-title">Review questions</div><ol>${ch.questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ol></div>
  </article>`;
}

function renderContracts() {
  const dir = path.join(ROOT, "schemas");
  const rows = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .sort()
    .map((f) => {
      const j = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
      const kind = f.endsWith(".schema.json") ? "JSON Schema for a data file" : j.$schema ? "JSON Schema" : "Data";
      const desc = String(j.description ?? "").split(/(?<=\.)\s/)[0];
      return `<tr><td><code>${esc(f)}</code></td><td>${esc(kind)}</td><td>${esc(desc)}</td></tr>`;
    })
    .join("");
  return `<table><thead><tr><th>File</th><th>Kind</th><th>Purpose</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderAppendix(a, i) {
  const letter = appendixLetter(i);
  let body;
  if (a.contracts) body = renderContracts();
  else body = renderSource(a.source, letter).replace(/<h2>.*?<\/h2>/s, "");
  return `<article class="chapter appendix" id="app-${letter}">
    <div class="chapter-label">Appendix ${letter}</div>
    <h1>${esc(a.title)}</h1>
    <p class="lede">${esc(a.intro)}</p>
    ${body}
  </article>`;
}

function renderToc() {
  const parts = book.parts
    .map((part, p) =>
      !hasChapters(p) ? "" : `<li class="toc-part"><span>Part ${["I", "II", "III", "IV", "V", "VI", "VII"][p]}: ${esc(part.title)}</span>
        <ol>${chapters
          .filter((c) => c.part === p)
          .map((c) => `<li><a href="#ch-${c.number}">${c.number}. ${esc(c.title)}</a></li>`)
          .join("")}</ol></li>`,
    )
    .join("");
  const apps = book.appendices.map((a, i) => `<li><a href="#app-${appendixLetter(i)}">Appendix ${appendixLetter(i)}: ${esc(a.title)}</a></li>`).join("");
  return `<article class="frontmatter" id="toc"><h1>Contents</h1><ol class="toc">${parts}</ol>
    <ol class="toc toc-apps">${apps}<li><a href="#glossary">Glossary</a></li></ol></article>`;
}

function sourceRevision() {
  try {
    const sha = execFileSync("git", ["-c", "safe.directory=*", "-C", ROOT, "rev-parse", "--short", "HEAD"], { encoding: "utf8" }).trim();
    const branch = execFileSync("git", ["-c", "safe.directory=*", "-C", ROOT, "rev-parse", "--abbrev-ref", "HEAD"], { encoding: "utf8" }).trim();
    return `${branch} @ ${sha}`;
  } catch {
    return "unknown revision";
  }
}

// PREVIEW=2,5 renders only those chapters (plus cover and contents) to a short preview PDF for review.
const preview = process.env.PREVIEW ? new Set(process.env.PREVIEW.split(",").map(Number)) : null;
if (preview) {
  for (const part of book.parts) part.chapters = part.chapters.filter((c) => preview.has(chapters.find((x) => x.title === c.title).number));
  chapters.splice(0, chapters.length, ...chapters.filter((c) => preview.has(c.number)));
  book.appendices = [];
}
/** Parts keep their original index (chapters refer to it); empty parts are skipped when rendering. */
const hasChapters = (p) => chapters.some((c) => c.part === p);

const css = fs.readFileSync(path.join(OUT, "book.css"), "utf8");
const roman = ["I", "II", "III", "IV", "V", "VI", "VII"];
const body = [
  `<section class="cover"><div class="cover-series">${esc(book.series)}</div><h1>${esc(book.title)}</h1><p class="cover-sub">${esc(book.subtitle)}</p></section>`,
  preview ? "" : `<article class="frontmatter edition"><p>Built ${new Date().toISOString().slice(0, 10)} from the Engineering Excellence Playbook, ${esc(sourceRevision())}. The chapters reproduce the playbook's documents; learning objectives, takeaways, review questions, and the glossary were added for this edition.</p></article>`,
  renderToc(),
  preview ? "" : `<article class="frontmatter" id="preface"><h1>Preface</h1>${book.preface.map((p) => `<p>${esc(p)}</p>`).join("")}
    <h2>How to use this book</h2>${list(book.howToUse, "")}</article>`,
  ...book.parts.map((part, p) =>
    !hasChapters(p) ? "" : `<section class="part-page"><div class="part-label">Part ${roman[p]}</div><h1>${esc(part.title)}</h1><p>${esc(part.intro)}</p></section>
      ${chapters.filter((c) => c.part === p).map(renderChapter).join("\n")}`,
  ),
  ...book.appendices.map(renderAppendix),
  preview ? "" : `<article class="chapter appendix" id="glossary"><div class="chapter-label">Reference</div><h1>Glossary</h1><dl class="glossary">${book.glossary
    .map(([t, d]) => `<dt>${esc(t)}</dt><dd>${esc(d)}</dd>`)
    .join("")}</dl></article>`,
].join("\n");

const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${esc(book.title)}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" onload="renderMathInElement(document.body,{delimiters:[{left:'\\\\[',right:'\\\\]',display:true},{left:'\\\\(',right:'\\\\)',display:false}]})"></script>
<style>${css}</style></head><body>${body}</body></html>`;

const name = preview ? "preview" : "engineering-excellence-textbook";
const htmlFile = path.join(OUT, `${name}.html`);
const pdfFile = path.join(OUT, `${name}.pdf`);
fs.writeFileSync(htmlFile, html);

const profile = fs.mkdtempSync(path.join(os.tmpdir(), "textbook-edge-"));
fs.rmSync(pdfFile, { force: true });
try {
  execFileSync(BROWSER, ["--headless=new", "--disable-gpu", "--no-first-run", ...BROWSER_FLAGS, `--user-data-dir=${profile}`, "--virtual-time-budget=10000", "--no-pdf-header-footer", `--print-to-pdf=${pdfFile}`, require("url").pathToFileURL(htmlFile).href], { stdio: "ignore", timeout: 180000 });
} catch {
  // checked below
}
const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
for (let i = 0; i < 60 && !(fs.existsSync(pdfFile) && fs.statSync(pdfFile).size > 0); i++) sleep(500);
if (!fs.existsSync(pdfFile)) throw new Error("PDF was not written");
console.log(`chapters=${chapters.length} appendices=${book.appendices.length} pdf=${fs.statSync(pdfFile).size} bytes`);

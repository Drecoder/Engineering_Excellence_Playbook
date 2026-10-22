"""
Verify antipatterns.v1 detector mappings by running the real tools on each rule's test cases.

Runs only inside the pinned toolchain image (tests/antipatterns/toolchain); nothing is verified with
host-installed tools. A mapping is verified when the detector reports exactly the catalog's rule_id
on every positive case and never on any negative case. Planned (custom rig) rules are skipped.

    docker run --rm -v "$PWD:/work" -e TOOLCHAIN_IMAGE=<image@sha256:...> \
        playbook-antipattern-toolchain python tests/antipatterns/verify_detectors.py [--write]

--write records verified mappings in schemas/antipatterns.v1.json (status, tool_version,
verified_on, verified_in, toolchain). It never downgrades a mapping and never changes enforcement.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "schemas" / "antipatterns.v1.json"
ESLINT_HOME = Path(os.environ.get("ESLINT_WORKDIR", "/opt/eslint/work"))
TIMEOUT = 300

ESLINT_TOOLS = {"eslint", "typescript-eslint", "eslint-plugin-n", "eslint-plugin-react",
                "eslint-plugin-react-hooks", "angular-eslint", "eslint-plugin-rxjs-x"}

ESLINT_CONFIG = """import tseslint from 'typescript-eslint';
import react from 'eslint-plugin-react';
import hooks from 'eslint-plugin-react-hooks';
import n from 'eslint-plugin-n';
import angular from '@angular-eslint/eslint-plugin';
import rxjsX from 'eslint-plugin-rxjs-x';
export default [{
  files: ['**/*.ts', '**/*.tsx', '**/*.js'],
  languageOptions: {
    parser: tseslint.parser,
    parserOptions: { projectService: { allowDefaultProject: ['*.js'] }, tsconfigRootDir: import.meta.dirname, ecmaFeatures: { jsx: true } },
  },
  plugins: { '@typescript-eslint': tseslint.plugin, react, 'react-hooks': hooks, n, '@angular-eslint': angular, 'rxjs-x': rxjsX },
  settings: { react: { version: '19.0' } },
  rules: { 'RULE': 'error' },
}];
"""

TSCONFIG = {
    "compilerOptions": {
        "strict": True, "target": "ES2022", "module": "ESNext", "moduleResolution": "Bundler",
        "jsx": "react-jsx", "experimentalDecorators": True, "skipLibCheck": True, "allowJs": True,
        "types": [],
    },
    "include": ["**/*.ts", "**/*.tsx"],
}


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
    return p.stdout, p.stderr


def version(cmd):
    out, err = run(cmd, "/")
    text = (out or err).strip().splitlines()
    return text[0].strip() if text else "unknown"


# Each detector returns the set of rule IDs it reported for the project in `d`.

def go_vet(d):
    (d / "go.mod").write_text("module x\n\ngo 1.26\n")
    out, _ = run(["go", "vet", "-json", "./..."], d)  # -json writes to stdout
    ids = set()
    for blob in re.findall(r"^\{.*?^\}", out, re.S | re.M):
        for analyzers in json.loads(blob).values():
            ids.update(analyzers.keys())
    return ids


def staticcheck(d):
    (d / "go.mod").write_text("module x\n\ngo 1.26\n")
    out, _ = run(["staticcheck", "-f", "json", "./..."], d)
    return {json.loads(l)["code"] for l in out.splitlines() if l.strip()}


def eslint(d, rule):
    (d / "eslint.config.mjs").write_text(ESLINT_CONFIG.replace("RULE", rule))
    (d / "tsconfig.json").write_text(json.dumps(TSCONFIG))
    out, err = run(["eslint", "--format", "json", "--no-warn-ignored", "."], d)
    try:
        results = json.loads(out)
    except json.JSONDecodeError:
        raise RuntimeError(f"eslint failed: {err.strip()[:400]}")
    ids = set()
    for f in results:
        for m in f["messages"]:
            if m.get("fatal"):
                raise RuntimeError(f"eslint parse error: {m['message']}")
            if m.get("ruleId"):
                ids.add(m["ruleId"])
    return ids


def ruff(d, rule):
    out, _ = run(["ruff", "check", "--isolated", "--no-cache", "--select", rule, "--output-format", "json", "."], d)
    return {r["code"] for r in json.loads(out or "[]")}


def bandit(d):
    out, _ = run(["bandit", "-r", ".", "-f", "json", "-q"], d)
    return {r["test_id"] for r in json.loads(out or "{}").get("results", [])}


def semgrep(d, config):
    out, err = run(["semgrep", "scan", "--metrics=off", "--quiet", "--json", "--config", config, "."], d)
    doc = json.loads(out or "{}")
    fatal = [e for e in doc.get("errors", []) if e.get("level") == "error"]
    if fatal:
        raise RuntimeError(f"semgrep error: {fatal[0].get('message')}")
    return {r["check_id"] for r in doc.get("results", [])}


def checkov(d, framework):
    out, _ = run(["checkov", "-d", ".", "--framework", framework, "-o", "json", "--quiet", "--compact"], d)
    doc = json.loads(out or "{}")
    reports = doc if isinstance(doc, list) else [doc]
    return {c["check_id"] for r in reports for c in r.get("results", {}).get("failed_checks", [])}


def trivy(d):
    out, _ = run(["trivy", "config", "--quiet", "--skip-check-update", "--format", "json", "."], d)
    doc = json.loads(out or "{}")
    return {m["ID"] for r in doc.get("Results") or [] for m in r.get("Misconfigurations") or [] if m.get("Status") == "FAIL"}


def tflint(d, rule):
    out, _ = run(["tflint", "--format", "json", "--enable-rule", rule], d)
    return {i["rule"]["name"] for i in json.loads(out or "{}").get("issues", [])}


def hadolint(d):
    ids = set()
    for f in d.rglob("Dockerfile*"):
        out, _ = run(["hadolint", "--no-fail", "--format", "json", str(f)], d)
        ids.update(i["code"] for i in json.loads(out or "[]"))
    return ids


def zizmor(d, config):
    persona = dict(kv.split("=", 1) for kv in (config or "persona=regular").split(","))["persona"]
    out, err = run(["zizmor", "--offline", f"--persona={persona}", "--format", "json", "."], d)
    try:
        return {f["ident"] for f in json.loads(out or "[]")}
    except json.JSONDecodeError:
        raise RuntimeError(f"zizmor failed: {err.strip()[:300]}")


def actionlint(d):
    files = [str(p) for p in d.rglob("*.yml")]
    out, err = run(["actionlint", "-format", "{{json .}}", *files], d)
    try:
        return {e["kind"] for e in json.loads(out or "[]")}
    except json.JSONDecodeError:
        raise RuntimeError(f"actionlint failed: {(out or err).strip()[:300]}")


def spectral(d, ruleset):
    (d / ".spectral.yaml").write_text(f'extends: ["{ruleset}"]\n')
    files = [str(p) for p in d.rglob("*.yaml") if p.name != ".spectral.yaml"]
    out, err = run(["spectral", "lint", *files, "-f", "json", "--quiet"], d)
    try:
        return {x["code"] for x in json.loads(out or "[]")}
    except json.JSONDecodeError:
        raise RuntimeError(f"spectral failed: {(out or err).strip()[:300]}")


def oasdiff(d, file):
    out, err = run(["oasdiff", "breaking", f"old/{file}", f"new/{file}", "--format", "json"], d)
    try:
        return {x["id"] for x in json.loads(out or "[]")}
    except json.JSONDecodeError:
        raise RuntimeError(f"oasdiff failed: {(out or err).strip()[:300]}")


def buf(d, mode):
    if mode == "breaking":
        for side in ("old", "new"):
            (d / side / "buf.yaml").write_text("version: v2\n")
        out, err = run(["buf", "breaking", "--against", "../old", "--error-format", "json"], d / "new")
    else:
        (d / "buf.yaml").write_text("version: v2\n")
        out, err = run(["buf", "lint", "--error-format", "json"], d)
    lines = [l for l in (out + err).splitlines() if l.strip().startswith("{")]
    return {json.loads(l)["type"] for l in lines}


def squawk(d):
    files = [str(p) for p in d.rglob("*.sql")]
    out, err = run(["squawk", "--reporter", "json", *files], d)
    try:
        return {v["rule_name"] for v in json.loads(out or "[]")}
    except json.JSONDecodeError:
        raise RuntimeError(f"squawk failed: {(out or err).strip()[:300]}")


def sqlfluff(d, rule, config):
    dialect = dict(kv.split("=", 1) for kv in config.split(","))["dialect"]
    files = [str(p) for p in d.rglob("*.sql")]
    out, err = run(["sqlfluff", "lint", "--dialect", dialect, "--rules", rule, "--format", "json", *files], d)
    try:
        return {v["code"] for f in json.loads(out or "[]") for v in f["violations"]}
    except json.JSONDecodeError:
        raise RuntimeError(f"sqlfluff failed: {(out or err).strip()[:300]}")


def kube_linter(d, check):
    out, err = run(["kube-linter", "lint", "--format", "json", "--include", check, "."], d)
    try:
        return {r["Check"] for r in json.loads(out or "{}").get("Reports") or []}
    except json.JSONDecodeError:
        raise RuntimeError(f"kube-linter failed: {(out or err).strip()[:300]}")


def shellcheck(d):
    files = [str(p) for p in d.rglob("*.sh")]
    out, err = run(["shellcheck", "-f", "json", *files], d)
    try:
        return {f"SC{x['code']}" for x in json.loads(out or "[]")}
    except json.JSONDecodeError:
        raise RuntimeError(f"shellcheck failed: {(out or err).strip()[:300]}")


VERSIONS = {
    "squawk": ["squawk", "--version"], "sqlfluff": ["sqlfluff", "--version"],
    "spectral": ["spectral", "--version"], "buf": ["buf", "--version"],
    "zizmor": ["zizmor", "--version"], "actionlint": ["actionlint", "-version"], "shellcheck": ["shellcheck", "--version"],
    "go-vet": ["go", "version"], "staticcheck": ["staticcheck", "-version"], "ruff": ["ruff", "--version"],
    "bandit": ["bandit", "--version"], "semgrep": ["semgrep", "--version"], "checkov": ["checkov", "--version"],
    "trivy": ["trivy", "--version"], "tflint": ["tflint", "--version"], "hadolint": ["hadolint", "--version"],
}


def detect(rule, d):
    det = rule["detector"]
    tool, rid = det["tool"], det["rule_id"]
    if tool == "go-vet":
        return go_vet(d)
    if tool == "staticcheck":
        return staticcheck(d)
    if tool in ESLINT_TOOLS:
        return eslint(d, rid)
    if tool == "ruff":
        return ruff(d, rid)
    if tool == "bandit":
        return bandit(d)
    if tool == "semgrep":
        return semgrep(d, det.get("config", "auto"))
    if tool == "checkov":
        return checkov(d, {"docker": "dockerfile", "kubernetes": "kubernetes"}.get(rule["stack"], "terraform"))
    if tool == "trivy":
        return trivy(d)
    if tool == "tflint":
        return tflint(d, rid)
    if tool == "hadolint":
        return hadolint(d)
    if tool == "zizmor":
        return zizmor(d, det.get("config"))
    if tool == "actionlint":
        return actionlint(d)
    if tool == "spectral":
        return spectral(d, det["config"])
    if tool == "oasdiff":
        return oasdiff(d, rule["test_cases"]["positive"][0]["file"])
    if tool == "buf":
        return buf(d, det["config"])
    if tool == "squawk":
        return squawk(d)
    if tool == "sqlfluff":
        return sqlfluff(d, rid, det["config"])
    if tool == "kube-linter":
        return kube_linter(d, rid)
    if tool == "shellcheck":
        return shellcheck(d)
    return None  # no runner in the toolchain (e.g. golangci-lint): stays mapped


def tool_version(tool):
    if tool in ESLINT_TOOLS:
        pkg = json.loads((Path("/opt/eslint/package.json")).read_text())["dependencies"]
        name = {"eslint": "eslint", "typescript-eslint": "typescript-eslint", "eslint-plugin-n": "eslint-plugin-n",
                "eslint-plugin-react": "eslint-plugin-react", "eslint-plugin-react-hooks": "eslint-plugin-react-hooks",
                "angular-eslint": "@angular-eslint/eslint-plugin", "eslint-plugin-rxjs-x": "eslint-plugin-rxjs-x"}[tool]
        return f"{name}@{pkg[name]} (eslint@{pkg['eslint']})"
    if tool == "oasdiff":
        return "oasdiff v1.34.1 (go install; the binary reports no release tag)"
    if tool == "kube-linter":
        return "kube-linter v0.8.3 (go install; the binary reports no release tag)"
    return version(VERSIONS[tool])


def case_dir(case):
    base = ESLINT_HOME if case["file"].endswith((".ts", ".tsx", ".js")) else None
    d = Path(tempfile.mkdtemp(dir=base))
    if "base" in case:  # two-version detectors compare old/<file> with new/<file>
        for side, text in (("old", case["base"]), ("new", case["code"])):
            target = d / side / case["file"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        return d
    target = d / case["file"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(case["code"])
    return d


def verify(rule):
    rid = rule["detector"]["rule_id"]
    outcome = {"id": rule["id"], "tool": rule["detector"]["tool"], "rule_id": rid, "cases": []}
    for kind in ("positive", "negative"):
        for case in rule["test_cases"][kind]:
            d = case_dir(case)
            try:
                found = detect(rule, d)
            except Exception as exc:  # a crashed detector verifies nothing
                outcome["cases"].append({"kind": kind, "error": str(exc)[:300]})
                continue
            finally:
                shutil.rmtree(d, ignore_errors=True)
            if found is None:
                outcome["status"] = "no_runner"
                return outcome
            hit = rid in found
            outcome["cases"].append({"kind": kind, "reported": hit, "ok": hit == (kind == "positive"),
                                     "other_ids": sorted(found - {rid})[:8]})
    ok = all(c.get("ok") for c in outcome["cases"])
    outcome["status"] = "verified" if ok else "failed"
    return outcome


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="record verified mappings in the catalog")
    ap.add_argument("--only", help="comma-separated AP-* IDs")
    ap.add_argument("--verified-in", default=os.environ.get("VERIFIED_IN", "local"), choices=["local", "ci"])
    args = ap.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    only = set(args.only.split(",")) if args.only else None
    image = os.environ.get("TOOLCHAIN_IMAGE", "")
    results = []
    for rule in catalog["rules"]:
        if only and rule["id"] not in only:
            continue
        if rule["detector"]["mapping"]["status"] == "planned":
            results.append({"id": rule["id"], "status": "planned"})
            continue
        res = verify(rule)
        results.append(res)
        print(f"{res['id']:<16} {res['status']:<10} {res['tool']}:{res['rule_id']}", file=sys.stderr)
        if args.write and res["status"] == "verified":
            if not re.match(r"^[a-z0-9./_-]+(:[A-Za-z0-9._-]+)?@sha256:[0-9a-f]{64}$", image):
                sys.exit("--write needs TOOLCHAIN_IMAGE=<name>@sha256:<digest>")
            rule["detector"]["mapping"] = {
                "status": "verified",
                "tool_version": tool_version(rule["detector"]["tool"]),
                "verified_on": datetime.date.today().isoformat(),
                "verified_in": args.verified_in,
                "toolchain": image,
            }

    if args.write:
        CATALOG.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {s: sum(1 for r in results if r["status"] == s) for s in ("verified", "failed", "no_runner", "planned")}
    print(json.dumps({"summary": summary, "results": results}, indent=2))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())

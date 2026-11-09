"""
Reference Policy Engine for quality_policy.v1 (00_UniversalStandards/17_Quality_Policy_Engine.md).

Every implementation of the engine must produce the same decision as evaluate() on the vectors in
schemas/examples/policy_engine/vectors.json. This is a specification aid and conformance oracle, not
the service.

evaluate() is pure: it takes the request's bytes and a map of path -> bytes for the files the request
names, and returns a policy_decision.v1 document. It reads no clock, environment, network or disk,
and every comparison is exact (fractions, never floats); scores are rounded only for display.

    python tests/contracts/policy_engine_reference.py REQUEST.json

reads the files named in the request relative to the request's folder, prints the canonical decision
and exits 0 (PASS), 1 (BLOCK), 2 (QUARANTINE) or 3 (no decision).
"""

import hashlib
import json
import sys
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from jsonschema import Draft202012Validator

ENGINE = {"name": "policy-engine-reference", "version": "2.2.0"}
SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
IMPLEMENTED = json.loads((SCHEMAS / "quality_policy.v1.json").read_text(encoding="utf-8"))
RULES = {r["id"]: r for r in IMPLEMENTED["rules"]}
EXIT = {"PASS": 0, "BLOCK": 1, "QUARANTINE": 2}
CHANGED = ("added", "modified", "renamed")


def _validator(name):
    return Draft202012Validator(json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8")))


VALIDATE = {n: _validator(n) for n in ("policy_evaluation_request.v1", "quality_policy.v1", "quality_metrics.v1")}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(doc) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def exact(number) -> Fraction:
    return Fraction(str(number))


def shown(value: Fraction) -> float:
    with localcontext() as ctx:
        ctx.prec = 60
        d = Decimal(value.numerator) / Decimal(value.denominator)
        return float(d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN))


def coverage(fn) -> Fraction:
    return Fraction(fn["lines_hit"], fn["lines_instrumented"])


def crap(fn) -> Fraction:
    cc = fn["complexity"]
    return cc * cc * (1 - coverage(fn)) ** 3 + cc


def mutation_score(module):
    m = module.get("mutation")
    if m is None:
        return None
    detected = m["killed"] + m["timeout"]
    total = detected + m["survived"] + m["no_coverage"]
    return None if total == 0 else Fraction(detected, total)


class Findings:
    def __init__(self):
        self.items = []

    def add(self, rule, detail, **fields):
        item = {"rule": rule, "decision": RULES[rule]["decision"], "detail": detail[:512]}
        for key in ("module", "function", "metric"):
            if fields.get(key) is not None:
                item[key] = fields[key]
        for key in ("value", "limit", "baseline"):
            if fields.get(key) is not None:
                item[key] = shown(Fraction(fields[key]))
        self.items.append(item)

    def __bool__(self):
        return bool(self.items)


def _schema_errors(name, doc):
    return sorted(e.message for e in VALIDATE[name].iter_errors(doc))[:3]


def _parse(data):
    try:
        return json.loads(data.decode("utf-8")), None
    except (UnicodeDecodeError, ValueError) as exc:
        return None, f"not JSON: {exc.__class__.__name__}"


def _request_problems(req):
    problems = []
    paths = [c["path"] for c in req["changes"]]
    if len(paths) != len(set(paths)):
        problems.append("a path appears twice in changes")
    if any(a > b for c in req["changes"] for a, b in c["hunks"]):
        problems.append("a hunk starts after it ends")
    return problems


def _evidence_problems(module, needs_mutation):
    problems = []
    names = [f["name"] for f in module["functions"]]
    if len(names) != len(set(names)):
        problems.append("duplicate function names")
    for f in module["functions"]:
        if f["start_line"] > f["end_line"]:
            problems.append(f"{f['name']}: starts after it ends")
        if f["lines_instrumented"] == 0:
            problems.append(f"{f['name']}: no instrumented lines, so no coverage")
        if f["lines_hit"] > f["lines_instrumented"]:
            problems.append(f"{f['name']}: more lines hit than instrumented")
    if needs_mutation and module["functions"] and "mutation" not in module:
        problems.append("no mutation counts")
    return problems


def _by_path(modules, findings, side):
    seen, dup = {}, set()
    for m in modules:
        if m["path"] in seen:
            dup.add(m["path"])
        seen[m["path"]] = m
    for path in sorted(dup):
        findings.add("QP-005", f"{side}: module listed twice", module=path, metric="evidence")
        seen.pop(path)
    return seen, dup


def _overlaps(fn, hunks):
    return any(a <= fn["end_line"] and b >= fn["start_line"] for a, b in hunks)


def _finish(header, inputs, findings, summary=None):
    items = sorted(findings.items, key=lambda f: (f["rule"], f.get("module", ""), f.get("function", ""), f["detail"]))
    if any(f["decision"] == "QUARANTINE" for f in items):
        decision = "QUARANTINE"
    elif items:
        decision = "BLOCK"
    else:
        decision = "PASS"
    counts = summary or {"modules_evaluated": 0, "functions_new": 0, "functions_changed": 0, "functions_unchanged": 0}
    counts = dict(counts,
                  quarantine_findings=sum(f["decision"] == "QUARANTINE" for f in items),
                  block_findings=sum(f["decision"] == "BLOCK" for f in items))
    return dict(header, schema_version="policy_decision.v1", engine=ENGINE, inputs=inputs,
                decision=decision, exit_code=EXIT[decision], findings=items, summary=counts)


def evaluate(request_bytes: bytes, files: dict) -> dict:
    findings = Findings()
    inputs = {"request": sha256(request_bytes)}
    header = {"repo": None, "commit": None, "merge_base": None, "policy_version": None}

    req, err = _parse(request_bytes)
    problems = [err] if err else _schema_errors("policy_evaluation_request.v1", req)
    if not problems:
        problems = _request_problems(req)
    if problems:
        findings.add("QP-001", "request: " + "; ".join(problems), metric="evidence")
        return _finish(header, inputs, findings)
    header = {"repo": req["repo"], "commit": req["commit"], "merge_base": req["merge_base"],
              "policy_version": req["policy"]["policy_version"]}

    # QP-002: every named file is present and is the file the request names.
    raw = {}
    for role in ("policy", "candidate", "baseline"):
        ref = req[role]
        data = files.get(ref["path"])
        if data is None:
            findings.add("QP-002", f"{role}: {ref['path']} was not provided", metric="evidence")
            continue
        inputs[role] = sha256(data)
        if inputs[role] != ref["sha256"]:
            findings.add("QP-002", f"{role}: SHA-256 does not match the request", metric="evidence")
        raw[role] = data
    if findings:
        return _finish(header, inputs, findings)

    # QP-001: each file parses and validates; the policy is one this engine implements.
    docs = {}
    for role, schema in (("policy", "quality_policy.v1"), ("candidate", "quality_metrics.v1"), ("baseline", "quality_metrics.v1")):
        doc, err = _parse(raw[role])
        problems = [err] if err else _schema_errors(schema, doc)
        if problems:
            findings.add("QP-001", f"{role}: " + "; ".join(problems), metric="evidence")
        docs[role] = doc
    if not findings:
        implemented = [(r["id"], r["decision"], r["stage"]) for r in IMPLEMENTED["rules"]]
        given = [(r["id"], r["decision"], r["stage"]) for r in docs["policy"]["rules"]]
        if given != implemented:
            findings.add("QP-001", "policy: its rule set is not the one this engine implements", metric="evidence")
        elif "unknown" not in docs["policy"]["vulnerabilities"]["block_new_severities"]:
            findings.add("QP-001", "policy: block_new_severities must include unknown", metric="evidence")
    if findings:
        return _finish(header, inputs, findings)
    policy, cand, base = docs["policy"], docs["candidate"], docs["baseline"]
    if policy["policy_version"] != req["policy"]["policy_version"]:
        findings.add("QP-002", "policy: policy_version does not match the request", metric="evidence")
        return _finish(header, inputs, findings)

    # QP-003 and QP-006: the documents describe this change and are comparable.
    if cand["repo"] != req["repo"] or cand["commit"] != req["commit"]:
        findings.add("QP-003", "candidate is not the request's repository and commit", metric="evidence")
    if base["repo"] != req["repo"] or base["commit"] != req["merge_base"]:
        findings.add("QP-003", "baseline is not the request's repository at the merge base", metric="evidence")
    if base["language"] != cand["language"]:
        findings.add("QP-003", "baseline and candidate measure different languages", metric="evidence")
    if findings:
        return _finish(header, inputs, findings)
    tools = lambda doc: sorted((t["name"], t["version"]) for t in doc["toolchain"]["tools"])  # noqa: E731
    if cand["toolchain"]["image"] != base["toolchain"]["image"] or tools(cand) != tools(base):
        findings.add("QP-006", "baseline and candidate were measured with different toolchains", metric="evidence")
        return _finish(header, inputs, findings)

    t = {k: exact(v) for k, v in policy["thresholds"].items()}
    vuln_policy = policy["vulnerabilities"]

    # QP-010 and QP-024: vulnerabilities, repository-wide.
    known = {(v["id"], v["package"]) for v in base["vulnerabilities"]}
    for v in cand["vulnerabilities"]:
        label = f"{v['id']} in {v['package']} ({v['severity']}{', KEV' if v['kev'] else ''})"
        if v["severity"] in vuln_policy["quarantine_severities"] or (v["kev"] and vuln_policy["quarantine_kev"]):
            findings.add("QP-010", label, module=v["manifest"], metric="vulnerability")
        elif (v["id"], v["package"]) not in known and v["severity"] in vuln_policy["block_new_severities"]:
            findings.add("QP-024", "new: " + label, module=v["manifest"], metric="vulnerability")

    # Modules.
    changes = {c["path"]: c for c in req["changes"]}
    cand_mods, cand_dup = _by_path(cand["modules"], findings, "candidate")
    base_mods, base_dup = _by_path(base["modules"], findings, "baseline")
    excluded = {e["path"] for e in cand["excluded"]}
    for path, change in sorted(changes.items()):
        if change["status"] != "deleted" and path not in cand_mods and path not in excluded | cand_dup:
            findings.add("QP-005", "changed path is neither measured nor excluded", module=path, metric="evidence")

    counts = {"modules_evaluated": 0, "functions_new": 0, "functions_changed": 0, "functions_unchanged": 0}
    for path, mod in sorted(cand_mods.items()):
        change = changes.get(path)
        status = change["status"] if change else "unchanged"
        hunks = change["hunks"] if change else []
        base_path = change["old_path"] if status == "renamed" else path
        base_mod = None if status == "added" else base_mods.get(base_path)
        is_changed = status in CHANGED

        problems = _evidence_problems(mod, needs_mutation=is_changed)
        if base_mod is not None:
            problems += ["baseline: " + p for p in _evidence_problems(base_mod, needs_mutation=False)]
        if problems:
            findings.add("QP-005", "; ".join(problems), module=path, metric="evidence")
            continue
        if status != "added" and base_mod is None and base_path not in base_dup:
            findings.add("QP-004", f"no baseline record for {base_path}", module=path, metric="evidence")
        if is_changed and base_mod is not None and base_mod["functions"] and "mutation" not in base_mod:
            findings.add("QP-004", "baseline has no mutation counts for a changed module", module=path, metric="evidence")
        counts["modules_evaluated"] += 1

        base_fns = {f["name"]: f for f in base_mod["functions"]} if base_mod else {}
        existing = []
        for fn in sorted(mod["functions"], key=lambda f: f["name"]):
            name, score, cc = fn["name"], crap(fn), fn["complexity"]
            old = base_fns.get(name)
            if old is None:
                kind = "new"
            elif is_changed and _overlaps(fn, hunks):
                kind = "changed"
            else:
                kind = "unchanged"
            counts[f"functions_{kind}"] += 1
            where = {"module": path, "function": name}
            if kind in ("new", "changed"):
                if score > t["crap_red_above"]:
                    findings.add("QP-011", "CRAP in the red zone", metric="crap", value=score, limit=t["crap_red_above"], **where)
                if cc > t["complexity_red_above"]:
                    findings.add("QP-012", "complexity in the red zone", metric="complexity", value=cc, limit=t["complexity_red_above"], **where)
            if kind == "new":
                if score > t["new_function_crap_max"]:
                    findings.add("QP-025", "new function above the CRAP limit", metric="crap", value=score, limit=t["new_function_crap_max"], **where)
                if coverage(fn) < t["new_function_coverage_min"]:
                    findings.add("QP-026", "new function below the coverage minimum", metric="coverage", value=coverage(fn), limit=t["new_function_coverage_min"], **where)
                continue
            existing.append((fn, old))
            if kind == "changed" and score > t["crap_green_max"]:
                findings.add("QP-030", "changed function outside the green zone", metric="crap", value=score, limit=t["crap_green_max"], **where)
            if score > crap(old):
                findings.add("QP-020", "CRAP rose above the baseline", metric="crap", value=score, baseline=crap(old), **where)

        if existing:
            cc_new, cc_old = sum(f["complexity"] for f, _ in existing), sum(o["complexity"] for _, o in existing)
            if cc_new > cc_old:
                findings.add("QP-022", "complexity of existing functions rose", module=path, metric="complexity", value=cc_new, baseline=cc_old)
            cov_new = Fraction(sum(f["lines_hit"] for f, _ in existing), sum(f["lines_instrumented"] for f, _ in existing))
            cov_old = Fraction(sum(o["lines_hit"] for _, o in existing), sum(o["lines_instrumented"] for _, o in existing))
            if cov_new < cov_old:
                findings.add("QP-023", "coverage of existing functions fell", module=path, metric="coverage", value=cov_new, baseline=cov_old)

        score_new = mutation_score(mod)
        score_old = mutation_score(base_mod) if base_mod else None
        zoned = score_new is not None and (base_mod is None or score_old is None) and is_changed
        if score_old is not None and "mutation" in mod:
            if score_new is None:
                findings.add("QP-021", "no mutants now, though the baseline had some", module=path, metric="mutation", baseline=score_old)
            else:
                if score_new < score_old:
                    findings.add("QP-021", "mutation score fell below the baseline", module=path, metric="mutation", value=score_new, baseline=score_old)
                zoned = True
        if zoned:
            red, green = t["mutation_red_below"], t["mutation_green_min"]
            fresh = score_old is None
            if score_new < red and (fresh or score_old >= red):
                findings.add("QP-013", "mutation score in the red zone", module=path, metric="mutation", value=score_new, limit=red)
            elif score_new < green and (fresh or score_old >= green):
                findings.add("QP-031", "mutation score outside the green zone", module=path, metric="mutation", value=score_new, limit=green)

    return _finish(header, inputs, findings, counts)


def main(argv):
    if len(argv) != 2:
        print("usage: policy_engine_reference.py REQUEST.json", file=sys.stderr)
        return 3
    try:
        request_path = Path(argv[1])
        request_bytes = request_path.read_bytes()
        files = {}
        try:
            req = json.loads(request_bytes)
            for role in ("policy", "candidate", "baseline"):
                rel = req[role]["path"]
                target = request_path.parent / rel
                if target.is_file():
                    files[rel] = target.read_bytes()
        except (ValueError, KeyError, TypeError):
            pass
        decision = evaluate(request_bytes, files)
    except Exception as exc:  # noqa: BLE001 - any failure means no decision, never a pass
        print(f"no decision: {exc.__class__.__name__}", file=sys.stderr)
        return 3
    sys.stdout.buffer.write(canonical(decision) + b"\n")
    return decision["exit_code"]


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""TIPSTER PRO: offline, non-destructive structural audit. Run: python sistem_butunluk_denetimi.py"""
import ast, json, re, sys
from pathlib import Path
from collections import Counter
try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent
issues, warnings = [], []
py_files = list(ROOT.rglob("*.py"))
json_files = list(ROOT.rglob("*.json"))
workflow_files = list((ROOT / ".github" / "workflows").glob("*.yml")) + list((ROOT / ".github" / "workflows").glob("*.yaml"))
for p in py_files:
    try:
        ast.parse(p.read_text(encoding="utf-8-sig"), filename=str(p))
    except Exception as e:
        issues.append(f"Python syntax: {p.relative_to(ROOT)}: {e}")
for p in json_files:
    try:
        json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as e:
        issues.append(f"JSON: {p.relative_to(ROOT)}: {e}")
calls = []
schedules = []
for p in workflow_files:
    try:
        doc = yaml.load(p.read_text(encoding="utf-8-sig"), Loader=yaml.BaseLoader)
        if not isinstance(doc, dict) or not isinstance(doc.get("jobs"), dict):
            issues.append(f"Invalid jobs: {p.name}")
            continue
        for cron in doc.get("on", {}).get("schedule", []) or []:
            schedules.append((p.name, cron.get("cron", "")))
        for job in doc["jobs"].values():
            for step in job.get("steps", []):
                for script in re.findall(r"\bpython(?:3)?\s+([\w./-]+\.py)", str(step.get("run", ""))):
                    if not (ROOT / script).is_file():
                        issues.append(f"Missing script: {p.name} -> {script}")
                    calls.append((p.name, script))
    except Exception as e:
        issues.append(f"YAML: {p.name}: {e}")
if (ROOT / ".github" / "workflows" / ".github" / "workflows").exists():
    issues.append("Nested workflows directory")
counts = Counter(script for _, script in calls)
for script, count in sorted(counts.items()):
    if count > 1:
        warnings.append(f"Script called by {count} workflows: {script}")
for p in (ROOT / ".github" / "workflows").glob("*"):
    if p.is_file() and p.suffix not in {".yml", ".yaml"}:
        warnings.append(f"Non-workflow file in workflows: {p.name}")
report = {
    "python_files": len(py_files),
    "json_files": len(json_files),
    "workflow_files": len(workflow_files),
    "scheduled_workflows": schedules,
    "errors": issues,
    "warnings": warnings,
    "scope": "Static validation only; does not validate APIs, prediction quality, or live Actions."
}
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if issues else 0)

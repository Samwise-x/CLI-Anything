import json
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
workflow_files = list((root / ".github" / "workflows").glob("*.yml"))
bad_runner = re.compile(r"runs-on:\s*(?:windows|macos)-", re.I)
for path in workflow_files:
    text = path.read_text(encoding="utf-8")
    if bad_runner.search(text):
        print(f"Unsupported Windows/macOS runner in {path.relative_to(root)}", file=sys.stderr)
        raise SystemExit(1)
for required in (".opencode/plugins/governance.ts", ".opencode/commands/goal.md",
                 ".opencode/commands/goal-resume.md", ".github/rulesets/main-governance.json"):
    if not (root / required).is_file():
        print(f"Missing governance file: {required}", file=sys.stderr)
        raise SystemExit(1)
print(f"Governance policy checked across {len(workflow_files)} workflow files.")

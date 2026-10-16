import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
config = json.loads((root / ".opencode" / "opencode.jsonc").read_text(encoding="utf-8-sig"))
assert config["default_agent"] == "goal-executor"
assert config["agents"]["goal-reviewer"]["mode"] == "subagent"
assert config["agents"]["goal-reviewer"]["model"] != config["agents"]["goal-executor"]["model"]
assert config["steps"] <= 48
for rule in config["permissions"]:
    assert set(rule) == {"action", "resource", "effect"}
print("OpenCode JSONC parses and executor/evaluator separation is configured.")

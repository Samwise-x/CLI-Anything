#!/usr/bin/env python3
"""Apply the repository's reviewed GitHub governance declaration.

Requires a repository-admin token in GH_TOKEN or GITHUB_TOKEN. It applies only
the named ruleset, enables auto-merge, and enables Dependabot alerts/security
updates. It never prints or persists the token.
"""
import argparse
import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from pathlib import Path

API = "https://api.github.com"


def request(method, path, token, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(API + path, data=data, method=method, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "cli-anything-governance-setup",
    })
    try:
        with urlopen(req, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else None
    except HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"GitHub API {error.code} for {method} {path}: {detail}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="Samwise-x/CLI-Anything")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token and not args.dry_run:
        parser.error("set GH_TOKEN or GITHUB_TOKEN to a repository-admin token")
    declaration = Path(__file__).resolve().parents[1] / ".github/rulesets/main-governance.json"
    ruleset = json.loads(declaration.read_text(encoding="utf-8"))
    if args.dry_run:
        print(json.dumps({"repo": args.repo, "ruleset": ruleset,
                          "settings": ["allow_auto_merge", "has_issues", "vulnerability_alerts",
                                       "automated_security_fixes"]}, indent=2))
        return
    path = f"/repos/{args.repo}"
    repository = request("GET", path, token)
    if repository.get("visibility") != "public":
        raise RuntimeError("refusing to apply this public-repository ruleset to a non-public repository")
    current = request("GET", path + "/rulesets", token)
    matches = [item for item in current if item.get("name") == ruleset["name"]]
    if matches:
        ruleset_id = matches[0]["id"]
        request("PUT", path + f"/rulesets/{ruleset_id}", token, ruleset)
        print(f"Updated ruleset {ruleset_id}.")
    else:
        created = request("POST", path + "/rulesets", token, ruleset)
        print(f"Created ruleset {created['id']}.")
    request("PATCH", path, token, {"allow_auto_merge": True, "has_issues": True})
    print("Enabled repository auto-merge.")
    request("PUT", path + "/vulnerability-alerts", token)
    print("Enabled Dependabot vulnerability alerts.")
    request("PUT", path + "/automated-security-fixes", token)
    print("Enabled Dependabot security updates.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, KeyError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)

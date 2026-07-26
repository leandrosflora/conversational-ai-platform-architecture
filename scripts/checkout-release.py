#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

import yaml


def run(args: list[str], cwd: Path | None = None, capture: bool = False, auth_header: str | None = None) -> str:
    command = ["git"]
    if auth_header:
        command.extend(["-c", f"http.extraHeader={auth_header}"])
    command.extend(args)
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "git command failed").strip()
        raise RuntimeError(detail)
    return (result.stdout or "").strip()


def github_auth_header(token: str | None) -> str | None:
    if not token:
        return None
    encoded = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return f"AUTHORIZATION: basic {encoded}"


def validate_manifest(data: dict[str, Any]) -> list[dict[str, Any]]:
    if data.get("schemaVersion") != 1:
        raise ValueError("release manifest schemaVersion must be 1")
    repositories = data.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise ValueError("release manifest must contain repositories")
    required_count = int(data.get("policy", {}).get("requiredRepositoryCount", 0))
    if required_count and len(repositories) != required_count:
        raise ValueError(f"expected {required_count} repositories, found {len(repositories)}")
    names: set[str] = set()
    paths: set[str] = set()
    for item in repositories:
        for field in ("name", "repository", "path", "ref", "role"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"repository entry missing {field}: {item!r}")
        if item["name"] in names:
            raise ValueError(f"duplicate repository name: {item['name']}")
        if item["path"] in paths:
            raise ValueError(f"duplicate checkout path: {item['path']}")
        names.add(item["name"])
        paths.add(item["path"])
    return repositories


def checkout_repository(
    repository: str,
    ref: str,
    destination: Path,
    auth_header: str | None,
    reuse_existing: bool,
) -> str:
    if destination.exists():
        if not (destination / ".git").exists():
            raise RuntimeError(f"destination exists but is not a git repository: {destination}")
        if not reuse_existing:
            raise RuntimeError(f"destination already exists: {destination}")
        sha = run(["rev-parse", "HEAD"], cwd=destination, capture=True)
        status = run(["status", "--porcelain"], cwd=destination, capture=True)
        if status:
            raise RuntimeError(f"existing checkout is dirty: {destination}")
        return sha

    destination.mkdir(parents=True)
    run(["init", "--quiet"], cwd=destination)
    run(["remote", "add", "origin", f"https://github.com/{repository}.git"], cwd=destination)
    try:
        run(["fetch", "--quiet", "--depth", "1", "origin", ref], cwd=destination, auth_header=auth_header)
    except RuntimeError:
        # A full SHA is not always accepted by shallow ref fetch on private repositories.
        run(["fetch", "--quiet", "origin", ref], cwd=destination, auth_header=auth_header)
    run(["checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=destination)
    sha = run(["rev-parse", "HEAD"], cwd=destination, capture=True)
    status = run(["status", "--porcelain"], cwd=destination, capture=True)
    if status:
        raise RuntimeError(f"checkout is dirty immediately after clone: {destination}")
    return sha


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a multi-repository release manifest to exact SHAs.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--token-env", default="MULTIREPO_READ_TOKEN")
    parser.add_argument("--reuse", action="append", default=[], help="Repository name already checked out in workspace")
    args = parser.parse_args()

    manifest = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    repositories = validate_manifest(manifest)
    token = os.getenv(args.token_env)
    auth_header = github_auth_header(token)
    args.workspace.mkdir(parents=True, exist_ok=True)

    locked: list[dict[str, str]] = []
    for item in repositories:
        destination = args.workspace / item["path"]
        sha = checkout_repository(
            item["repository"],
            item["ref"],
            destination,
            auth_header,
            reuse_existing=item["name"] in set(args.reuse),
        )
        locked.append({
            "name": item["name"],
            "repository": item["repository"],
            "path": item["path"],
            "role": item["role"],
            "requestedRef": item["ref"],
            "sha": sha,
        })
        print(f"locked {item['name']} at {sha}")

    lock = {
        "schemaVersion": 1,
        "release": manifest["release"],
        "sourceManifest": str(args.manifest),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "githubRunId": os.getenv("GITHUB_RUN_ID"),
        "githubRunAttempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "repositories": locked,
    }
    args.lock.parent.mkdir(parents=True, exist_ok=True)
    args.lock.write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")
    print(f"wrote locked release manifest to {args.lock}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

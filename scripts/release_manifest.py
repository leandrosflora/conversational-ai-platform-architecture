#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def load_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a mapping")
    if data.get("apiVersion") != "platform.leandroflora.dev/v1":
        raise ValueError("unsupported apiVersion")
    if data.get("kind") != "PlatformRelease":
        raise ValueError("kind must be PlatformRelease")
    repositories = data.get("spec", {}).get("repositories")
    if not isinstance(repositories, list) or len(repositories) != 13:
        raise ValueError("spec.repositories must contain exactly 13 repositories")
    names: set[str] = set()
    repos: set[str] = set()
    for item in repositories:
        if not isinstance(item, dict):
            raise ValueError("repository entries must be mappings")
        name = item.get("name")
        repository = item.get("repository")
        ref = item.get("ref")
        if not all(isinstance(v, str) and v.strip() for v in (name, repository, ref)):
            raise ValueError("name, repository and ref are required")
        if not REPOSITORY_RE.fullmatch(repository):
            raise ValueError(f"invalid repository: {repository}")
        if name in names or repository in repos:
            raise ValueError(f"duplicate repository entry: {name}/{repository}")
        names.add(name)
        repos.add(repository)
    return data


def resolve_ref(repository: str, ref: str, token: str) -> str:
    if SHA_RE.fullmatch(ref):
        return ref
    url = f"https://api.github.com/repos/{repository}/commits/{ref}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "platform-release-resolver",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"unable to resolve {repository}@{ref}: HTTP {exc.code}") from exc
    sha = payload.get("sha")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise RuntimeError(f"GitHub returned an invalid SHA for {repository}@{ref}")
    return sha


def build_lock(manifest: dict, token: str) -> dict:
    locked = []
    for item in manifest["spec"]["repositories"]:
        locked.append(
            {
                "name": item["name"],
                "repository": item["repository"],
                "ref": item["ref"],
                "sha": resolve_ref(item["repository"], item["ref"], token),
            }
        )
    return {
        "apiVersion": manifest["apiVersion"],
        "kind": "PlatformReleaseLock",
        "metadata": manifest["metadata"],
        "spec": {
            "repositories": locked,
            "promotion": manifest["spec"].get("promotion", {}),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--validate-lock", type=Path)
    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest)
        if args.lock:
            token = os.environ.get("GITHUB_TOKEN", "")
            if not token:
                raise ValueError("GITHUB_TOKEN is required to resolve mutable refs")
            args.lock.parent.mkdir(parents=True, exist_ok=True)
            args.lock.write_text(
                yaml.safe_dump(build_lock(manifest, token), sort_keys=False),
                encoding="utf-8",
            )
        if args.validate_lock:
            lock = yaml.safe_load(args.validate_lock.read_text(encoding="utf-8"))
            entries = lock.get("spec", {}).get("repositories", [])
            if len(entries) != 13 or any(not SHA_RE.fullmatch(str(i.get("sha", ""))) for i in entries):
                raise ValueError("lock must contain 13 immutable 40-character SHAs")
    except (OSError, ValueError, RuntimeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("OK: release manifest is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

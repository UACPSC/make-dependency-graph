#!/usr/bin/env python3
"""
commit.py - Commit changed graphs to an existing branch with one GitHub API request

Usage: commit.py <graph dir> <branch> <message>

Compares each makegraph.svg under <graph dir> with the fetched origin/<branch>, then commits
only the changed ones with the GraphQL createCommitOnBranch mutation, which is faster than
git push and makes a commit GitHub signs. Needs GITHUB_TOKEN, GITHUB_REPOSITORY, and
GITHUB_GRAPHQL_URL in the environment.
"""

import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.request

MUTATION = """
mutation($input: CreateCommitOnBranchInput!) {
  createCommitOnBranch(input: $input) { commit { oid } }
}
"""


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def blob_id(data):
    """The git object id of a file's contents, as git hash-object computes it."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main():
    graph_dir, branch, message = sys.argv[1:]
    remote = f"refs/remotes/origin/{branch}"

    # object ids of the graphs already on the branch
    existing = {}
    for line in git("ls-tree", "-r", remote).splitlines():
        info, path = line.split("\t", 1)
        existing[path] = info.split()[2]

    additions = []
    for root, _, files in os.walk(graph_dir):
        for name in files:
            if name != "makegraph.svg":
                continue
            full = os.path.join(root, name)
            path = os.path.relpath(full, graph_dir)
            with open(full, "rb") as f:
                data = f.read()
            if existing.get(path) != blob_id(data):
                additions.append({"path": path, "contents": base64.b64encode(data).decode()})

    if not additions:
        print("Graphs already up to date")
        return

    variables = {"input": {
        "branch": {"repositoryNameWithOwner": os.environ["GITHUB_REPOSITORY"], "branchName": branch},
        "message": {"headline": message},
        "expectedHeadOid": git("rev-parse", remote).strip(),
        "fileChanges": {"additions": additions},
    }}
    request = urllib.request.Request(
        os.environ["GITHUB_GRAPHQL_URL"],
        data=json.dumps({"query": MUTATION, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        result = json.load(response)
    if result.get("errors"):
        sys.exit("commit: " + "; ".join(e["message"] for e in result["errors"]))

    oid = result["data"]["createCommitOnBranch"]["commit"]["oid"]
    print(f"[{branch} {oid[:7]}] {message}")
    for a in additions:
        print(f"  {a['path']}")


if __name__ == "__main__":
    main()

"""GitHub world publisher.

Level generators describe repositories as :class:`RepoSpec` objects (ordered
commits, branches, issues, releases). The publisher materializes them:

- **dry-run** (always): writes a local mirror under ``<root>/github/<repo>/``
  with per-branch final trees, full commit history snapshots, issues and
  releases. Validators and the oracle solver read this mirror.
- **live** (publish phase): builds the same history with local git and pushes
  it to the TreasureHuntBench organization over SSH; issues and releases are
  created through the REST API using the ``gh`` CLI token.
"""

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..artifacts.files import write_json, write_text

ORG = "TreasureHuntBench"


@dataclass
class CommitSpec:
    message: str
    files: Dict[str, str]                 # path -> content (utf-8 text)
    remove: List[str] = field(default_factory=list)


@dataclass
class RepoSpec:
    name: str
    description: str = ""
    default_branch: str = "main"
    commits: List[CommitSpec] = field(default_factory=list)          # on main
    branches: Dict[str, List[CommitSpec]] = field(default_factory=dict)
    issues: List[Dict[str, str]] = field(default_factory=list)
    releases: List[Dict[str, str]] = field(default_factory=list)
    private: bool = False

    def add_commit(self, message: str, files: Dict[str, str],
                   branch: Optional[str] = None,
                   remove: Optional[List[str]] = None) -> None:
        commit = CommitSpec(message=message, files=dict(files),
                            remove=list(remove or []))
        if branch is None or branch == self.default_branch:
            self.commits.append(commit)
        else:
            self.branches.setdefault(branch, []).append(commit)


def _apply_commits(commits: List[CommitSpec],
                   base: Optional[Dict[str, str]] = None):
    """Yield (message, snapshot) applying commits over a base tree."""
    tree = dict(base or {})
    out = []
    for commit in commits:
        tree.update(commit.files)
        for path in commit.remove:
            tree.pop(path, None)
        out.append((commit.message, dict(tree)))
    return out


class LocalMirrorPublisher:
    """Writes the dry-run mirror consumed by validators and the oracle."""

    def __init__(self, root: str):
        self.root = os.path.join(root, "github")

    def repo_dir(self, name: str) -> str:
        return os.path.join(self.root, name)

    def publish(self, spec: RepoSpec) -> str:
        rdir = self.repo_dir(spec.name)
        if os.path.isdir(rdir):
            shutil.rmtree(rdir)
        main_history = _apply_commits(spec.commits)
        history = {spec.default_branch: [
            {"message": m, "files": snap} for m, snap in main_history]}
        final_main = main_history[-1][1] if main_history else {}
        for branch, commits in spec.branches.items():
            branch_history = _apply_commits(commits, base=final_main)
            history[branch] = [{"message": m, "files": snap}
                               for m, snap in branch_history]
        # final tree per branch
        for branch, entries in history.items():
            tree = entries[-1]["files"] if entries else {}
            for path, content in tree.items():
                write_text(os.path.join(rdir, "branches", branch, path),
                           content)
        write_json(os.path.join(rdir, "repo.json"),
                   {"name": spec.name, "org": ORG,
                    "description": spec.description,
                    "default_branch": spec.default_branch,
                    "private": spec.private,
                    "branch_names": sorted(history)})
        write_json(os.path.join(rdir, "history.json"), history)
        write_json(os.path.join(rdir, "issues.json"), spec.issues)
        write_json(os.path.join(rdir, "releases.json"), spec.releases)
        return rdir

    def list_repos(self) -> List[str]:
        if not os.path.isdir(self.root):
            return []
        return sorted(d for d in os.listdir(self.root)
                      if os.path.isdir(os.path.join(self.root, d)))

    def read_file(self, repo: str, path: str, branch: str = "main") -> str:
        full = os.path.join(self.repo_dir(repo), "branches", branch, path)
        with open(full, encoding="utf-8") as fh:
            return fh.read()

    def history(self, repo: str) -> Dict[str, List[Dict[str, Any]]]:
        with open(os.path.join(self.repo_dir(repo), "history.json"),
                  encoding="utf-8") as fh:
            return json.load(fh)


def _run(cmd, cwd=None, env=None):
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                            text=True)
    if result.returncode != 0:
        raise RuntimeError("command failed: %s\n%s\n%s"
                           % (" ".join(cmd), result.stdout, result.stderr))
    return result.stdout


def _gh_token() -> str:
    return _run(["gh", "auth", "token"]).strip()


def _api(method: str, path: str, payload: Optional[Dict[str, Any]] = None):
    cmd = ["gh", "api", "-X", method, path]
    if payload:
        for key, value in payload.items():
            if isinstance(value, bool):
                cmd += ["-F", "%s=%s" % (key, "true" if value else "false")]
            else:
                cmd += ["-f", "%s=%s" % (key, value)]
    return json.loads(_run(cmd) or "{}")


class LiveGitHubPublisher:
    """Pushes RepoSpecs to the real TreasureHuntBench organization."""

    def __init__(self, org: str = ORG):
        self.org = org

    def repo_exists(self, name: str) -> bool:
        try:
            _run(["gh", "api", "repos/%s/%s" % (self.org, name)])
            return True
        except RuntimeError:
            return False

    def create_repo(self, spec: RepoSpec) -> None:
        if self.repo_exists(spec.name):
            return
        _api("POST", "orgs/%s/repos" % self.org, {
            "name": spec.name,
            "description": spec.description,
            "private": spec.private,
            "has_issues": True,
            "has_wiki": False,
        })

    def publish(self, spec: RepoSpec) -> str:
        self.create_repo(spec)
        url = "git@github.com:%s/%s.git" % (self.org, spec.name)
        workdir = tempfile.mkdtemp(prefix="thbpub-")
        env = dict(os.environ,
                   GIT_AUTHOR_NAME="thb-generator",
                   GIT_AUTHOR_EMAIL="generator@treasurehuntbench.invalid",
                   GIT_COMMITTER_NAME="thb-generator",
                   GIT_COMMITTER_EMAIL="generator@treasurehuntbench.invalid")
        try:
            _run(["git", "init"], cwd=workdir, env=env)
            _run(["git", "checkout", "-b", spec.default_branch],
                 cwd=workdir, env=env)
            for commit in spec.commits:
                self._write_commit(workdir, commit, env)
            _run(["git", "remote", "add", "origin", url], cwd=workdir, env=env)
            _run(["git", "push", "-f", "origin", spec.default_branch],
                 cwd=workdir, env=env)
            for branch, commits in spec.branches.items():
                _run(["git", "checkout", "-B", branch, spec.default_branch],
                     cwd=workdir, env=env)
                for commit in commits:
                    self._write_commit(workdir, commit, env)
                _run(["git", "push", "-f", "origin", branch],
                     cwd=workdir, env=env)
            _run(["git", "checkout", spec.default_branch],
                 cwd=workdir, env=env)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        for issue in spec.issues:
            _api("POST", "repos/%s/%s/issues" % (self.org, spec.name), issue)
        for release in spec.releases:
            _api("POST", "repos/%s/%s/releases" % (self.org, spec.name), {
                "tag_name": release["tag"],
                "name": release.get("name", release["tag"]),
                "body": release.get("body", ""),
            })
        return "https://github.com/%s/%s" % (self.org, spec.name)

    @staticmethod
    def _write_commit(workdir: str, commit: CommitSpec, env) -> None:
        for path, content in commit.files.items():
            write_text(os.path.join(workdir, path), content)
        for path in commit.remove:
            target = os.path.join(workdir, path)
            if os.path.exists(target):
                os.remove(target)
        _run(["git", "add", "-A"], cwd=workdir, env=env)
        _run(["git", "commit", "--allow-empty", "-m", commit.message],
             cwd=workdir, env=env)

    def delete_repo(self, name: str) -> None:
        _run(["gh", "api", "-X", "DELETE",
              "repos/%s/%s" % (self.org, name)])

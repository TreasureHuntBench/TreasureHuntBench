"""Publish the generated benchmark to the live TreasureHuntBench org.

Publishes every repository of the training and validation worlds, plus one
assets repository per world carrying the media mirrors (video metadata,
captions, frames, playlists) and the public source cache. Test worlds stay
local and private.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from thb.gen.github_pub import (LiveGitHubPublisher, RepoSpec,
                                spec_from_mirror)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLITS = ("training", "validation")
STATE_PATH = os.path.join(ROOT, "private/publish_state.json")


def _load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as fh:
            return set(json.load(fh))
    return set()


def _save_state(done):
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(sorted(done), fh)


def assets_spec(split: str, wname: str, out_root: str) -> RepoSpec:
    spec = RepoSpec(
        name="thb-assets-%s-%s" % (split, wname),
        description="TreasureHuntBench %s %s world assets: media mirrors "
                    "and source cache" % (split, wname))
    files = {}
    for sub in ("media_mirror", "cache"):
        base = os.path.join(out_root, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, names in os.walk(base):
            for name in names:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, out_root).replace(os.sep, "/")
                with open(full, "rb") as fh:
                    data = fh.read()
                try:
                    files[rel] = data.decode("utf-8")
                except UnicodeDecodeError:
                    files[rel] = data
    spec.add_commit("import world assets", files)
    return spec


def _publish_with_retry(publisher, spec, attempts=4):
    for attempt in range(1, attempts + 1):
        try:
            return publisher.publish(spec)
        except Exception as exc:  # noqa: BLE001 - transient API errors
            if attempt == attempts:
                raise
            wait = 10 * attempt
            print("attempt %d failed for %s (%s); retrying in %ds"
                  % (attempt, spec.name, str(exc).splitlines()[0][:120],
                     wait), flush=True)
            time.sleep(wait)


def main() -> int:
    publisher = LiveGitHubPublisher()
    done = _load_state()
    published = []
    for split in SPLITS:
        base = os.path.join(ROOT, "private/build", split)
        for wname in sorted(os.listdir(base)):
            out_root = os.path.join(base, wname)
            github_root = os.path.join(out_root, "github")
            for repo in sorted(os.listdir(github_root)):
                key = "%s/%s/%s" % (split, wname, repo)
                if key in done:
                    continue
                spec = spec_from_mirror(os.path.join(github_root, repo))
                url = _publish_with_retry(publisher, spec)
                done.add(key)
                _save_state(done)
                published.append(url)
                print("published %s" % url, flush=True)
                time.sleep(0.3)
            akey = "%s/%s/__assets__" % (split, wname)
            if akey not in done:
                spec = assets_spec(split, wname, out_root)
                url = _publish_with_retry(publisher, spec)
                done.add(akey)
                _save_state(done)
                published.append(url)
                print("published %s" % url, flush=True)
    print("newly published: %d" % len(published))
    return 0


if __name__ == "__main__":
    sys.exit(main())

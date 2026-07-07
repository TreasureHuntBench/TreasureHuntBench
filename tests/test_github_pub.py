from thb.gen.github_pub import CommitSpec, LocalMirrorPublisher, RepoSpec


def _spec():
    spec = RepoSpec(name="kestrel-L4S2-TEST", description="records bundle")
    spec.add_commit("initial records import",
                    {"records/L4S2_83A_route.md": "v1",
                     "manifests/kestrel-L4S2-TEST.json": '{"run_ref": "L4S2-7QK9"}'})
    spec.add_commit("pre-migration snapshot",
                    {"records/L4S2_83A_route.md": "v2-with-payload"})
    spec.add_commit("migration-complete",
                    {"records/L4S2_83A_route.md": "v3-clean"},
                    remove=["manifests/kestrel-L4S2-TEST.json"])
    spec.add_commit("archived ledger", {"tables/L4S2_idx.csv": "key,val\n1,a\n"},
                    branch="archiv-1848")
    spec.issues.append({"title": "ingest window", "body": "batch 07A closed"})
    spec.releases.append({"tag": "v0.9", "name": "pre-migration",
                          "body": "snapshot before rollout"})
    return spec


def test_local_mirror_layout(tmp_path):
    pub = LocalMirrorPublisher(str(tmp_path))
    rdir = pub.publish(_spec())
    assert pub.list_repos() == ["kestrel-L4S2-TEST"]
    # final main tree has v3 and no manifest (removed in last commit)
    assert pub.read_file("kestrel-L4S2-TEST",
                         "records/L4S2_83A_route.md") == "v3-clean"
    import os
    assert not os.path.exists(os.path.join(
        rdir, "branches/main/manifests/kestrel-L4S2-TEST.json"))
    # branch tree includes branch commit on top of main head
    assert pub.read_file("kestrel-L4S2-TEST", "tables/L4S2_idx.csv",
                         branch="archiv-1848").startswith("key,val")


def test_history_snapshots_support_git_investigation(tmp_path):
    pub = LocalMirrorPublisher(str(tmp_path))
    pub.publish(_spec())
    history = pub.history("kestrel-L4S2-TEST")["main"]
    messages = [h["message"] for h in history]
    assert messages == ["initial records import", "pre-migration snapshot",
                        "migration-complete"]
    # the last commit BEFORE migration-complete still contains the payload
    idx = messages.index("migration-complete")
    before = history[idx - 1]["files"]
    assert before["records/L4S2_83A_route.md"] == "v2-with-payload"
    assert "manifests/kestrel-L4S2-TEST.json" in before


def test_republish_is_idempotent(tmp_path):
    pub = LocalMirrorPublisher(str(tmp_path))
    pub.publish(_spec())
    pub.publish(_spec())
    assert pub.list_repos() == ["kestrel-L4S2-TEST"]

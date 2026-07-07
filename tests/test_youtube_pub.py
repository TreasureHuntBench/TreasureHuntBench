import os

from thb.gen.youtube_pub import (PlaylistSpec, Segment, VideoSpec,
                                 YouTubeMirror, captions_vtt, mmss,
                                 video_reference_file)


def _spec():
    return VideoSpec(
        ref="video_L5S1_7C3",
        title="field readout 7C3",
        description="run_ref=L5S1-7C3\nseries archive readout",
        segments=[
            Segment(0, 3, ["calibration"]),
            Segment(3, 4, ["repository=RXcTT_712_Q4",
                           "document=records/RXcTT_712_Q4.md"]),
            Segment(4, 10, ["end of readout"]),
        ],
        tags=["archive", "readout"])


def test_mirror_layout_and_text_at(tmp_path):
    mirror = YouTubeMirror(str(tmp_path))
    vdir = mirror.build_video(_spec())
    assert os.path.exists(os.path.join(vdir, "metadata.json"))
    assert os.path.exists(os.path.join(vdir, "captions.vtt"))
    assert os.path.exists(os.path.join(vdir, "frames", "seg01.png"))
    # the clue text appears exactly at 00:03 and not at 00:02
    assert mirror.text_at("video_L5S1_7C3", "00:03") == [
        "repository=RXcTT_712_Q4", "document=records/RXcTT_712_Q4.md"]
    assert mirror.text_at("video_L5S1_7C3", "00:02") == ["calibration"]
    meta = mirror.metadata("video_L5S1_7C3")
    assert meta["privacy"] == "unlisted"
    assert "run_ref=L5S1-7C3" in meta["description"]


def test_captions_parse():
    vtt = captions_vtt(_spec())
    assert vtt.startswith("WEBVTT")
    assert "00:00:03.000 --> 00:00:04.000" in vtt
    assert "repository=RXcTT_712_Q4" in vtt


def test_mp4_assembly(tmp_path):
    mirror = YouTubeMirror(str(tmp_path))
    vdir = mirror.build_video(_spec(), make_mp4=True)
    mp4 = os.path.join(vdir, "video.mp4")
    assert os.path.exists(mp4) and os.path.getsize(mp4) > 1000


def test_playlist_and_helpers(tmp_path):
    mirror = YouTubeMirror(str(tmp_path))
    pl = PlaylistSpec(ref="playlist_L7S2_61B", title="survey uploads",
                      video_refs=["v1", "v2"],
                      video_titles=["Kite survey", "Early figures"])
    mirror.build_playlist(pl)
    data = mirror.playlist("playlist_L7S2_61B")
    assert data["video_titles"][1] == "Early figures"
    assert mmss(63) == "01:03"
    ref = video_reference_file("video_L5S1_7C3")
    assert ref["channel"] == "@TreasureHuntBench" and ref["url"] == ""

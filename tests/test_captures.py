from thb.artifacts.captures import (build_capture_vtt, build_upload_log,
                                    cue_lines_at, parse_note_fields,
                                    parse_upload_log_titles)


def _vtt():
    return build_capture_vtt(
        {"run_ref": "L9S3-2D8A", "kind": "survey capture"},
        [(0, 27, ["series calibration"]),
         (27, 28, ["repository=r", "document=d.md"]),
         (28, 33, ["capture complete"])])


def test_note_fields_and_cues():
    vtt = _vtt()
    assert vtt.startswith("WEBVTT")
    assert parse_note_fields(vtt) == {"run_ref": "L9S3-2D8A",
                                      "kind": "survey capture"}
    assert cue_lines_at(vtt, "00:27") == ["repository=r", "document=d.md"]
    assert cue_lines_at(vtt, "00:26") == ["series calibration"]
    assert cue_lines_at(vtt, "00:28") == ["capture complete"]
    assert cue_lines_at(vtt, "01:30") == []
    assert cue_lines_at(vtt, "00:00:27") == ["repository=r", "document=d.md"]


def test_upload_log_roundtrip():
    titles = ["Kite survey", "Early figures", "Vent recap"]
    log = build_upload_log(titles)
    assert parse_upload_log_titles(log) == titles

import pytest

from thb.artifacts import encodings as enc
from thb.artifacts.archive import list_zip, read_zip_entry, write_zip
from thb.artifacts.files import (csv_text, markdown_doc, read_text,
                                 write_csv, write_json, write_markdown)
from thb.artifacts.multilingual import (LANGS, STEP_TEMPLATES, render_numbered,
                                        render_step)
from thb.artifacts.sqlite_gen import query_sqlite, write_sqlite


def test_codecs_roundtrip():
    msg = "kestrel-batch 1847 Q7"
    assert enc.base64_decode(enc.base64_encode(msg)) == msg
    assert enc.hex_decode(enc.hex_encode(msg)) == msg
    assert enc.caesar_decode(enc.caesar_encode(msg, 5), 5) == msg
    assert enc.vigenere_decode(enc.vigenere_encode(msg, "LANTERN"), "LANTERN") == msg
    assert enc.morse_decode(enc.morse_encode("BATCH 42")) == "BATCH 42"


def test_acrostic():
    titles = enc.acrostic_encode("KEY", ["ite survey notes", "vent recap", "early figures"])
    assert enc.acrostic_decode(titles) == "KEY"
    with pytest.raises(ValueError):
        enc.acrostic_encode("TOOLONG", ["a"])


def test_markdown_and_csv(tmp_path):
    p = write_markdown(str(tmp_path / "reports/r1.md"), "Ledger review 07A",
                       [{"heading": "Scope", "body": "Rows 1-40."}],
                       front_matter={"run_id": "L4S2-7QK9"})
    text = read_text(p)
    assert "run_id: L4S2-7QK9" in text and "## Scope" in text
    assert markdown_doc("T", [{"heading": "", "body": "b"}]).startswith("# T")

    c = write_csv(str(tmp_path / "tables/t.csv"), ["key", "val"],
                  [["1848", "bundle_A17"], ["1849", "bundle_B02"]])
    assert "1848,bundle_A17" in read_text(c)
    assert csv_text(["a"], [["x"]]) == "a\nx\n"

    j = write_json(str(tmp_path / "m.json"), {"run_ref": "L9S3-2D8"})
    assert '"run_ref": "L9S3-2D8"' in read_text(j)


def test_sqlite(tmp_path):
    db = write_sqlite(str(tmp_path / "records/ledger.db"), "entries",
                      ["key", "payload"], [["1848", "route-A"], ["77", "route-B"]])
    rows = query_sqlite(db, "SELECT payload FROM entries WHERE key = ?", ["1848"])
    assert rows == [{"payload": "route-A"}]


def test_zip_with_and_without_password(tmp_path):
    plain = write_zip(str(tmp_path / "a.zip"), {"docs/x.md": "hello"})
    assert list_zip(plain) == ["docs/x.md"]
    assert read_zip_entry(plain, "docs/x.md") == "hello"

    protected = write_zip(str(tmp_path / "b.zip"), {"inner/y.md": "payload"},
                          password="k3y-1848")
    assert read_zip_entry(protected, "inner/y.md", password="k3y-1848") == "payload"
    with pytest.raises(Exception):
        read_zip_entry(protected, "inner/y.md", password="wrong")


def test_multilingual_all_templates_all_langs():
    sample_kwargs = {
        "date": "2018-04-17", "var": "GOLD_INT", "repo": "RXcTT_1348_Q7",
        "pattern": "RXcTT_1348_*", "path": "records/r.md", "branch": "archiv-1848",
        "city": "Passau, Germany", "tz": "Europe/Berlin", "field": "run_ref",
        "value": "L9S3-2D8", "shift": 5, "msg": "migration-complete",
        "ref": "L8S1", "qid": "Q4190", "lang_name": "German", "n": 5,
        "page": "Passau",
    }
    for key, translations in STEP_TEMPLATES.items():
        for lang in LANGS:
            text = render_step(key, lang, **sample_kwargs)
            assert text.strip()
            # substituted values must survive translation verbatim
            if "{date}" in translations["en"]:
                assert "2018-04-17" in text
            if "{var}" in translations["en"]:
                assert "GOLD_INT" in text
            if "{path}" in translations["en"]:
                assert "records/r.md" in text


def test_render_numbered():
    block = render_numbered(
        [("use_gold_source", {}),
         ("get_gold_for_date", {"date": "2018-04-17"}),
         ("round_nearest_var", {"var": "GOLD_INT"})], "de")
    assert block.startswith("1. ") and "\n2. " in block and "GOLD_INT" in block


def test_unknown_template_and_lang():
    with pytest.raises(KeyError):
        render_step("nope", "en")
    with pytest.raises(KeyError):
        render_step("read_file", "fr", path="x")

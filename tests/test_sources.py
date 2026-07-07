"""Source-module tests. All run offline against the bundled snapshot."""
import pytest

from thb.core.cache import SourceCache
from thb.sources.base import SourceError, apply_rule, bundle
from thb.sources.fx import get_fx_rate, bundled_fx_dates
from thb.sources.gold import get_gold_price, bundled_gold_dates
from thb.sources.open_meteo import (approved_cities, get_coldest_hour,
                                    OpenMeteoSource)
from thb.sources.wiki import city_qid, get_wikidata_label, get_wikibase_item
from thb.sources.worldbank import get_series_observation


@pytest.fixture()
def cache(tmp_path):
    return SourceCache(str(tmp_path / "cache"))


def test_bundle_loaded():
    b = bundle()
    assert b["cities"] and b["open_meteo"] and b["gold_yahoo"]


def test_normalization_rules():
    assert apply_rule("round_nearest_integer", 1347.5) == "1348"
    assert apply_rule("integer_part", "132.87") == "132"
    assert apply_rule("two_digit", 3) == "03"
    with pytest.raises(SourceError):
        apply_rule("no_such_rule", 1)


def test_coldest_hour_bundled(cache):
    city = "Passau, Germany"
    assert city in approved_cities()
    key = "%s|2017-01-12" % city
    temps = bundle()["open_meteo"][key]["temperature_2m"]
    expected = "%02d" % temps.index(min(t for t in temps if t is not None))
    value, entry = get_coldest_hour(city, "2017-01-12", cache)
    assert value == expected
    assert entry.raw_response_hash.startswith("sha256:")
    assert "Open-Meteo" in entry.citation
    # second call is a cache hit with identical value
    value2, entry2 = get_coldest_hour(city, "2017-01-12", cache)
    assert (value2, entry2.cache_id) == (value, entry.cache_id)


def test_coldest_hour_tie_break_earliest(cache):
    src = OpenMeteoSource()
    raw = {"time": ["t0", "t1", "t2", "t3"],
           "temperature_2m": [-5.0, -9.0, -9.0, -1.0]}
    assert src.extract(raw, {}, "coldest_hour_two_digit") == 1


def test_gold_price_bundled(cache):
    date = "2018-04-17"
    assert date in bundled_gold_dates()
    close = bundle()["gold_yahoo"][date]["close_usd"]
    value, entry = get_gold_price(date, cache)
    assert value == str(int(round(close)))
    assert entry.normalization_rule == "round_nearest_integer"
    assert entry.query["symbol"] == "GC=F"


def test_fx_bundled(cache):
    date = bundled_fx_dates()[0]
    rate = bundle()["fx_frankfurter"][date]["JPY"]
    value, entry = get_fx_rate(date, "JPY", cache)
    assert value == str(int(float(rate)))
    assert "Central Bank" in entry.citation or "Frankfurter" in entry.citation


def test_worldbank_bundled(cache):
    value, entry = get_series_observation("DE", "SP.POP.TOTL", "2018", cache,
                                          normalization="millions_round")
    assert value == "83"  # Germany 2018 population, millions
    assert "World Bank" in entry.citation


def test_wikidata_and_wikipedia_bundled(cache):
    qid = city_qid("Passau, Germany")
    assert qid == "Q4190"
    label_ar, _ = get_wikidata_label(qid, "ar", cache)
    assert label_ar  # Arabic label exists
    item, _ = get_wikibase_item("Passau", cache)
    assert item == "Q4190"


def test_cache_written_and_reusable(cache, tmp_path):
    _, entry = get_gold_price("2019-03-05", cache)
    reopened = SourceCache(str(tmp_path / "cache"))
    assert reopened.get(entry.cache_id) == entry

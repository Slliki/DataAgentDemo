import pytest
from datapilot import data
from datapilot.data import build_database
from datapilot.tools import query_readonly
from datapilot.agent import run_analysis

@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    test_db = tmp_path / "test.duckdb"
    monkeypatch.setattr(data, "DB", test_db)
    build_database(test_db)
def test_reproducible_rows():
    from datapilot.tools import query_readonly
    x = query_readonly("SELECT count(*) n FROM daily_metrics").iloc[0].n
    assert x == 4344

def test_six_month_range_and_channels():
    row = query_readonly("SELECT min(day) start_day, max(day) end_day, count(DISTINCT channel) channels FROM daily_metrics").iloc[0]
    assert str(row.start_day.date()) == "2025-01-01"
    assert str(row.end_day.date()) == "2025-06-30"
    assert row.channels == 4

def test_stockout_is_observable_without_truth_table():
    row = query_readonly("""SELECT min(stock) min_stock FROM inventory
        WHERE sku = 'phone_x' AND day BETWEEN DATE '2025-06-17' AND DATE '2025-06-30'""").iloc[0]
    assert row.min_stock == 0
def test_truth_is_blocked():
    with pytest.raises(ValueError): query_readonly("SELECT * FROM event_truth")
def test_writes_are_blocked():
    with pytest.raises(ValueError): query_readonly("DROP TABLE daily_metrics")
def test_end_to_end_has_layers():
    r = run_analysis()
    assert r["facts"]["gmv"] > 0 and r["hypotheses"] and not r["conclusions"]


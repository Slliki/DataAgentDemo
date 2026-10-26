from datapilot import data
from datapilot.data import build_database
from datapilot.nlq import generate_sql
from datapilot.tools import query_readonly


def test_recent_week_digital_gmv(tmp_path, monkeypatch):
    test_db = tmp_path / "nlq.duckdb"
    monkeypatch.setattr(data, "DB", test_db)
    build_database(test_db)
    plan = generate_sql("给我拉出最近一周数码下的gmv数据")
    result = query_readonly(plan.sql)
    assert plan.category == "数码"
    assert plan.days == 7
    assert plan.grain == "day"
    assert len(result) == 7
    assert result.metric_value.sum() > 0


def test_category_breakdown_sql(tmp_path, monkeypatch):
    test_db = tmp_path / "category.duckdb"
    monkeypatch.setattr(data, "DB", test_db)
    build_database(test_db)
    plan = generate_sql("最近30天各品类销售额")
    result = query_readonly(plan.sql)
    assert plan.grain == "category"
    assert set(result.category) == {"数码", "家电", "美妆", "服装", "食品"}


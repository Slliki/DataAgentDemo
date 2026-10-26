import pytest
from datapilot.tools import query_readonly


@pytest.mark.parametrize("sql", [
    "SELECT * FROM event_truth",
    "SELECT * FROM read_json_auto('https://example.com/a.json')",
    "SELECT * FROM daily_metrics -- bypass",
    "SELECT * FROM daily_metrics; DROP TABLE daily_metrics",
])
def test_unsafe_model_sql_is_rejected(sql):
    with pytest.raises(ValueError):
        query_readonly(sql)


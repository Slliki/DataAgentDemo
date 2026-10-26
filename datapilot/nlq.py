"""受限的自然语言问数：将常见中文经营问题转换为白名单 SQL。"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class QueryPlan:
    sql: str
    metric: str
    metric_label: str
    grain: str
    days: int
    category: str | None
    explanation: str


METRICS = {
    "gmv": ("SUM(gmv)", "GMV"),
    "销售额": ("SUM(gmv)", "GMV"),
    "成交额": ("SUM(gmv)", "GMV"),
    "订单": ("SUM(orders)", "订单数"),
    "uv": ("SUM(uv)", "UV"),
    "访客": ("SUM(uv)", "UV"),
    "转化率": ("SUM(orders)::DOUBLE / NULLIF(SUM(uv), 0)", "转化率"),
    "客单价": ("SUM(gmv) / NULLIF(SUM(orders), 0)", "客单价"),
}
CATEGORIES = ("数码", "家电", "美妆", "服装", "食品")


def _parse_days(question: str) -> int:
    match = re.search(r"(?:最近|近)\s*(\d+)\s*天", question)
    if match:
        return max(1, min(int(match.group(1)), 90))
    if re.search(r"最近一周|近一周|过去一周|最近7天", question):
        return 7
    if re.search(r"最近一个月|近一个月|最近30天", question):
        return 30
    return 7


def _parse_metric(question: str):
    lowered = question.lower()
    for token, definition in METRICS.items():
        if token in lowered:
            expression, label = definition
            return expression, label
    raise ValueError("暂未识别指标。请在问题中包含 GMV、销售额、订单、UV、转化率或客单价。")


def generate_sql(question: str) -> QueryPlan:
    question = question.strip()
    if not question:
        raise ValueError("请输入一个经营问题。")

    expression, metric_label = _parse_metric(question)
    days = _parse_days(question)
    category = next((name for name in CATEGORIES if name in question), None)

    if re.search(r"按\s*(sku|商品)|sku维度|商品维度", question, re.I):
        grain, dimension, group_by, order_by = "sku", "sku", "sku", "metric_value DESC"
    elif re.search(r"按\s*品类|各品类|品类维度", question):
        grain, dimension, group_by, order_by = "category", "category", "category", "metric_value DESC"
    elif re.search(r"汇总|合计|总共|总计", question):
        grain, dimension, group_by, order_by = "total", "'合计' AS period", "", ""
    else:
        grain, dimension, group_by, order_by = "day", "day", "day", "day"

    filters = [
        f"day >= (SELECT MAX(day) FROM daily_metrics) - INTERVAL '{days - 1} days'",
        "day <= (SELECT MAX(day) FROM daily_metrics)",
    ]
    if category:
        filters.append(f"category = '{category}'")

    sql = (
        f"SELECT {dimension}, {expression} AS metric_value "
        "FROM daily_metrics "
        f"WHERE {' AND '.join(filters)}"
    )
    if group_by:
        sql += f" GROUP BY {group_by}"
    if order_by:
        sql += f" ORDER BY {order_by}"

    scope = f"{category}品类" if category else "全部品类"
    explanation = f"查询模拟数据最新日期往前 {days} 天的{scope}{metric_label}，按{grain}展示。"
    return QueryPlan(sql, "metric_value", metric_label, grain, days, category, explanation)


"""使用 OpenAI Responses API 生成结构化、安全可验证的 SQL 计划。"""
import json
import os

from .nlq import QueryPlan


SQL_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "sql": {"type": "string"},
        "metric_label": {"type": "string"},
        "metric_column": {"type": "string"},
        "grain": {"type": "string", "enum": ["day", "sku", "category", "channel", "total", "table"]},
        "explanation": {"type": "string"},
    },
    "required": ["sql", "metric_label", "metric_column", "grain", "explanation"],
    "additionalProperties": False,
}

INSTRUCTIONS = """你是星河电商的 SQL 分析 Agent。把用户中文问题转换为一条 DuckDB SELECT。
只可使用：
1. daily_metrics(day DATE, sku VARCHAR, category VARCHAR, channel VARCHAR, price INTEGER, uv INTEGER, orders INTEGER, gmv DOUBLE)
2. inventory(day DATE, sku VARCHAR, stock INTEGER)
数据范围 2025-01-01 到 2025-06-30。“最近”必须以表中 MAX(day) 为基准。
指标：GMV=SUM(gmv)，订单=SUM(orders)，UV=SUM(uv)，转化率=SUM(orders)/SUM(uv)，客单价=SUM(gmv)/SUM(orders)。
要求：SQL 必须以 SELECT 开头；禁止 WITH、写操作、DDL、PRAGMA、ATTACH、文件/网络读取、event_truth、dataset_metadata、多语句和任意代码；不要添加分号；最多返回 500 行。聚合值尽量命名 metric_value，维度使用 day/sku/category/channel。只输出指定 JSON 结构。"""


def generate_sql_openai(question: str, api_key: str, model: str | None = None) -> QueryPlan:
    if not api_key:
        raise ValueError("未配置 OPENAI_API_KEY。")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("缺少 openai 包，请重新执行：python -m pip install -r requirements.txt") from exc

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model or os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        instructions=INSTRUCTIONS,
        input=question,
        text={
            "format": {
                "type": "json_schema",
                "name": "sql_plan",
                "strict": True,
                "schema": SQL_PLAN_SCHEMA,
            }
        },
    )
    payload = json.loads(response.output_text)
    sql = payload["sql"].strip().removesuffix(";")
    return QueryPlan(
        sql=sql,
        metric=payload["metric_column"],
        metric_label=payload["metric_label"],
        grain=payload["grain"],
        days=0,
        category=None,
        explanation=payload["explanation"],
    )


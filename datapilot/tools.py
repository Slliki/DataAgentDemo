import re
from .data import connect

ALLOWED = {"daily_metrics", "inventory"}
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|copy|install|load|pragma|attach|call|export|import|"
    r"event_truth|dataset_metadata|read_csv|read_parquet|read_json|read_text|sqlite_master|duckdb_tables)\b",
    re.I,
)

def query_readonly(sql: str):
    if (
        ";" in sql.strip().rstrip(";")
        or "--" in sql
        or "/*" in sql
        or "://" in sql
        or FORBIDDEN.search(sql)
        or not re.match(r"^\s*select\b", sql, re.I)
    ):
        raise ValueError("仅允许单条 SELECT，且禁止写操作、文件读取和真相集访问")
    if not any(re.search(rf"\b{t}\b", sql, re.I) for t in ALLOWED):
        raise ValueError("查询必须使用白名单业务表")
    with connect() as con:
        return con.execute(f"SELECT * FROM ({sql.strip().rstrip(';')}) AS safe_result LIMIT 1000").fetchdf()

def inspect_business():
    return query_readonly("""SELECT sum(gmv) gmv, sum(uv) uv, sum(orders) orders,
      sum(orders)::DOUBLE/sum(uv) conversion, sum(gmv)/sum(orders) aov
      FROM daily_metrics
      WHERE day >= (SELECT max(day) FROM daily_metrics) - INTERVAL '6 days'""")

def diagnose():
    return query_readonly("""SELECT category, sum(gmv) gmv, sum(uv) uv, sum(orders) orders,
      sum(orders)::DOUBLE/sum(uv) conversion FROM daily_metrics
      WHERE day >= (SELECT max(day) FROM daily_metrics) - INTERVAL '6 days'
      GROUP BY category ORDER BY gmv DESC""")

def simulate_restock(days=14, recovery=0.9):
    d = diagnose()
    return {"days": days, "recovery": recovery, "estimated_gmv_recovered": float(d.gmv.sum() * recovery * days / 14), "assumption": "受影响 SKU 转化恢复至正常期的 90%"}


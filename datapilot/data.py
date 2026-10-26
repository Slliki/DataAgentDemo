from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "stardust.duckdb"
DATA_VERSION = 2
EXPECTED_ROWS = 181 * 6 * 4

def build_database(path=None, seed=42):
    path = Path(path or DB)
    con = duckdb.connect(str(path))
    try:
        con.execute("DROP TABLE IF EXISTS daily_metrics")
        con.execute("DROP TABLE IF EXISTS inventory")
        con.execute("DROP TABLE IF EXISTS event_truth")
        con.execute("DROP TABLE IF EXISTS dataset_metadata")
        con.execute("""
        CREATE TABLE daily_metrics AS
        WITH dates AS (
          SELECT CAST(day AS DATE) AS day
          FROM generate_series(DATE '2025-01-01', DATE '2025-06-30', INTERVAL 1 DAY) t(day)
        ),
        skus AS (
          SELECT * FROM (VALUES
            ('phone_x',   '数码', 1999, 160, 0.040),
            ('earbuds_y', '数码',  299, 230, 0.085),
            ('cleaner_z', '家电',  399, 135, 0.070),
            ('beauty_a',  '美妆',  159, 190, 0.095),
            ('shirt_b',   '服装',  129, 175, 0.082),
            ('food_c',    '食品',   79, 210, 0.110)
          ) v(sku, category, price, base_uv, base_cvr)
        ),
        channels AS (
          SELECT * FROM (VALUES
            ('自然推荐', 0.35, 0.25, 1.05),
            ('搜索',     0.30, 0.22, 1.15),
            ('广告',     0.25, 0.40, 0.75),
            ('活动',     0.10, 0.13, 1.10)
          ) v(channel, normal_share, shifted_share, cvr_factor)
        ),
        traffic AS (
          SELECT day, sku, category, price, channel, base_cvr, cvr_factor,
            GREATEST(1, CAST(ROUND(
              base_uv
              * CASE extract('isodow' FROM day) WHEN 6 THEN 1.18 WHEN 7 THEN 1.22 ELSE 1.0 END
              * CASE WHEN day BETWEEN DATE '2025-02-10' AND DATE '2025-02-16' THEN 1.45
                     WHEN day BETWEEN DATE '2025-05-20' AND DATE '2025-05-26' THEN 1.35 ELSE 1.0 END
              * CASE WHEN day >= DATE '2025-06-01' THEN shifted_share ELSE normal_share END
              * (0.96 + (hash(day, sku, channel) % 9) / 100.0)
            ) AS INTEGER)) AS uv
          FROM dates CROSS JOIN skus CROSS JOIN channels
        ),
        converted AS (
          SELECT *, CAST(ROUND(
            uv * base_cvr * cvr_factor
            * CASE WHEN sku IN ('phone_x', 'earbuds_y')
                         AND day BETWEEN DATE '2025-06-17' AND DATE '2025-06-30'
                    THEN 0.08 ELSE 1.0 END
          ) AS INTEGER) AS orders
          FROM traffic
        )
        SELECT day, sku, category, channel, price, uv, orders,
               CAST(orders * price AS DOUBLE) AS gmv
        FROM converted
        """)
        con.execute("""CREATE TABLE inventory AS
      SELECT day, sku,
        CASE WHEN sku IN ('phone_x','earbuds_y') AND day BETWEEN DATE '2025-06-17' AND DATE '2025-06-30'
             THEN 0 ELSE 100 + CAST(hash(day, sku) % 80 AS INTEGER) END AS stock
      FROM (SELECT DISTINCT day FROM daily_metrics), (SELECT DISTINCT sku FROM daily_metrics)""")
        con.execute("""CREATE TABLE event_truth AS
          SELECT '促销活动' AS event_type, DATE '2025-02-10' AS start_day, DATE '2025-02-16' AS end_day, '全品类' AS affected_scope, '春节活动带来流量提升' AS hidden_cause
          UNION ALL SELECT '促销活动', DATE '2025-05-20', DATE '2025-05-26', '全品类', '年中预热活动带来流量提升'
          UNION ALL SELECT '渠道变化', DATE '2025-06-01', DATE '2025-06-30', '全品类', '广告占比提升但渠道转化率较低'
          UNION ALL SELECT '库存异常', DATE '2025-06-17', DATE '2025-06-30', 'phone_x,earbuds_y', '供应商延迟导致热销 SKU 缺货'""")
        con.execute(f"CREATE TABLE dataset_metadata AS SELECT {DATA_VERSION} AS version, DATE '2025-01-01' AS start_day, DATE '2025-06-30' AS end_day")
    finally:
        con.close()

def database_ready(path=None):
    path = Path(path or DB)
    if not path.exists():
        return False
    try:
        con = duckdb.connect(str(path), read_only=True)
        try:
            version = con.execute("SELECT version FROM dataset_metadata").fetchone()[0]
            rows = con.execute("SELECT count(*) FROM daily_metrics").fetchone()[0]
            return version == DATA_VERSION and rows == EXPECTED_ROWS
        finally:
            con.close()
    except duckdb.Error:
        return False

def ensure_database(path=None):
    path = Path(path or DB)
    if not database_ready(path):
        build_database(path)
    return path

def connect(path=None):
    path = Path(path or DB)
    ensure_database(path)
    return duckdb.connect(str(path), read_only=True)


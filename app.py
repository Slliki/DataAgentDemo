import streamlit as st
import plotly.express as px
from datetime import datetime
import os
from importlib import reload
from datapilot import data as data_module

# Streamlit 热重载可能保留旧模块；版本升级后缺少新函数时主动刷新。
if not hasattr(data_module, "ensure_database"):
    data_module = reload(data_module)

from datapilot.agent import run_analysis
from datapilot.nlq import generate_sql
from datapilot.openai_sql import generate_sql_openai
from datapilot.tools import query_readonly

st.set_page_config(page_title="星河电商 · DataPilot", layout="wide")
data_module.ensure_database()
st.title("星河电商 · DataPilot 经营分析中心")
st.caption("6 个月可复现模拟数据｜多渠道经营｜只读分析｜事实、假设与结论严格分层")

api_key = os.getenv("OPENAI_API_KEY", "")
api_key_source = "环境变量" if api_key else ""
model_name = os.getenv("OPENAI_MODEL", "gpt-5-mini")
try:
    secret_key = st.secrets.get("OPENAI_API_KEY", "")
    if secret_key:
        api_key = secret_key
        api_key_source = "Streamlit Secrets"
    model_name = st.secrets.get("OPENAI_MODEL", model_name)
except FileNotFoundError:
    pass

def clear_manual_api_key():
    st.session_state.manual_api_key = ""

with st.sidebar:
    st.subheader("Agent 配置")
    manual_api_key = st.text_input(
        "临时填写 OpenAI API Key",
        type="password",
        key="manual_api_key",
        placeholder="sk-...",
        help="只保存在当前 Streamlit 会话内，不会写入文件、数据库或 GitHub。",
    ).strip()
    if manual_api_key:
        api_key = manual_api_key
        api_key_source = "当前会话输入"

    if api_key:
        query_mode = st.radio("SQL 生成方式", ["OpenAI Agent", "本地安全解析"])
        st.success(f"API Key 已加载（{api_key_source}）｜模型：{model_name}")
        if manual_api_key:
            st.button("清除临时 API Key", on_click=clear_manual_api_key)
    else:
        query_mode = "本地安全解析"
        st.info("填写 API Key 后即可使用 OpenAI Agent；留空则使用本地安全解析。")
    st.caption("安全提示：页面不会持久化或显示完整 Key。生产部署请使用环境变量或 Secrets。")

st.subheader("自然语言问数")
with st.form("nlq_form"):
    question = st.text_input(
        "输入你想查询的经营问题",
        value="给我拉出最近一周数码下的 GMV 数据",
        placeholder="例如：最近30天各品类销售额；近7天数码订单；按 SKU 查看最近一周 GMV",
    )
    ask = st.form_submit_button("生成 SQL 并查询", type="primary")

if ask:
    try:
        with st.spinner("正在理解问题、生成安全 SQL 并执行……"):
            if query_mode == "OpenAI Agent":
                plan = generate_sql_openai(question, api_key, model_name)
                plan_source = f"OpenAI Agent · {model_name}"
            else:
                plan = generate_sql(question)
                plan_source = "本地安全解析"
            result = query_readonly(plan.sql)
            st.session_state.nlq_result = result
            st.session_state.nlq_plan = plan
            st.session_state.nlq_source = plan_source
        st.toast("问数查询完成", icon="✅")
    except Exception as exc:
        st.error(str(exc))

if "nlq_result" in st.session_state:
    plan = st.session_state.nlq_plan
    result = st.session_state.nlq_result
    st.caption(f"生成方式：{st.session_state.get('nlq_source', '本地安全解析')}｜{plan.explanation} ‘最近’以模拟数据中的最新日期为准。")
    with st.expander("查看生成的只读 SQL"):
        st.code(plan.sql, language="sql")
    st.dataframe(result, use_container_width=True, hide_index=True)
    if not result.empty and plan.grain != "total" and plan.metric in result.columns:
        x_column = result.columns[0]
        chart = px.line(result, x=x_column, y=plan.metric, markers=True, title=f"{plan.metric_label} 查询结果") if plan.grain == "day" else px.bar(result, x=x_column, y=plan.metric, title=f"{plan.metric_label} 查询结果")
        st.plotly_chart(chart, use_container_width=True)

st.divider()
st.subheader("自动经营巡检")

if "run_count" not in st.session_state:
    st.session_state.run_count = 0

if st.button("开始一键经营巡检", type="primary", use_container_width=False):
    with st.spinner("Data Agent 正在取数、拆解指标并验证原因假设……"):
        st.session_state.report = run_analysis()
        st.session_state.run_count += 1
        st.session_state.completed_at = datetime.now().strftime("%H:%M:%S")
    st.toast("经营巡检已完成", icon="✅")

if "report" not in st.session_state:
    st.info("点击上方按钮开始第一次经营巡检。系统将分析内置的 6 个月模拟经营数据。")
    st.stop()

completed_at = st.session_state.get("completed_at", "本次页面打开前")
st.success(
    f"第 {st.session_state.run_count or 1} 次巡检已完成 · {completed_at}。"
    "模拟数据固定可复现，因此重复巡检的指标结果相同。"
)
r = st.session_state.report
f = r["facts"]
cols = st.columns(4)
metric_values = [
    ("GMV", f"¥{f['gmv']:,.0f}"),
    ("UV", f"{f['uv']:,.0f}"),
    ("订单", f"{f['orders']:,.0f}"),
    ("转化率", f"{f['conversion']:.2%}"),
]
for c, (label, value) in zip(cols, metric_values):
    c.metric(label, value)
st.subheader("诊断明细")
st.dataframe(r["diagnosis"], use_container_width=True)
st.plotly_chart(px.bar(r["diagnosis"], x="category", y="gmv", title="品类 GMV"), use_container_width=True)
st.subheader("证据分层")
st.info("事实：以上指标和品类聚合结果由 DuckDB 查询得到。")
st.warning("原因假设：数码品类转化率下降，可能与核心 SKU 供给异常相关。")
st.success("因果结论：当前 V1 不自动下因果结论；需补充更严格的对照或实验验证。")
st.subheader("补货情景模拟")
st.json(r["simulation"])
with st.expander("任务轨迹"):
    for i, x in enumerate(r["trace"], 1): st.write(f"{i}. {x}")


# Agent 协作约束

- 先获取指标定义，再规划查询；不得凭空编造数字。
- 任何业务陈述标记为 `FACT`、`HYPOTHESIS` 或 `CAUSAL_CONCLUSION`。
- 只有当结果同时显示时间先后、分群差异和交叉验证证据时，才允许使用因果结论；否则使用“可能原因”。
- 仅调用 `query_readonly`、`inspect`、`simulate_restock` 等受限工具。
- 不访问 `event_truth`，不执行 Python/SQL 外的代码，不写数据库。


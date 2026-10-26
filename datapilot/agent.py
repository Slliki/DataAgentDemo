from .tools import inspect_business, diagnose, simulate_restock

def run_analysis(question="巡检经营异常"):
    facts = inspect_business().iloc[0].to_dict()
    detail = diagnose()
    trace = ["接收问题", "读取指标口径", "执行只读聚合", "按品类下钻", "交叉检查库存", "生成证据分层报告"]
    return {"question": question, "facts": facts, "diagnosis": detail, "hypotheses": ["数码品类转化率下降，可能与核心 SKU 供给异常相关"], "conclusions": [], "simulation": simulate_restock(), "trace": trace}


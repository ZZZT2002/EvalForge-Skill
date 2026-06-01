"""三维判分（PROJECT.md §8.3）

总分 = 0.3·tool_recall(F1) + 0.3·tool_order(LCS) + 0.4·argument_accuracy，
归一化到 0-100。

- tool_recall        : 工具集合 F1，不看顺序、不看参数
- tool_order         : 工具名序列的 LCS 相似度（difflib.SequenceMatcher）
- argument_accuracy  : 顺序贪心匹配 + 参数键值比对

顺序贪心：维护 matched_expected_idx，每个 expected 节点最多被一个 predicted
节点消费一次，防止 Agent 重复输出同一工具刷分。这不是二分图匹配，就是顺序贪心。
"""
from difflib import SequenceMatcher
from typing import Any, Dict, List

from config import SCORE_WEIGHTS


def calculate_skill_score(
    predicted: List[Dict[str, Any]],
    expected: List[Dict[str, Any]],
) -> float:
    """返回 0-100 总分。明细见 score_breakdown()。"""
    return score_breakdown(predicted, expected)["total"]


def score_breakdown(
    predicted: List[Dict[str, Any]],
    expected: List[Dict[str, Any]],
) -> Dict[str, float]:
    """返回总分 + 三维分项（badcase 收集需要分项）。各分项与 total 同为 0-100。"""
    # ---------- 边界：对抗样例与空预测 ----------
    if not expected:
        # 期望拒绝执行：predicted 也空 → 满分；执行了 → 0 分
        full = 0.0 if predicted else 100.0
        return _pack(full, full, full)
    if not predicted:
        return _pack(0.0, 0.0, 0.0)

    pred_tools = [c["tool"] for c in predicted]
    exp_tools = [c["tool"] for c in expected]

    recall = _tool_recall_f1(pred_tools, exp_tools)
    order = SequenceMatcher(None, pred_tools, exp_tools).ratio()
    arg = _argument_accuracy(predicted, expected)

    total = (
        SCORE_WEIGHTS["tool_recall"] * recall
        + SCORE_WEIGHTS["tool_order"] * order
        + SCORE_WEIGHTS["argument_accuracy"] * arg
    )
    return _pack(recall * 100, order * 100, arg * 100, total * 100)


def _tool_recall_f1(pred_tools: List[str], exp_tools: List[str]) -> float:
    """集合 F1：基于工具名去重集合，不计顺序与重复。"""
    pred_set, exp_set = set(pred_tools), set(exp_tools)
    inter = len(pred_set & exp_set)
    if inter == 0:
        return 0.0
    precision = inter / len(pred_set)
    recall = inter / len(exp_set)
    return 2 * precision * recall / (precision + recall)


def _argument_accuracy(
    predicted: List[Dict[str, Any]],
    expected: List[Dict[str, Any]],
) -> float:
    """顺序贪心：每个 predicted 找首个同名且未被消费的 expected，比对参数键值。"""
    matched_expected_idx: set = set()
    arg_score = 0.0

    for pred in predicted:
        for j, exp in enumerate(expected):
            if j in matched_expected_idx:
                continue
            if exp["tool"] != pred["tool"]:
                continue
            matched_expected_idx.add(j)
            arg_score += _arg_match_ratio(pred.get("args", {}), exp.get("args", {}))
            break  # 该 predicted 已配对，进入下一个

    return arg_score / len(expected)


def _arg_match_ratio(pred_args: Dict[str, Any], exp_args: Dict[str, Any]) -> float:
    """单对配对节点的参数得分 ∈ [0,1]：正确键数 / 期望键数。"""
    if not exp_args:
        return 1.0  # 期望无参数，工具名匹配即满分
    correct = sum(1 for k, v in exp_args.items() if k in pred_args and pred_args[k] == v)
    return correct / len(exp_args)


def _pack(recall: float, order: float, arg: float, total: float = None) -> Dict[str, float]:
    if total is None:
        total = recall  # 边界情形三项一致
    return {
        "total": round(total, 2),
        "tool_recall": round(recall, 2),
        "tool_order": round(order, 2),
        "argument_accuracy": round(arg, 2),
    }

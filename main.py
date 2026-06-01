"""主流水线入口（PROJECT.md §11）

幂等：每个阶段检查产物是否已存在，存在则跳过。
首跑可一键贯通 A→B→C→D，复跑只补缺失环节。
"""
import json
import os

import config


def benchmark_v1_exists() -> bool:
    return os.path.exists(f"{config.VERSION_HISTORY_DIR}/benchmark_v1.0.0.json")


def benchmark_v11_exists() -> bool:
    return os.path.exists(f"{config.VERSION_HISTORY_DIR}/benchmark_v1.1.0.json")


def seeds_have_feedback() -> bool:
    """seeds.json 中已含 from_badcase 种子则说明 D10 已注入过。"""
    if not os.path.exists(config.SEEDS_PATH):
        return False
    with open(config.SEEDS_PATH, encoding="utf-8") as f:
        seeds = json.load(f)
    return any("from_badcase" in s.get("tags", []) for s in seeds)


def main():
    print(f"[EvalForge-Skill] mode={config.EVAL_MODE} target={config.TARGET_AGENT}")

    # Stage A: 构建
    if not benchmark_v1_exists():
        print("[A] 评测集 v1.0 不存在，启动构建流程")
        # TODO: TaskGenerator().run()
        # TODO: DatasetValidator().run()
        # TODO: publish_v1()
    else:
        print("[A] 检测到已有 v1.0，跳过构建")

    # Stage B+C: 评测 + 衰退检测 + 演进（v1.1 已存在则跳过，避免重复评测）
    if benchmark_v11_exists():
        print("[B+C] 检测到已有 v1.1，跳过评测与演进")
    else:
        print("[B] Agent 实测 + [C] 衰退检测与演进 (→ v1.1)")
        from updater.release import run as run_evolution
        run_evolution(version_old="1.0.0", version_new="1.1.0")

    # Stage D: 反向闭环（已注入过则跳过）
    if seeds_have_feedback():
        print("[D] 检测到 seeds.json 已含 from_badcase 种子，跳过注入")
    else:
        print("[D] Badcase 反向注入")
        from generator.feedback_injector import inject_auto
        with open(config.BADCASES_PATH, encoding="utf-8") as f:
            badcases = json.load(f)
        with open(f"{config.VERSION_HISTORY_DIR}/benchmark_v1.0.0.json", encoding="utf-8") as f:
            benchmark = json.load(f)
        stats = inject_auto(badcases, benchmark, per_skill=2)
        print(f"      注入 {stats['injected']} 条新种子 → seeds 总数 {stats['seeds_total_now']}")


if __name__ == "__main__":
    main()

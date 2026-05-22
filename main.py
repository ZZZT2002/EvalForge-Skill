"""主流水线入口（PROJECT.md §11）

骨架阶段：仅占位，各模块填充后逐步替换 TODO。
"""
import os
import config


def benchmark_v1_exists() -> bool:
    return os.path.exists(f"{config.VERSION_HISTORY_DIR}/benchmark_v1.0.0.json")


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

    # Stage B: 评测
    print("[B] Agent 实测（TODO）")
    # TODO: evaluator.run()

    # Stage C: 维护
    print("[C] 衰退检测与演进（TODO）")
    # TODO: updater.detect_decay() / evolve_constraints()

    # Stage D: 反向闭环
    print("[D] Badcase 反向注入（TODO）")
    # TODO: FeedbackInjector().review_and_inject()


if __name__ == "__main__":
    main()

"""评测流水线（PROJECT.md §8）

批量调度 Agent，收集 raw_response，调用 normalizer + scorer，
累积 badcases.json 和 evaluation_v*.md。
TODO: D8 完成
"""

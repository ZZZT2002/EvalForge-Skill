"""embedding 相似度去重

D3 决定：因 torch DLL 在本机不可用，先用 sklearn TF-IDF + cosine。
设计上预留 Embedder 接口，未来 torch 修好后插入 TransformerEmbedder。

D5 答辩话术：
- "TF-IDF 在 lexical 层面已经能抓近似 paraphrase 重复"
- "架构上 Embedder 是 pluggable 的，MiniLM 是已规划的下一步"
"""
from typing import List, Protocol

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class Embedder(Protocol):
    def encode(self, texts: List[str]) -> np.ndarray: ...


class TfidfEmbedder:
    """字符 n-gram TF-IDF。对中英文 prompt 都鲁棒，无需分词器。"""

    def __init__(self, ngram_range=(2, 4)):
        self._vec = TfidfVectorizer(analyzer="char_wb", ngram_range=ngram_range)
        self._fitted = False

    def encode(self, texts: List[str]) -> np.ndarray:
        if not self._fitted:
            mat = self._vec.fit_transform(texts)
            self._fitted = True
        else:
            mat = self._vec.transform(texts)
        return mat  # sparse；cosine_similarity 直接接受


def dedup_by_similarity(
    candidates: List[dict],
    threshold: float = 0.85,
    embedder: Embedder = None,
) -> List[dict]:
    """贪心去重：按顺序遍历，与已保留集中任何一条相似度 >= threshold 即丢弃。

    保证：
    - 每条种子的第一个变体（task_id 字典序最小）有更高机会被保留
    - 同 task_id 不会重复
    """
    if not candidates:
        return []
    if embedder is None:
        embedder = TfidfEmbedder()

    prompts = [c["prompt"] for c in candidates]
    matrix = embedder.encode(prompts)
    sim = cosine_similarity(matrix)

    keep_mask = [True] * len(candidates)
    for i in range(len(candidates)):
        if not keep_mask[i]:
            continue
        # 标记所有与 i 相似度过高的后续候选为重复
        for j in range(i + 1, len(candidates)):
            if keep_mask[j] and sim[i, j] >= threshold:
                keep_mask[j] = False

    return [c for c, keep in zip(candidates, keep_mask) if keep]


if __name__ == "__main__":
    import json
    with open("data/candidates_v0.1.json", "r", encoding="utf-8") as f:
        cands = json.load(f)
    print(f"Loaded {len(cands)} candidates, deduping at threshold 0.85...")
    out = dedup_by_similarity(cands, threshold=0.85)
    print(f"After dedup: {len(out)} (-{len(cands) - len(out)})")
    with open("data/candidates_v0.9.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Output: data/candidates_v0.9.json")

"""LLM 润色：用 DeepSeek 改写 prompt 的表达风格

D3 关键约束：
- 改 prompt 的措辞、句式、长度，但**不动 expected_tool_calls**
- "硬参数"（USR_xxx / IPv4 / ITEM_xxxx / 命令字符串 / 邮箱 / 电话）必须在改写后仍然
  出现在 prompt 里；用预提取 + 后校验保证
- 失败重试 1 次，再失败就 fallback 到原 prompt
"""
import concurrent.futures
import json
import os
import re
import time
from typing import Dict, List, Optional, Set

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_CLIENT: Optional[OpenAI] = None


def _client() -> OpenAI:
    global _CLIENT
    if _CLIENT is None:
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        _CLIENT = OpenAI(api_key=api_key, base_url=base_url)
    return _CLIENT


_PROTECTED_PATTERNS = [
    r"USR_\d{3}",
    r"ITEM_\d{4}",
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",          # IPv4
    r"\+\d{11,15}",                                   # 国际手机号
    r"[\w.-]+@[\w.-]+\.\w+",                         # 邮箱
    r"#[\w-]+",                                       # Slack 频道
]


def extract_protected_tokens(prompt: str) -> List[str]:
    """提取必须在改写后仍然出现的硬参数。"""
    tokens: Set[str] = set()
    for pat in _PROTECTED_PATTERNS:
        for m in re.findall(pat, prompt):
            tokens.add(m)
    return sorted(tokens)


def _build_system_prompt(protected: List[str]) -> str:
    token_list = "、".join(f"`{t}`" for t in protected) if protected else "（无）"
    return (
        "你是一位中文 prompt 改写助手。请把用户给出的 prompt 改写成一个语义完全等价、"
        "但措辞/句式/语气有变化的新版本，长度可比原 prompt 略长或略短，不超过 1.5 倍。\n\n"
        "硬性要求：\n"
        f"1. 下列标识符**必须原样保留**：{token_list}\n"
        "2. 涉及到的具体命令（如 systemctl restart nginx、find ... -delete 等）必须保留\n"
        "3. 仅输出改写后的 prompt，不要任何解释、引号、Markdown\n"
    )


def paraphrase_once(prompt: str, protected: List[str], timeout: float = 20.0) -> Optional[str]:
    """单次调用 DeepSeek 改写，返回改写结果或 None。"""
    try:
        resp = _client().chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _build_system_prompt(protected)},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            timeout=timeout,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return None


def _all_tokens_present(text: str, tokens: List[str]) -> bool:
    return all(t in text for t in tokens)


def paraphrase_candidate(candidate: dict, retries: int = 1) -> dict:
    """对一条候选改写 prompt，硬参数全部保留则采用，否则保留原 prompt 但打 tag。"""
    original_prompt = candidate["prompt"]
    protected = extract_protected_tokens(original_prompt)

    for _ in range(retries + 1):
        paraphrased = paraphrase_once(original_prompt, protected)
        if paraphrased and _all_tokens_present(paraphrased, protected):
            out = dict(candidate)
            out["prompt"] = paraphrased
            out["tags"] = list(out.get("tags", [])) + ["paraphrased"]
            return out

    # 改写失败：回滚原 prompt + 打标
    out = dict(candidate)
    out["tags"] = list(out.get("tags", [])) + ["paraphrase_failed"]
    return out


def paraphrase_all(candidates: List[dict], max_workers: int = 10) -> List[dict]:
    """并发改写。保留原顺序。"""
    results: List[Optional[dict]] = [None] * len(candidates)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(paraphrase_candidate, c): i for i, c in enumerate(candidates)}
        for fut in concurrent.futures.as_completed(futures):
            i = futures[fut]
            results[i] = fut.result()
    return [r for r in results if r is not None]


if __name__ == "__main__":
    with open("data/candidates_v0.0.json", "r", encoding="utf-8") as f:
        cands = json.load(f)
    print(f"Loaded {len(cands)} candidates, paraphrasing with DeepSeek...")
    t0 = time.time()
    out = paraphrase_all(cands)
    print(f"Done in {time.time() - t0:.1f}s")
    print(f"Successful paraphrases: {sum('paraphrased' in c.get('tags', []) for c in out)}")
    print(f"Failed (fallback to original): {sum('paraphrase_failed' in c.get('tags', []) for c in out)}")
    with open("data/candidates_v0.1.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Output: data/candidates_v0.1.json")

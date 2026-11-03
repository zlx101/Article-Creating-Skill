# -*- coding: utf-8 -*-
"""原创审查：检测成稿与素材原文的连续字重合（默认 12 字）。

用法：
    python scripts/originality_diff.py --draft 成稿.md --source 原文.md [--source 另一篇.md] [--n 12]

判定（以成稿归一化字数为分母）：
    < 3%        无明显字面痕迹
    3% – 8%     需重组：改论述顺序、换例子、换句式
    >= 8%       不安全：退回重写，不做逐句修补

注意：脚本只算字面重合，结构和论证方式是否照搬仍要人工判断。
退出码：0 = 无明显痕迹或需重组；1 = 不安全；2 = 参数或文件错误。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

KEEP_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")


def normalize(text: str) -> str:
    return "".join(KEEP_RE.findall(text)).lower()


def ngram_set(text: str, n: int) -> set:
    if len(text) < n:
        return set()
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def merged_segments(covered, n: int):
    """把被覆盖的位置合并成片段 (start, end)，end 不含。"""
    segments = []
    length = len(covered)
    i = 0
    while i < length:
        if covered[i]:
            j = i
            while j < length and covered[j]:
                j += 1
            segments.append((i, min(j + n - 1, length)))
            i = j
        else:
            i += 1
    return segments


def main() -> int:
    ap = argparse.ArgumentParser(description="成稿与素材原文的重合检测")
    ap.add_argument("--draft", required=True, help="成稿 Markdown")
    ap.add_argument("--source", action="append", required=True, help="素材原文，可重复")
    ap.add_argument("--n", type=int, default=12, help="连续重合字数阈值，默认 12")
    args = ap.parse_args()

    draft_path = Path(args.draft)
    if not draft_path.exists():
        print(f"找不到成稿：{draft_path}")
        return 2

    draft = normalize(draft_path.read_text(encoding="utf-8-sig"))
    if not draft:
        print("成稿没有可比较的中文内容。")
        return 2

    if len(draft) < args.n:
        print(f"成稿仅 {len(draft)} 字，短于阈值 {args.n}，跳过检测。")
        return 0

    covered = [False] * len(draft)
    print("== 原创重合检测 ==")
    print(f"成稿：{draft_path}（归一化 {len(draft)} 字）｜阈值：连续 {args.n} 字")
    print("")

    for src in args.source:
        src_path = Path(src)
        if not src_path.exists():
            print(f"[跳过] 找不到素材：{src_path}")
            continue
        source = normalize(src_path.read_text(encoding="utf-8-sig"))
        grams = ngram_set(source, args.n)
        hits = 0
        for i in range(len(draft) - args.n + 1):
            if draft[i:i + args.n] in grams:
                hits += 1
                for k in range(i, i + args.n):
                    covered[k] = True
        rate = (hits * args.n) / len(draft) * 100 if len(draft) else 0.0
        print(f"素材：{src_path.name}（归一化 {len(source)} 字）→ 命中 {hits} 处，重合率 {rate:.1f}%")

    total_covered = sum(1 for c in covered if c)
    overall = total_covered / len(draft) * 100
    segments = merged_segments(covered, args.n)
    segments.sort(key=lambda seg: seg[1] - seg[0], reverse=True)

    print("")
    print(f"合计重合率：{overall:.1f}%（{total_covered} 字）")
    if segments:
        print(f"重合片段：{len(segments)} 处，最长 {segments[0][1] - segments[0][0]} 字")
        for start, end in segments[:10]:
            print(f"  · 第 {start} 字起，{end - start} 字：{draft[start:end]}")
    else:
        print("未发现连续重合片段。")

    print("")
    if overall >= 8:
        verdict = "不安全：退回重写，重新找切入点与论述顺序，不要逐句修补"
        code = 1
    elif overall >= 3:
        verdict = "需重组：改有痕迹段落的顺序、例子与句式，再复检"
        code = 0
    else:
        verdict = "无明显字面痕迹（结构是否照搬仍需人工判断）"
        code = 0

    print(f"判定：{verdict}")
    return code


if __name__ == "__main__":
    sys.exit(main())

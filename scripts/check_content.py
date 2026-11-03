# -*- coding: utf-8 -*-
"""内容成稿自检：按目标平台档检查段落长度、句长、AI 腔黑名单、加粗密度、
表情符号、开头结尾套话、标题候选数量与字数。

用法：
    python scripts/check_content.py 成稿.md
    python scripts/check_content.py 成稿.md --platform xiaohongshu
    python scripts/check_content.py --list-platforms

平台档：generic / wechat / zhihu / xiaohongshu / toutiao / blog / newsletter

退出码：0 = 无 FAIL；1 = 存在 FAIL（必须改完再交付）；2 = 参数或文件错误。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 与 references/platform-profiles.md 保持一致；改这里必须同步改文档
# 段上限 = 单行字数 × 2（两行规则，见 references/writing-rules.md 第六节）
PROFILES = {
    "generic": {
        "label": "通用长文", "line_chars": 25,
        "sentence": 60, "titles": 6, "title_len": 18,
        "length": (1000, 2500), "bold_per": 300, "emoji": "forbid", "emoji_max": 0,
    },
    "wechat": {
        "label": "公众号", "line_chars": 25,
        "sentence": 60, "titles": 6, "title_len": 18,
        "length": (1000, 2500), "bold_per": 300, "emoji": "forbid", "emoji_max": 0,
    },
    "zhihu": {
        "label": "知乎", "line_chars": 30,
        "sentence": 70, "titles": 3, "title_len": 25,
        "length": (1500, 3000), "bold_per": 400, "emoji": "forbid", "emoji_max": 0,
    },
    "xiaohongshu": {
        "label": "小红书", "line_chars": 18,
        "sentence": 40, "titles": 3, "title_len": 20,
        "length": (600, 1000), "bold_per": 300, "emoji": "allow", "emoji_max": 5,
    },
    "toutiao": {
        "label": "头条/百家号", "line_chars": 28,
        "sentence": 50, "titles": 5, "title_len": 30,
        "length": (800, 1500), "bold_per": 250, "emoji": "forbid", "emoji_max": 0,
    },
    "blog": {
        "label": "博客/技术专栏", "line_chars": 32,
        "sentence": 70, "titles": 3, "title_len": 40,
        "length": (1500, 3000), "bold_per": 400, "emoji": "forbid", "emoji_max": 0,
    },
    "newsletter": {
        "label": "Newsletter", "line_chars": 28,
        "sentence": 60, "titles": 3, "title_len": 25,
        "length": (2000, 4000), "bold_per": 400, "emoji": "forbid", "emoji_max": 0,
    },
}

A_LEVEL = [
    "赋能", "闭环", "底层逻辑", "颗粒度", "抓手", "护城河", "降维打击",
    "认知升级", "顶层设计", "生态位", "组合拳", "飞轮", "心智", "范式",
    "链路", "锚点", "第一性原理", "价值锚定", "增量博弈",
    "不得不说", "值得深思", "引起广泛讨论", "在这个时代", "让我们一起",
    "本文将", "综上所述", "总的来说", "希望这篇文章", "干货满满", "深度好文",
]

B_LEVEL = [
    "更重要的是", "与此同时", "换句话说", "某种意义上", "某种程度上",
    "本质上", "显然", "事实上", "可以说",
]

BAD_OPENING = ("在当今", "随着", "在这个", "众所周知", "近年来", "如今的时代")
BAD_ENDING = ("希望这篇文章", "希望对你有帮助", "共勉", "愿我们", "愿你我", "以上就是")

BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
SENT_SPLIT_RE = re.compile(r"[。！？…]+")
QUOTE_RE = re.compile(r'["\']')
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF\uFE0F]"
)
# 先否定再肯定的对偶句：先否定一项、随即用「而是/，是」肯定另一项
ANTITHESIS_RE = re.compile(
    r"(?:不是|并非|不在于)[^。！？；\n]{1,30}(?:而是|，\s*是|,\s*是)"
)
TITLE_LINE_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|")

# 机械连接词：只标位置不给信息，见 references/writing-rules.md 第一节
MECH_CONNECTIVES = (
    "首先", "其次", "再次", "最后", "然后", "接下来",
    "另一方面", "与此同时", "综上所述", "总的来说", "总之",
)
# 正文禁用字符，见 references/writing-rules.md 第五节
BANNED_CHARS = ("「", "」", "——", "---", ">")
NUM_RANGE_RE = re.compile(r"\d\s*-\s*\d")


def count_cjk(text: str) -> int:
    return len(CJK_RE.findall(text))


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2]
    return text


def content_paragraphs(text: str):
    """返回 [(行号, 段落文本)]，跳过标题、表格、代码块、引用块。"""
    result = []
    in_code = False
    buffer: list[str] = []
    start_line = 0

    def flush():
        nonlocal buffer, start_line
        if buffer:
            para = "\n".join(buffer).strip()
            if para:
                result.append((start_line, para))
            buffer = []

    for idx, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            flush()
            continue
        if in_code:
            continue
        if not line:
            flush()
            continue
        if line.startswith("#") or line.startswith("|") or line.startswith(">"):
            flush()
            continue
        if not buffer:
            start_line = idx
        buffer.append(line)
    flush()
    return result


def parse_title_table(text: str):
    """从标题候选表里抽出 (序号, 标题, 字数-若给出)。"""
    rows = []
    for line in text.splitlines():
        m = TITLE_LINE_RE.match(line.strip())
        if not m:
            continue
        seq = m.group(1)
        title = m.group(2).strip().strip("`").strip()
        if not title or title in {"标题", "---"} or set(title) <= set("-: "):
            continue
        rows.append((seq, title))
    return rows


def split_sentences(para: str):
    return [s.strip() for s in SENT_SPLIT_RE.split(para) if count_cjk(s.strip()) >= 2]


def check_banned_chars(para: str, line_no: int, issues) -> None:
    """正文禁用字符。加粗语法 **...** 先剥掉，不算正文符号。"""
    body = BOLD_RE.sub("", para)
    for ch in BANNED_CHARS:
        if ch in body:
            add(issues, "FAIL", "BANNED", f"第 {line_no} 行出现禁用字符 {ch}")
    if "*" in body:
        add(issues, "FAIL", "BANNED", f"第 {line_no} 行出现单星号，列表与强调都不许用")
    if "-" in body:
        if NUM_RANGE_RE.search(body):
            add(issues, "WARN", "BANNED", f"第 {line_no} 行数字范围用了横线，改写成到或至")
        else:
            add(issues, "FAIL", "BANNED", f"第 {line_no} 行出现连字符，列表符不许用")


def check_connectives(sents, line_no: int, issues) -> None:
    """机械连接词出现在句首或段首即判，不看全篇频率。"""
    for s in sents:
        for word in MECH_CONNECTIVES:
            if s.startswith(word):
                add(issues, "FAIL", "CONNECTIVE", f"第 {line_no} 行以机械连接词开头：{word}")
                break


def check_rhythm(sents, line_no: int, issues) -> None:
    """连续短句与句式过于整齐，两类都要看。"""
    lens = [count_cjk(s) for s in sents]
    for i in range(len(lens) - 2):
        window = lens[i:i + 3]
        if min(window) >= 4 and max(window) - min(window) <= 1:
            add(issues, "WARN", "RHYTHM", f"第 {line_no} 行连续三句长度接近（{window}），句式过于整齐")
            break
    for i in range(len(lens) - 3):
        if all(n < 12 for n in lens[i:i + 4]):
            add(issues, "WARN", "RHYTHM", f"第 {line_no} 行连续四句都不足 12 字，像电报体")
            break


def add(issues, level, code, message):
    issues.append((level, code, message))


def check(text: str, profile_key: str):
    profile = PROFILES[profile_key]
    issues = []
    body = strip_frontmatter(text)
    paras = content_paragraphs(body)
    body_text = "\n".join(p for _, p in paras)
    total = count_cjk(body_text)

    # A 级黑名单
    for word in A_LEVEL:
        n = body_text.count(word)
        if n:
            add(issues, "FAIL", "A-LEVEL", f"A 级表达「{word}」出现 {n} 次")

    # B 级：同篇两次以上
    for word in B_LEVEL:
        n = body_text.count(word)
        if n >= 2:
            add(issues, "WARN", "B-LEVEL", f"B 级过渡「{word}」出现 {n} 次")

    # 段落长度：两行是硬规则，超一成记 WARN，超四成记 FAIL
    limit = profile["line_chars"] * 2
    for line_no, para in paras:
        n = count_cjk(para)
        if n > limit * 1.4:
            add(issues, "FAIL", "PARA", f"第 {line_no} 行段落 {n} 字，超过两行上限 {limit} 字四成以上")
        elif n > limit:
            add(issues, "WARN", "PARA", f"第 {line_no} 行段落 {n} 字，略超两行上限 {limit} 字")

    # 禁用字符
    for line_no, para in paras:
        check_banned_chars(para, line_no, issues)

    # 机械连接词与句式节奏
    for line_no, para in paras:
        sents = split_sentences(para)
        check_connectives(sents, line_no, issues)
        check_rhythm(sents, line_no, issues)

    # 句长
    s_limit = profile["sentence"]
    for line_no, para in paras:
        for sent in SENT_SPLIT_RE.split(para):
            sent = sent.strip()
            n = count_cjk(sent)
            if n > s_limit:
                add(issues, "WARN", "SENT", f"第 {line_no} 行有 {n} 字长句：{sent[:24]}…")

    # 加粗密度
    bold = len(BOLD_RE.findall(body_text))
    if total >= 300:
        if bold == 0 and profile_key != "xiaohongshu":
            add(issues, "WARN", "BOLD", "全篇没有加粗，缺少核心观点标记")
        elif bold and total / bold < 150:
            add(issues, "WARN", "BOLD", f"加粗 {bold} 处，平均每 {total // bold} 字一处，过密")

    # 表情符号
    emojis = EMOJI_RE.findall(body_text)
    if profile["emoji"] == "forbid" and emojis:
        add(issues, "FAIL", "EMOJI", f"该平台不用表情符号，出现 {len(emojis)} 个")
    elif len(emojis) > profile["emoji_max"]:
        add(issues, "WARN", "EMOJI", f"表情符号 {len(emojis)} 个，超过建议上限 {profile['emoji_max']} 个")

    # 篇长
    lo, hi = profile["length"]
    if total and total < lo:
        add(issues, "WARN", "LENGTH", f"全文 {total} 字，低于平台区间 {lo}–{hi}，可能论证不足")
    elif total > hi:
        add(issues, "WARN", "LENGTH", f"全文 {total} 字，高于平台区间 {lo}–{hi}，考虑拆分或删减")

    # 开头套话
    if paras:
        opening = paras[0][1]
        for word in BAD_OPENING:
            if word in opening[:40]:
                add(issues, "FAIL", "OPENING", f"开头出现套话「{word}」，换成具体的事")
                break

    # 结尾套话
    if paras:
        ending = paras[-1][1]
        for word in BAD_ENDING:
            if word in ending:
                add(issues, "WARN", "ENDING", f"结尾出现套话「{word}」，换成具体动作或判断")
                break

    # 先否定再肯定的对偶句
    for line_no, para in paras:
        for m in ANTITHESIS_RE.finditer(para):
            snippet = m.group(0)
            add(
                issues, "FAIL", "ANTITHESIS",
                f"第 {line_no} 行用了先否定再肯定的对偶句：「{snippet[:24]}…」，拆成两句陈述",
            )

    # 英文引号
    for line_no, para in paras:
        if QUOTE_RE.search(para):
            add(issues, "WARN", "QUOTE", f"第 {line_no} 行出现英文引号，中文用「」")

    # 标题候选
    titles = parse_title_table(body)
    if titles:
        need = profile["titles"]
        if len(titles) < need:
            add(issues, "WARN", "TITLE", f"标题候选 {len(titles)} 个，平台要求 {need} 个")
        for seq, title in titles:
            n = count_cjk(title)
            if n > profile["title_len"]:
                add(issues, "FAIL", "TITLE", f"第 {seq} 个标题 {n} 字，超过 {profile['title_len']} 字上限：{title}")

    return issues, total, len(paras), bold, len(titles)


def main() -> int:
    ap = argparse.ArgumentParser(description="内容成稿自检（按平台档）")
    ap.add_argument("path", nargs="?", help="成稿 Markdown 文件")
    ap.add_argument("--platform", default="generic", choices=sorted(PROFILES),
                    help="目标平台档，默认 generic")
    ap.add_argument("--list-platforms", action="store_true", help="列出所有平台档")
    args = ap.parse_args()

    if args.list_platforms:
        for key in sorted(PROFILES):
            p = PROFILES[key]
            print(
                f"{key:12s} {p['label']:10s} 段≤{p['line_chars'] * 2}字(两行) "
                f"句≤{p['sentence']} 标题{p['titles']}个/≤{p['title_len']}字 "
                f"篇长{p['length'][0]}-{p['length'][1]} 表情{p['emoji']}"
            )
        return 0

    if not args.path:
        print("缺少成稿文件路径。用 --list-platforms 查看所有平台档。")
        return 2

    target = Path(args.path)
    if not target.exists():
        print(f"找不到文件：{target}")
        return 2

    text = target.read_text(encoding="utf-8-sig")
    issues, total, para_count, bold, title_count = check(text, args.platform)
    profile = PROFILES[args.platform]

    fails = [i for i in issues if i[0] == "FAIL"]
    warns = [i for i in issues if i[0] == "WARN"]

    print("== 内容自检报告 ==")
    print(f"文件：{target}")
    print(f"平台档：{profile['label']}（{args.platform}）")
    print(
        f"汉字数：{total}｜段落数：{para_count}｜加粗：{bold} 处｜标题候选：{title_count} 个"
    )
    print("")
    for level, code, msg in fails + warns:
        print(f"[{level}] {code}: {msg}")
    if not issues:
        print("未发现结构或语言问题。")
    print("")
    print(f"汇总：FAIL {len(fails)}｜WARN {len(warns)}")
    print("结论：" + ("不通过，先改 FAIL 项" if fails else "通过（WARN 项按需人工判断）"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

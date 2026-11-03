# 内容创作 / Article Creating

一个**平台参数化**的通用内容创作 Skill：从灵感、素材或语音稿出发，先定角度和思路，再产出有独立判断、语言朴素、原创不照搬的成稿，并按目标平台给足标题候选与发布前质检。

不是「帮我把话说漂亮」，而是把写作流程里最容易省掉的三件事固定下来：**先想清楚写什么**、**有素材时必须原创审查**、**发布前必须逐项质检**。

## 解决什么问题

| 常见问题 | 本技能怎么处理 |
|---|---|
| 拿到素材直接改写，一眼看出出处 | 原创审查硬门禁：抽事实 → 弃用原文结构 → 重建论述 → 12 字连续重合检测 |
| 写完一看全是 AI 腔 | A/B/C 三级黑名单 + 脚本检查，FAIL 必须清零 |
| 一稿想投所有平台，结果都不合适 | 平台档案：段落、句长、标题数、篇长、加粗、表情按档取 |
| 用户讲了一堆，整理完观点变了 | 只删表达不动观点，改方向必须回到用户确认 |
| 观点单薄，只有信息没有判断 | 第 3 问质检强制要求「至少一处只属于作者的解释/经验/反例」 |

## 平台档案

| 平台 | 段落 | 句长 | 标题 | 篇长 |
|---|---|---|---|---|
| 通用长文（默认） | ≤200 字 | ≤60 字 | 6 个 / ≤18 字 | 1000–2500 |
| 公众号 | ≤200 字 | ≤60 字 | 6 个 / ≤18 字 | 1000–2500 |
| 知乎 | ≤250 字 | ≤70 字 | 3 个 / ≤25 字 | 1500–3000 |
| 小红书 | ≤80 字 | ≤40 字 | 3 个 / ≤20 字 | 600–1000 |
| 头条 / 百家号 | ≤150 字 | ≤50 字 | 5 个 / ≤30 字 | 800–1500 |
| 博客 / 技术专栏 | ≤250 字 | ≤70 字 | 3 个 / ≤40 字 | 1500–3000 |
| Newsletter | ≤180 字 | ≤60 字 | 3 个 / ≤25 字 | 2000–4000 |

新增平台按 `references/platform-profiles.md` 的五项确认后再补，不凭印象编参数。

## 安装

### 方式一：作为目录使用

把仓库克隆到客户端的 skills 目录，目录名保持 `article-creating-skill`（与 frontmatter 的 `name: article-creating` 相差 `-skill` 后缀，属于允许写法），也可以直接改名为 `article-creating`：

```text
git clone https://github.com/zlx101/Article-Creating-Skill.git ~/.cursor/skills/article-creating-skill
```

加载路径：

```text
~/.cursor/skills/article-creating-skill/SKILL.md   # Cursor
~/.claude/skills/article-creating/SKILL.md         # Claude Code（改名为 article-creating）
```

`SKILL.md` 必须在技能根目录，文件名大小写敏感。

### 方式二：上传 zip 包

打包时保持 `SKILL.md` 在包根目录：

```text
article-creating/SKILL.md
article-creating/references/...
```

部分平台（如 WorkBuddy）还要求 frontmatter 带 `version`、`display_name`、`description_zh` 等字段，上传前按平台提示补齐，否则会提示「解析失败」。

## 使用

直接说需求即可，技能会按 8 步推进并停在需要你拍板的地方：

```text
写一篇知乎回答，讲讲带新人为什么讲道理没用
这篇文章按我的角度重写一篇，发小红书
选题定了，帮我起 6 个公众号标题
这是我的语音稿，整理成一篇博客
```

关键停止点：**角度未经你选定不写正文**；**思路单未经你确认不出初稿**；**质检有任一项不通过不交付**。

## 目录结构

```text
SKILL.md                      入口：使命、任务契约、平台档案、红线、工作流、暗礁、索引
references/
  platform-profiles.md        各平台参数与额外要求（第 1 步必读）
  topic-discovery.md          找角度：热点方向与观点方向
  knowledge-mining.md         调积累：检索与可用性判断
  drafting-rules.md           三层打磨与 AI 腔黑名单
  originality-review.md       原创审查 7 条与判定级别
  title-method.md             标题角度与取舍
  quality-gates.md            7 问质检与合成规则
templates/
  topic-options.md            选题建议输出格式
  outline.md                  思路单格式
  title-options.md            标题候选输出格式
examples/
  dialogue-demo.md            一次完整对话怎么走
  platform-samples.md         同一判断写成公众号/小红书/知乎三稿
  ai-tone-rewrite.md          10 组 AI 腔对照
scripts/
  check_content.py            按平台档检查结构、语言、标题
  originality_diff.py         与素材原文的连续字重合检测
evals/
  trigger-cases.json          命中/改写/排除/近邻用例
```

## 脚本

两个脚本都只用标准库，不需要安装依赖。

```text
python scripts/check_content.py 成稿.md --platform xiaohongshu
python scripts/check_content.py --list-platforms
python scripts/originality_diff.py --draft 成稿.md --source 原文.md
```

退出码 0 为通过，1 为需要修改。

## 边界

不处理：纯排版与格式终检、小说正文、公文、学术论文、口播或分镜脚本、一次性翻译或摘要、替用户定选题和观点、编造素材。

需要排版时请配合专门的排版技能（例如 `wechat-article-format`），本技能只交付内容与结构。

## 证据状态

如实说明，避免把设计预期当成已验证效果：

- **工程账**：结构、命名、相对链接、包内文件已核对；未对脚本做真实运行测试。
- **质量账**：触发用例已写入 `evals/trigger-cases.json`（命中 / 同义改写 / 排除 / 近邻），尚未跑真实提示词回归。
- **对外账**：未做真实发布与读者反馈；平台参数来自各平台公开的发布规范与常见实践，未逐平台实测，属 `missing evidence`。

## 许可

MIT，见 [LICENSE](LICENSE)。

作者：成云杉（[@zlx101](https://github.com/zlx101)）

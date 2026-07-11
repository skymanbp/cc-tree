# cc-tree

[![CI](https://github.com/skymanbp/cc-tree/actions/workflows/ci.yml/badge.svg)](https://github.com/skymanbp/cc-tree/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/skymanbp/cc-tree?color=6aa84f&label=release)](https://github.com/skymanbp/cc-tree/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8e7cc3)
[![Star on GitHub](https://img.shields.io/github/stars/skymanbp/cc-tree?style=social)](https://github.com/skymanbp/cc-tree/stargazers)

> 语言：中文。英文规范版：[`README.md`](README.md)。如有歧义，以英文版为准。
<!-- i18n-source-sha256: ced3dccaa4312aa03b351e8d279b70aba5f249f555473c4b11bd5f7e5a9a5779 -->

一个 Claude Code 插件：**一台通用的放射状树探索引擎，四个可替换的
preset**。用它来做发散式构思、对抗式批评、设计空间探索，或代码审计
—— 同一台引擎，不同的词汇。英文是默认输出语言和机器 schema 语言；
根、证据、所引来源与自定义内容可以使用任何语言，而 `--lang` 选择本次
运行人类可读的输出语言。

```bash
claude plugin marketplace add skymanbp/cc-tree
claude plugin install cc-tree@cc-tree
```

> 由 [`sci-paper`](https://github.com/skymanbp/sci-paper) 的 `brainstorm`
> + `paper-attack-tree` 技能重构而来，剥离了论文特定的锚点，并通过
> preset 参数化。

## 立意 —— 一棵思想的系统发生树

cc-tree 把*任何*开放式思考任务都当作**一棵从单一根向外生长的系统
发生树**。根就是你的输入（一个主题、一份文档、一条代码路径、一个
设计提示）。每个节点都由**同样的 12 个 framing 过程**展开，每个子节点
被完整推导并打分，只有高价值（`advances`）的叶子才会被重新展开 ——
直到这棵树达到**实质性收敛**，而不是某个任意的数量。

![cc-tree as a radial "phylogenetic tree of thoughts": one ROOT at the
centre, depth as concentric rings growing outward, four coloured "clades"
for the four presets (brainstorm / attack / design / code-audit). There is
no single winner — a branch can succeed ("advances"), hit a dead end
("pruned" / "blocked"), or keep branching and be judged again, so several
wins appear at different depths and the branches reach uneven length. Each
terminal leaf carries a verdict marker — advances, kept, pruned, or blocked
— and the total leaf count is the width.](docs/assets/cc-tree-radial-tree.svg)

<sub>灵感来自放射状的<em>生命之树</em>。本 README 其余部分用到的词汇
全在这一张图里：<strong>root（根）</strong>（位于中心的输入 —— topic ·
artifact · code · design）、<strong>node（节点）</strong>（一个想法 /
批评 / 选项 / 发现，各自带有同一套 12 字段推导）、<strong>depth
（深度）</strong>（framing 递归形成的同心圆环；分支停在不同的圆环上，
因为只有 <code>advances</code> 叶子才会重新展开）、<strong>width
（宽度）</strong>（终端叶子 / 末梢的总数，无论它们落在何处 —— 由收敛
决定，而非手挑的上限），以及 <strong>n</strong>（树中节点总数）。图源：
<a href="tools/gen_radial_tree.py"><code>tools/gen_radial_tree.py</code></a>。</sub>

```
  the tree grows OUTWARD from one root. a branch can WIN, hit a DEAD END, or
  keep BRANCHING and be judged again — no single winner, wins at any depth:

    ROOT ──┬── pruned                      (dead end at depth 1)
           ├── advances                    (a win at depth 1)
           └── advances ──┬── pruned        (this branch keeps going…)
                          └── advances ──┬── advances   (…a deeper win)
                                         └── blocked

  each node → 12 framings (§3.A–§3.L) → 12-field derivation → score → verdict;
  branches that keep advancing grow deeper; pruned / blocked ones stop.
```

逐节点的循环，精确地说：

```mermaid
flowchart LR
    R([root<br/>topic · artifact · code · design]) --> F{{12 framing passes<br/>§3.A–§3.L}}
    F --> D[per-node 12-field derivation<br/>evidence · no hedging · no defer]
    D --> S[score 5 dims → verdict]
    S -->|advances| RE((re-expand<br/>this leaf))
    RE --> F
    S -->|kept / pruned| K[keep in tree,<br/>don't re-expand]
    S -->|blocked| B[INCOMPLETE_FORBIDDEN<br/>drive to completion]
    B --> D
    S --> C{§6 convergence?<br/>6 conditions all true}
    C -->|no| RE
    C -->|yes| OUT[/final report +<br/>tree.md · tree.json/]
```

有两条性质让它不只是"循环里的头脑风暴"：**(1)** 每个叶子都用
`file:line` / URL 证据完整推导 —— 对 `defer / future-work / TODO /
NEEDS-MORE-INFO` 叶子有一条硬性禁令（§0.5）；**(2)** 终止依据是*实质性
收敛*（六个同时成立的条件），而绝非"耐心耗尽"。

## 它交付什么

### 1 skill

| 技能 | 它做什么 |
|---|---|
| `/cc-tree:tree` | 通用放射状树引擎。加载一个 preset，构建 §2 基线，然后对每个节点递归施加 12 个 framing 过程，直到**稳定收敛**（最近 2 轮没有新的高判定分支 + 全部 12 个 framing 都被执行 + 全部叶子完整）。宽度 × 深度默认为 ∞；资源上限是可选的。对 `defer / future-work / TODO / NEEDS-MORE-INFO` 叶子有硬性禁令。 |

### 4 presets（`presets/<name>.md`）

| Preset | 何时使用 | 判定词汇（advances / kept / pruned / blocked） |
|---|---|---|
| `brainstorm` | 发散式构思；浮现尚未探索的研究方向或穷尽式问题求解路径 | `PROMISING / MARGINAL / DEAD-END / NEEDS-MORE-INFO` |
| `attack` | 对一份成品 artifact（文档、论证、设计方案）的对抗式批评；浮现最具破坏力的审稿人式攻击 | `CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN` |
| `design` | 设计空间探索；想要一张针对某项决策的 选项 × 取舍 × 可逆性 表 | `RECOMMENDED / VIABLE / NOT-RECOMMENDED / NEEDS-MORE-INFO` |
| `code-audit` | 代码风味的对抗式审查（安全 / 性能 / 契约 / API 误用 / 数据泄露） | `CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN` |

### 5 ergonomic slash-commands（`commands/<name>.md`）

`/cc-tree:brainstorm <topic>` ≡ `/cc-tree:tree <topic> --preset brainstorm`
（`:attack`、`:design`、`:code-audit` 同理）。输入更短；底层是同一台
引擎。此外还有 `/cc-tree:tree-chain`，用于依次运行多个 preset（见下方
**跨 preset 串联**）。

### 引擎规范与文档

技能本身约 250 行导航；完整引擎在
[`docs/ENGINE.md`](docs/ENGINE.md)（中文平行版：[`docs/ENGINE.zh.md`](docs/ENGINE.zh.md)）。
另见：

- [`docs/framings.md`](docs/framings.md) —— 12 个 framing 及每个 preset
  的示例（中文：[`docs/framings.zh.md`](docs/framings.zh.md)）
- [`docs/presets.md`](docs/presets.md) —— 如何撰写你自己的 preset
  （中文：[`docs/presets.zh.md`](docs/presets.zh.md)；schema 由
  `tools/validate_plugin.py` 在 CI 中强制）
- [`docs/chaining.md`](docs/chaining.md) —— 跨 preset 串联契约
  （中文：[`docs/chaining.zh.md`](docs/chaining.zh.md)）
- [`field-profiles/README.md`](field-profiles/README.md) —— 通过
  `--field` 实现领域感知的审稿人加权（中文：
  [`field-profiles/README.zh.md`](field-profiles/README.zh.md)）
- [`examples/attack/README.md`](examples/attack/README.md) —— attack
  preset 示例指南（中文：
  [`examples/attack/README.zh.md`](examples/attack/README.zh.md)）

## 语言契约

英文是文档的规范语言，也是默认输出语言。用 `--lang <tag>` 指定一个
显式的类 BCP-47 输出标签（`en`、`zh`、`zh-Hans`、`zh-Hant`、`fr-CA`
……），或用 `--lang auto` 来检测主调用/根内容的主导自然语言。混合的、
无法识别的、仅含路径的、仅含代码的 auto 输入会回退到 `en`。`zh` 表示
维护的简体中文约定；要繁体中文请用 `zh-Hant` 显式请求。

一次运行从开始、经恢复到串联，始终保持一种语言。人类散文（节点陈述、
推导、证据解释、警告与报告叙述）使用解析出的语言。机器标识符保持
英文：命令与旗标、frontmatter 与 JSON 键、`root_kind` 值、判定
角色/标签、score 键、`node_schema` 字段、framing ID、状态/标记 token、
文件名、路径、代码、公式与 API 标识符。输入的根、artifact、注释、
术语表、领域画像正文、自定义 preset 散文、引用与所引证据可以使用任何
语言；引文保持逐字原样，并在需要时附加本地化解释。绑定性的解析与恢复
规则见 [`docs/ENGINE.md`](docs/ENGINE.md) §1.0。

文档版本管理遵循 [`docs/languages.json`](docs/languages.json)：无后缀的
`X.md` 文件是规范英文，`X.zh.md` 文件是维护的中文平行版，源摘要
（digest）会让过期的翻译在 CI 中失败。

## 安装

cc-tree 是一个自包含的目录式 marketplace。用 Claude Code 插件 CLI
安装它：

```bash
# 1. Register this repo as a marketplace (directory source)
claude plugin marketplace add <path-to-this-repo>

# 2. Install the plugin from it
claude plugin install cc-tree@cc-tree

# (optional) sanity-check the manifests before/after
claude plugin validate <path-to-this-repo>
claude plugin list
```

重启你的 Claude Code 会话以加载插件（新插件在会话开始时加载）。技能
随后以带命名空间的形式出现：`/cc-tree:tree`、`/cc-tree:brainstorm`
等。要拾取之后的改动，运行 `claude plugin update cc-tree` 并重启。

## 快速开始

```bash
# Divergent ideation
/cc-tree:brainstorm "ways to detect dark-matter substructure with weak lensing"

# Adversarial critique of a finished doc
/cc-tree:attack ./paper.tex

# Design-space exploration
/cc-tree:design "auth flow for our internal admin tool"

# Code audit
/cc-tree:code-audit ./src/api/upload.py

# Use the engine directly with an explicit preset
/cc-tree:tree <root> --preset brainstorm
/cc-tree:tree <file> --preset ./my-custom-preset.md

# Domain-aware reviewer weighting (physics ships built-in; author other
# fields from field-profiles/_template.md)
/cc-tree:attack ./paper.tex --field physics

# Explicit Chinese human-readable output; machine keys/statuses stay English
/cc-tree:attack ./paper.tex --lang zh

# Detect the dominant natural language of the root; ambiguous inputs fall back to en
/cc-tree:brainstorm "如何验证弱引力透镜中的暗物质子结构" --lang auto
```

每次运行都会增量写入 `<out>/<UTCdate>__<slug>/`（默认
`tree-out/...`；各 preset 命令默认写入 `brainstorm-out/`、
`attack-out/` 等）。输出是一份 `tree.md` + `tree.json` + 一份由 preset
决定的最终报告（brainstorm 为 `shortlist.md`，attack 为
`confirmed.md`，等等）。

## 跨 preset 串联

一个自然的工作流会把一个 preset 最好的输出喂给下一个：
**brainstorm** → 取 top-K → 用 **design** 落成每个 → **attack** 攻击
胜者。

```bash
/cc-tree:tree-chain "ways to cut our API p99 latency" \
    --stages brainstorm,design,attack --top-k 3
```

每个阶段独立收敛；阶段之间的 top-K 交接总是被记录（绝不静默截断）。
契约：[`docs/chaining.md`](docs/chaining.md)。其底层是通用的
`--seed-from <primary.md>` 旗标（别名 `--from-prior`），它用先前运行的
产物给一次运行播种。

## 为什么？

|  | 临时的"陪我头脑风暴" | cc-tree |
|---|---|---|
| **覆盖度** | 那 3 个显而易见的角度 | 每节点 12 个固定 framing，含唱反调 / 反转 / 高风险 |
| **完整度** | "我们以后可以看看 X" | 对 `defer / TODO / future-work` 叶子有硬性禁令 —— 每个叶子都用 `file:line` / URL 证据推导 |
| **何时停止** | 当聊天渐渐冷场 | 实质性收敛（6 个条件），而非节点计数 |
| **输出** | 一段聊天记录 | `tree.md` + `tree.json` + 一份结构化的逐 preset 报告 |
| **复用** | 每次都从头重新提示 | 一台引擎，4 个 preset，可串联（`brainstorm → design → attack`） |

两条理由，用散文说。

**理由 1：结构在重复。** 头脑风暴、对抗式审查、设计探索和代码审计
共享同一副骨架 —— *从 N 个 framing 生成候选 → 把每个完整推导 → 打分
→ 在高价值分支上递归 → 在稳定收敛（而非耐心耗尽）时终止*。把这副骨架
编码一次、再把其余参数化，胜过写四个近乎重复的技能。

**理由 2：失败模式也在重复。** LLM 做的每一个发散任务都有同样的
懒惰均衡吸引子：推给未来工作、用同义词替换生成近乎重复的分支、跳过
高风险/唱反调的 framing、在第一个变慢的回合就宣布收敛。引擎对这些
全部编码了硬性禁令（§0 forbidden patterns），它们对头脑风暴一个研究
方向和审计一个 Python 文件同样适用。

完整的设计理据见 [`EVALUATION.md`](EVALUATION.md)。

## 与 sci-paper 的关系

[`skymanbp/sci-paper`](https://github.com/skymanbp/sci-paper) 是这台
引擎最初的家，作用域限定在科学论文写作 / 审查。cc-tree 是与领域无关的
抽取；sci-paper 保留其论文特定版本的独立性（无耦合）。如果你写论文，
用 sci-paper。如果你想把引擎用在别的任何事情上，用 cc-tree。

## 许可证

[MIT](LICENSE)。本仓库中的代码、技能、preset、命令与文档均采用 MIT
许可。`tree-out/` / `brainstorm-out/` / `attack-out/` / `design-out/`
/ `code-audit-out/` 目录是用户生成的，默认被 `.gitignore` 忽略。

# cc-tree

[![CI](https://github.com/skymanbp/cc-tree/actions/workflows/ci.yml/badge.svg)](https://github.com/skymanbp/cc-tree/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/skymanbp/cc-tree?color=6aa84f&label=release)](https://github.com/skymanbp/cc-tree/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8e7cc3)
[![Star on GitHub](https://img.shields.io/github/stars/skymanbp/cc-tree?style=social)](https://github.com/skymanbp/cc-tree/stargazers)

> 语言：中文。英文规范版：[`README.md`](README.md)。如有歧义，以英文版为准。
<!-- i18n-source-sha256: 08b5f461867a4492f4faf7b581daaa2e59f810d79ae45acef1cb59ccb6444e5a -->

**cc-tree 是一个 Claude Code 插件，它把开放式思考变成一棵可以被审计的树。**
一台通用的放射状树探索引擎，四个可替换的 preset：发散式头脑风暴、对抗式批评、
设计空间探索、代码审计 —— 同一台引擎，不同的词汇。它是一种有纪律的、落盘持久化的
tree-of-thoughts 搜索：每个节点都必须带着 `file:line` 或 URL 证据被完整推导，
`defer / future-work / TODO / NEEDS-MORE-INFO` 式的叶子被硬性禁止，
运行的终止依据是实质性收敛，而不是耗尽某个节点预算。

```bash
claude plugin marketplace add skymanbp/cc-tree
claude plugin install cc-tree@cc-tree
```

> 由 [`sci-paper`](https://github.com/skymanbp/sci-paper) 的 `brainstorm`
> + `paper-attack-tree` 技能重构而来，剥离了论文特定的锚点，并通过
> preset 参数化。

## What it is

cc-tree 把*任何*开放式思考任务都当作**一棵从单一根向外生长的系统发生树**。
根就是你的输入 —— 一个主题、一份文档、一条代码路径、一个设计提示。每个节点都由
**同样的 12 个 framing 过程**展开，每个子节点被完整推导并打分，只有高价值
（`advances`）的叶子才会被重新展开，直到这棵树达到**实质性收敛**，
而不是停在某个任意的数量上。

![cc-tree as a radial phylogenetic tree of thoughts: one ROOT at the
centre, depth as concentric rings growing outward, four coloured clades
for the four presets (brainstorm / attack / design / code-audit). There
is no single winner — a branch can succeed (advances), hit a dead end
(pruned / blocked), or keep branching and be judged again, so several
wins appear at different depths and the branches reach uneven length.
Each tip carries a verdict marker, and the width is the number of
terminal leaves — blocked tips are excluded until they are driven to
completion, so this snapshot is a run still in
flight.](docs/assets/cc-tree-radial-tree.svg)

<sub>灵感来自放射状的<em>生命之树</em>。本文档后面用到的全部词汇都在这张图里：
<strong>root</strong>（中心的输入 —— 主题 · 工件 · 代码 · 设计）、<strong>node</strong>
（一个想法 / 批评 / 方案 / 发现，各自都有同样的 12 字段推导）、<strong>depth</strong>
（一圈圈的 framing 递归年轮；因为只有 <code>advances</code> 叶子会被重新展开，
不同分支会停在不同的圈层）、<strong>width</strong>（终端叶子的数量，
无论它们落在哪一圈 —— 由收敛判据决定，而不是手工挑一个上限；按 §0.1，
<code>blocked</code> 树梢在被推进到完整之前一律不计入），以及
<strong>n</strong>（树中节点总数）。图的源码：
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

## How it works

五个不可再分的步骤，全部写在 [`docs/ENGINE.md`](docs/ENGINE.md) 里，
并且对每一个 preset 都有约束力。

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

### 1 · 把根锚定在真实证据上（§2）

recipe 由 preset 提供；引擎负责强制每一个根字段都带上 `file:line`、URL
或命令输出作为引用。可选的术语拷问前奏（§2.0）会在生成任何一个分支之前，
把根节点里的技术名词短语锁定到你项目的术语表上，这样整棵树才不会花掉一百个叶子
去解一个错的问题。

### 2 · 让每个节点走完 12 个 framing（§3）

每个节点 —— 先是根，然后是每一片 `advances` 叶子 —— 都要过一遍全部 12 个
framing，每一个都必须至少产出一个子节点。这个集合是固定的，
model 没法悄悄跳过那些让它不舒服的角度。

| Pass | 它强迫你做什么 |
|---|---|
| §3.A First-principles | 剥掉一条承重假设，看还剩下什么 |
| §3.B Inversion | 试试否定、对偶，以及它失效的边界 |
| §3.C Cross-disciplinary | 从至少 3 个其他领域移植工具 |
| §3.D Adversarial / red team | 找出杀伤力最大的 3 条反驳 |
| §3.E Constraint variation | 放松一条约束，收紧另一条 |
| §3.F Scale extrapolation | 1000× / 0.001× / 领域边界 |
| §3.G Substitution | 换掉一个组件，观察变化 |
| §3.H Office-hours 6Q | YC 式的需求真实性拷问 |
| §3.I Contrarian | 这里哪条主流共识可能是错的？ |
| §3.J Failure-driven | 把一个具体的当前失败变成下一个问题 |
| §3.K High-risk asymmetric | 强制至少 1 条低概率、范式级的分支 |
| §3.L Meta self-audit | 对模型自身盲区的 7 问自审 |

还有第十三个过程 §3.X，除非加了 `--no-online`，否则每个节点都要做一次外部
交叉核查（先 `WebSearch`，再 `WebFetch` 真实页面）。完整提示词与每个 preset
的示例见 [`docs/framings.md`](docs/framings.md)。

### 3 · 把每个子节点推导成 12 个字段（§4）

每个子节点都要填进 preset 的 12 字段节点 schema —— 陈述、父 framing、位置、
推导、假设、预测、辩护、替代解读、修复/代价、外部核查、分支潜力、临时判决。
空白、含糊或推脱的字段不会产出一个"弱一点"的节点；它们产出的是一个
`INCOMPLETE_FORBIDDEN` 节点，**阻塞整轮终止**，直到它被推进到完整为止。

### 4 · 打分，然后决定要不要递归（§5）

五个由 preset 声明的维度，每个取 0–3 的整数，加总上限 15。`score ≥ 11`
（外加 preset 自己的附加门槛）→ `advances`，这片叶子会被重新展开；`8–10` →
`kept`；`≤ 7` → `pruned`；任何被未经验证的断言主导的 → `blocked`。
近似重复的兄弟节点在余弦相似度 ≥ 0.85 时合并（§5.4），
所以 width 代表的是覆盖度，不是复读。

### 5 · 只在实质性收敛时停下（§6）

六个条件必须**同时**成立：不存在未完成节点；最近两轮的 `advances` 比例已经跌到
`--min-novelty-ratio` 以下；12 个 framing 全部触发过；每一片 `advances` 叶子都被
重新展开过且再没长出新东西；至少存在一条被完整推导的 §3.K 高风险分支；
并且没有任何用户上限被触发。如果先撞到了上限，引擎会如实报告
`WIDTH_CAP_REACHED` / `DEPTH_CAP_REACHED` / `ROUNDS_EXHAUSTED` ——
绝不谎称 `CONVERGED` —— 而且仍会先把所有在途叶子补完。

## Why it's different

|  | 随口一句"陪我头脑风暴一下" | cc-tree |
|---|---|---|
| **覆盖度** | 那 3 个显而易见的角度 | 每个节点 12 个固定 framing，含反共识 / 反转 / 高风险 |
| **完整度** | "这个我们回头再看" | 硬禁 `defer / TODO / future-work` 叶子 —— 每片叶子都带 `file:line` / URL 证据 |
| **何时停** | 聊到没话说为止 | 实质性收敛（6 个条件），不是数够了几个节点 |
| **产物** | 一段聊天记录 | 落盘的 `tree.md` + `tree.json` + 按 preset 结构化的报告 |
| **抗崩溃** | 往上翻聊天记录，祈祷 | 每个节点即时写盘；重新调用即可续跑 |
| **复用** | 每次都从头重新提示 | 一台引擎、4 个 preset、可串联（`brainstorm → design → attack`） |

两条理由，用散文说。

**理由 1：结构是重复的。** 头脑风暴、对抗式评审、设计探索、代码审计，
共享同一副骨架 —— *从 N 个 framing 生成候选 → 把每个都完整推导 → 打分 →
在高价值分支上递归 → 在稳定收敛处终止，而不是在耐心耗尽处终止*。
把这副骨架写一次、其余参数化，胜过写四个近乎重复的技能。

**理由 2：失效模式也是重复的。** LLM 做的每一类发散任务，
都有同样的偷懒平衡点：推给 future-work、用换词法造出近乎重复的分支、
跳过高风险 / 反共识的 framing、在第一个变慢的回合就宣布收敛。
引擎对这些全部编码了硬禁令（§0.5 禁止模式，§F1–§F8），
它们对"头脑风暴一个研究方向"和"审一个 Python 文件"同样有效。

完整的设计理据 —— 包括为什么是 12 个 framing 而不是 7 个或 20 个，
以及 cc-tree 与学术界的 Tree-of-Thoughts、与 agent 循环有何不同 ——
见 [`docs/EVALUATION.md`](docs/EVALUATION.md)。

## Feature reference

### Exploration engine

- **12 个 framing 过程**，每节点每轮全跑（§3.A–§3.L），外加 §3.X
  外部交叉核查；`--min-frameworks` 的硬下限就是 12。
- **12 字段推导**（§4），每个字段都必须非空、不含糊、并带引用。
- **5 维打分**（§5.1），每维 0–3 整数，上限 15，映射到四角色判决（§5.2）。
- **兄弟节点合并**，余弦相似度 ≥ 0.85（§5.4），被合并的节点仍然可见，
  并打上 `MERGED_INTO=<id>` 标签。
- **六条件收敛判据**（§6.1），配一张显式的终止决策表（§6.2）；
  上限只是逃生阀，从来不算成功。
- **fan-out ≥ 5 时强制子代理并行**（§8.1），并配再验证契约：
  主代理要重新核对子代理返回的每一条引用，子节点才算数。

### Presets — 4 shipped, unlimited custom

每个 preset（[`presets/`](presets/)）提供词汇；谁都不能削弱通用规则（§10）。

| Preset | 什么时候用 | 根 | 判决（advances / kept / pruned / blocked） | 主产物 |
|---|---|---|---|---|
| `brainstorm` | 发散式构思；挖出没被探索过的研究方向或穷尽解题路径 | topic | `PROMISING / MARGINAL / DEAD-END / NEEDS-MORE-INFO` | `shortlist.md` |
| `attack` | 对成稿工件（文档、论证、提案）做对抗式批评 | artifact | `CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN` | `confirmed.md` |
| `design` | 设计空间探索；想要一张方案 × 取舍 × 可逆性的对照表 | design-prompt | `RECOMMENDED / VIABLE / NOT-RECOMMENDED / NEEDS-MORE-INFO` | `options.md` |
| `code-audit` | 代码味的对抗式评审（安全 / 性能 / 正确性 / 契约） | code | `CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN` | `findings.md` |

自己写一个只需要一份带规定 frontmatter schema 的 `.md` —— 见
[`docs/presets.md`](docs/presets.md)。这套 schema 是 CI 强制的，
所以格式不对的 preset 在跑起来之前就会被拦下。

### Commands

| 命令 | 等价于 |
|---|---|
| `/cc-tree:tree <root> --preset <name\|path>` | 引擎本身；唯一接受自定义 preset 路径的命令 |
| `/cc-tree:brainstorm <topic>` | `/cc-tree:tree <topic> --preset brainstorm` |
| `/cc-tree:attack <file>` | `/cc-tree:tree <file> --preset attack` |
| `/cc-tree:design <prompt\|file>` | `/cc-tree:tree <prompt> --preset design` |
| `/cc-tree:code-audit <path>` | `/cc-tree:tree <path> --preset code-audit` |
| `/cc-tree:tree-chain <root> --stages …` | 多个 preset 依次跑，阶段之间传递 top-K |

这些外壳还会改掉默认输出目录（`brainstorm-out/`、`attack-out/` 等），
并携带 preset 专属 flag，比如 `attack` 的
`--focus <section|claim|equation>`。

### Quality gates — the 8 forbidden patterns

违反其中任何一条都会让该轮作废（§0.5）。它们在每种输出语言里都按语义强制，
而不是一份英文短语黑名单。

| 关卡 | 禁止 |
|---|---|
| §F1 | 凭记忆断言 —— 每条外部断言都必须在同一轮内被验证 |
| §F2 | 伪发散 —— 换词造出的兄弟节点算同一个分支，会被合并 |
| §F3 | 跳过推导 —— 不许"显然"、不许"细节从略"；数字必须过一遍 `python` 自检 |
| §F4 | 规避风险 —— 每轮必须完整推导一条高风险分支，无论它最后是什么判决 |
| §F5 | 伪收敛 —— "我没新想法了"不等于 §6 收敛 |
| §F6 | 中途追问 —— 根和 preset 一旦加载就全自动跑完 |
| §F7 | 自行收窄上限 —— 引擎不得擅自调小 `--width` / `--depth` / `--rounds` |
| §F8 | 推脱式叶子 —— `defer / future work / TODO / 待定 / NEEDS-MORE-INFO` 一律判 `INCOMPLETE_FORBIDDEN` |

### Domain weighting — field profiles

`--field <name|path>` 会加载一份**领域视角档案**
（[`field-profiles/`](field-profiles/)）：四份简短清单 —— 审稿人关注点、
领域共识、常见失效模式、证据门槛 —— 用来重新排定 12 个 framing 先探索哪些分支，
并抬高引用标准（§2.2）。档案与 preset 无关：同一份档案能让 `attack`
审一篇论文更锋利，也能让 `brainstorm` 找研究方向、让 `code-audit`
审一份模拟代码更锋利。插件自带一份物理档案
（[`field-profiles/physics.md`](field-profiles/physics.md)）；
其他领域从
[`field-profiles/_template.md`](field-profiles/_template.md) 开始写。
档案找不到只会告警并继续 —— 加权是增强项，从来不是阻塞项。

### Cross-preset chaining

一条很自然的工作流是把一个 preset 最好的产物喂给下一个：
**brainstorm** → 取 top-K → 逐个 **design** → 对赢家做 **attack**。

```bash
/cc-tree:tree-chain "ways to cut our API p99 latency" \
    --stages brainstorm,design,attack --top-k 3
```

每个阶段独立收敛；阶段之间的 top-K 交接一定会被记录，绝不静默截断。
底层机制是通用的 `--seed-from <primary.md>` flag（别名 `--from-prior`），
它用上一轮运行的产物给新一轮播种，所以你也可以手工串。契约见
[`docs/chaining.md`](docs/chaining.md)。

### Output, resume, and crash-safety

每个节点在它的 12 个字段填满的那一刻就落盘（§7.1）—— 不是攒到最后一起写。
就算进程被杀、上下文窗口被填满、或者你中途打断，磁盘上的树在最后一个完成节点
之前都是自洽的。用同一个 `--out <dir>` 重新调用，引擎就会从 id 最大的叶子继续。
`tree.json` 是机器可读的事实源；`tree.md` 是人看的视图；`REPORT.md` 是
§7.4 的最终报告。

### Bilingual output and documentation

`--lang <tag|auto>` 选择本次运行人类可读的输出语言（`en`、`zh`、`zh-Hans`、
`zh-Hant`、`fr-CA` 等）；`auto` 会检测根的主导自然语言，遇到混合、无法识别、
纯路径、纯代码的输入则回退到 `en`。**机器骨架在任何语言下都保持英文**：
flag、frontmatter 与 JSON 键、`root_kind` 取值、判决标签、score key、
`node_schema` 字段、framing ID、状态 token、文件名与路径。根文本、工件、
术语表、自定义 preset 的散文、引文与引述证据可以用任何语言，
引述保持原文逐字不动，只在旁边补一段本地化解释，而不是替换掉它。
一次运行从开始到续跑、到串联全程只用一种语言（§1.0）。

文档本身遵守同一条规则：不带后缀的 `X.md` 是规范英文版，`X.zh.md` 是
持续维护的中文平行版，登记在 [`docs/languages.json`](docs/languages.json) 中，
每份译文都记录了英文源的 SHA-256 摘要，所以过期的译文会让 CI 失败。

### Extensibility

| 你想加什么 | 就写 | 由谁校验 |
|---|---|---|
| 一种新的探索模式 | 一份带 frontmatter schema 的 preset `.md` | preset schema 检查 + 外壳配对检查 |
| 一个新的领域视角 | 一份带四个 `##` 小节的 field profile `.md` | field-profile schema 检查 |
| 一种更短的输入方式 | 一份 command `.md` 外壳 | command frontmatter + flag 文档化检查 |
| 一种新的文档语言 | 在 `docs/languages.json` 里加一条 `pairs` | 摘要、标题、代码围栏与机器 token 的一致性 |

### Engineering guarantees

`tools/validate_plugin.py` 会在每一个 pull request、以及每一次推到 `main`
的 push 上跑七组检查，覆盖 Python 3.11 与 3.13：

| 检查 | 在什么情况下失败 |
|---|---|
| manifests | 插件与市场清单的版本或身份信息漂移 |
| skills | `SKILL.md` 没有 frontmatter，或它的 `name` 与所在目录不一致 |
| presets | 违反任何一条 preset schema 规则（§10–§11） |
| commands | 命令没有描述，或某个 preset 发布时没带它的外壳 |
| tools | 有 Python 文件无法解析 |
| cross-refs | 死锚点、解析不了的相对链接、越界的示例行号引用、未文档化的命令 flag、格式错误的 field profile、悬空的 `§N` 引用 |
| i18n | 未登记的文档、过期摘要、标题或围栏结构分叉、译文过薄或直接抄英文、丢失机器 token |

关键在于：这份 README 声称的一切，要么可以执行，要么被 CI 检查。
文档、运行时提示词与 schema 三者之间的漂移，是本仓库最当回事的缺陷类别。

## Install

cc-tree 是一个自包含的目录型 marketplace。用 Claude Code 的插件 CLI 安装：

```bash
# 1. Register this repo as a marketplace (directory or GitHub source)
claude plugin marketplace add skymanbp/cc-tree

# 2. Install the plugin from it
claude plugin install cc-tree@cc-tree

# (optional) sanity-check the manifests before/after
claude plugin validate <path-to-this-repo>
claude plugin list
```

重启 Claude Code 会话以加载插件（新插件在会话启动时加载）。技能随后会带命名空间
出现：`/cc-tree:tree`、`/cc-tree:brainstorm` 等。要让后续改动生效，
运行 `claude plugin update cc-tree` 并重启。

## Quick start

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

# Quick capped run when you want a taste rather than convergence
/cc-tree:brainstorm "topic" --width 20 --depth 2 --no-online
```

一个从输入到产物的完整实例见
[`examples/attack/`](examples/attack/README.md)。

## Flag reference

通用 flag 对每个 preset 都生效。带逐条语义的权威表格在
[`skills/tree/SKILL.md`](skills/tree/SKILL.md) 里。

| Flag | 默认 | 含义 |
|---|---|---|
| `--preset <name\|path>` | *必填* | `brainstorm` / `attack` / `design` / `code-audit`，或你自己的路径 |
| `--lang <tag\|auto>` | `en` | 本地化散文的输出语言；机器 token 保持英文 |
| `--width N` | ∞ | 最终叶子数上限 |
| `--depth N` | ∞ | 相对根的树深上限 |
| `--rounds N` | `conv` | 展开轮数上限；`conv` = 由 §6 收敛终止 |
| `--max-branches N` | ∞ | 每节点每轮的新分支上限；下限是 12 |
| `--out <dir>` | 按命令而定 | 输出目录 |
| `--glossary <path>` | 按 preset 而定 | §2.0 术语拷问用的术语表 |
| `--field <name\|path>` | 无 | 领域加权用的 field profile |
| `--seed-from <primary.md>` | 无 | 用上一轮的产物给 depth-1 播种（别名 `--from-prior`） |
| `--no-grill` | 关 | 跳过 §2.0 术语前奏 |
| `--no-online` | 关 | 禁用 `WebSearch` / `WebFetch` |
| `--min-frameworks N` | 12 | 每节点最少 framing 数；下限就是 12 |
| `--min-novelty-ratio R` | 0.15 | §6.1 收敛判据里 `advances` 比例的阈值 |

`tree-chain` 另有 `--stages <a,b,c>`（默认 `brainstorm,design,attack`）
和 `--top-k N`（默认 3）。preset 可以文档化自己的 flag，
比如 `attack` 的 `--focus <section|claim|equation>`。

## Output layout

每次运行都增量写入它的 `--out` 目录，而那个目录**就是**本次运行的目录 ——
你传进去的路径后面不会再被追加任何东西。带日期的那一段只属于*默认值*：
引擎是 `tree-out/<UTCdate>__<slug>/`，按 preset 的命令分别是
`brainstorm-out/<UTCdate>__<slug>/`、`attack-out/…`、`design-out/…`、
`code-audit-out/…`，`tree-chain` 则是 `chain-out/…`。

```
<out>/
├── tree.md              # outline of every node; primary human view
├── tree.json            # full data for every node; machine source of truth
├── glossary-anchors.md  # §2.0 prelude output (unless --no-grill)
├── <primary>.md         # shortlist.md / confirmed.md / options.md / findings.md
├── <secondary>.md*      # marginal.md / refuted.md / pending.md / …
├── REPORT.md            # §7.4 final report (also echoed to the terminal)
└── nodes/
    └── <id>.md          # spilled when a node's evidence exceeds 100 lines
```

这些目录默认全部被 `.gitignore` 掉 —— 它们是你的内容，不是插件的。

## Repository map

```
cc-tree/
├── .claude-plugin/        Plugin + marketplace manifests (fixed location)
├── commands/              Slash-command wrappers, one per preset + tree-chain
├── skills/tree/           The engine skill (SKILL.md) Claude Code loads
├── presets/               The 4 shipped presets — resolved by --preset <name>
├── field-profiles/        Domain lenses — resolved by --field <name>
├── docs/                  Engine spec, framings, authoring guides, rationale
│   ├── assets/            Generated diagrams
│   └── languages.json     Bilingual document manifest + machine-token registry
├── examples/attack/       A worked example: input, expected output, how to rerun
├── tools/                 Repo validators and generators (no runtime dependency)
│   └── tests/             Self-tests for the validator, parser, and i18n contract
└── .github/workflows/     CI: validator + self-tests on Python 3.11 and 3.13
```

运行时的代码与内容住在 `commands/`、`skills/`、`presets/`、`field-profiles/`；
`docs/`、`examples/`、`tools/`、`.github/` 底下的一切，
都是为了规定、演示或验证它们而存在的。

## Documentation index

从 [`docs/README.md`](docs/README.md) 这份带注索引开始。简要版：

| 文档 | 什么时候读它 |
|---|---|
| [`docs/ENGINE.md`](docs/ENGINE.md) | 你想要有约束力的契约 —— §0 到 §11 |
| [`docs/framings.md`](docs/framings.md) | 你想要 12 个 framing 提示词及各 preset 示例 |
| [`docs/presets.md`](docs/presets.md) | 你要写一个 preset |
| [`docs/chaining.md`](docs/chaining.md) | 你要把多个 preset 串起来 |
| [`field-profiles/README.md`](field-profiles/README.md) | 你要写一个领域视角档案 |
| [`examples/attack/README.md`](examples/attack/README.md) | 你想看真实的输入与产物 |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | 你想要设计理据，以及被否掉的替代方案 |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 你准备提一个 pull request |
| [`CHANGELOG.md`](CHANGELOG.md) | 你想要逐版本的历史 |

上面每一份文档都有维护中的中文平行版 `X.zh.md`，
除了 `docs/EVALUATION.md`、`CONTRIBUTING.md` 和 `CHANGELOG.md` ——
它们在 [`docs/languages.json`](docs/languages.json) 中被声明为仅保留规范英文。

## What cc-tree is not

- **不是一次性的头脑风暴工具。** 引擎是递归的、以收敛终止的；
  一次真实运行要花几分钟到几小时。
- **不是聊天界面。** 一旦调用就跑到收敛，中途不再追问（§F6）。
  你通过下一次调用的 flag 来操舵。
- **不能替代领域专家。** 它产出的是带引用的结构化探索；
  该行动哪些叶子，仍然由人来决定。
- **不捆绑任何模型。** 它是纯粹的提示词工程，跑在你现有的 Claude Code
  模型设置之上。
- **不是 linter。** `code-audit` 找的正是静态分析器找不到的东西：
  依赖威胁模型的、契约层面的、跨文件推理的缺陷。

## Related terms

如果你是搜下面这些词找来的，那 cc-tree 大概正是你要的：
面向 Claude Code 的 tree of thoughts（ToT）· 结构化 LLM 推理 ·
递归探索型 agent · AI 头脑风暴工具 · 对抗式评审 / red-team 提示词 ·
审稿式论文批评 · 审稿回复准备 · LLM 代码审计与安全评审 ·
设计空间探索与取舍分析 · 架构决策支持 · 研究选题 · 发散思维框架 ·
多代理 fan-out · LLM 搜索的收敛判据 · Claude Code 插件、技能与斜杠命令 ·
中英双语提示词工程。

## Relationship to sci-paper

[`skymanbp/sci-paper`](https://github.com/skymanbp/sci-paper)
是这台引擎最初的家，范围限定在科学论文写作与评审。cc-tree 是它领域无关的
抽取版；sci-paper 保留自己那套论文专用版本，两者互不耦合。
如果你写论文，用 sci-paper。如果你想把这台引擎用在别的地方，用 cc-tree。

## Contributing

欢迎提 issue 和 pull request。[`CONTRIBUTING.md`](CONTRIBUTING.md)
讲了仓库布局、能在本地复现 CI 的那几条命令，以及最容易绊倒新贡献者的那些
不变式 —— 其中包括：preset 是被 schema 校验的、每个 preset 都必须带上它的
命令外壳、每个新增的 Markdown 文件都必须登记进 `docs/languages.json`，
以及改英文文档就必须刷新对应中文平行版的源摘要。
（这里刻意不写条数：一个文件里写数字、另一个文件里放清单，正是本仓库
反复在自己身上查出来的那种漂移。）

## License

[MIT](LICENSE)。本仓库中的代码、技能、preset、命令与文档均以 MIT 授权。
运行产物目录（`tree-out/`、`brainstorm-out/`、`attack-out/`、`design-out/`、
`code-audit-out/`、`chain-out/`）由用户生成，默认被 `.gitignore` 掉。

# 跨 preset 串联（Cross-preset chaining）

> 语言：中文。英文规范版：[`docs/chaining.md`](chaining.md)。如有歧义，以英文版为准。
<!-- i18n-source-sha256: 16d6fd23211dec75eba8fdde36d3fc3289b1fb69d54c3990e197d14e28862f82 -->

一个自然的工作流会把若干 preset 依次串起来，把每个阶段最好的输出
喂给下一个阶段：

> **brainstorm**（我们能做什么？）→ 取 top-K → 用 **design** 把每个
> 想法落成具体选项 → 挑出胜者 → 在投入之前用 **attack** 攻击这个胜者。

`tree-chain`（[`commands/tree-chain.md`](../commands/tree-chain.md)）
会自动执行这条流水线；本文档定义每个阶段所依赖的**交接契约**
（handoff contract），因此你也可以手工串联，或搭建自己的流水线。

## 交接契约

每个 preset 都会写出一份由 `advances` 判定叶子组成的**主产物**
（`docs/ENGINE.md` §7.2），并按该 preset 自己声明的排序键排序 ——
`brainstorm` / `design` 按分数降序，`attack` 按 severity 降序，
`code-audit` 按 severity × exploit-likelihood 降序（每个 preset 的
`output_artifacts` 注释才是权威）：

| Preset | 主产物 | 每行是一个… | 排序依据 |
|---|---|---|---|
| brainstorm | `shortlist.md` | 研究想法 / 方向 | 分数降序 |
| design | `options.md` | 设计选项 | 分数降序 |
| attack | `confirmed.md` | 已确认的批评 | severity 降序 |
| code-audit | `findings.md` | 已确认的发现 | severity × exploit-likelihood 降序 |

下一阶段如何消费这份文件，取决于它所属 preset 的 `root_kind`
—— 见下方 **Root 还是 seeds**。对于 `topic` / `design-prompt` 阶段，
用的是 `--seed-from <primary.md>`（`docs/ENGINE.md` §2.3）：列表里的
每一项都成为一个 depth-1 seed 节点并被重新展开。不需要任何重新排版
—— 主产物本来就是逐行一项的。

### Top-K extraction

`tree-chain` 从每个阶段的主产物中，**按该产物自己的排序键取 top-K**
（默认 K=3）并带入下一阶段。因为每份产物都已按其声明的键排序，
"top-K" 就是前 K 项。被丢弃的尾部会被报告出来（绝不静默截断 ——
`docs/ENGINE.md` §F7 的精神）：链路日志会写明
"seeded 3 of 11; dropped 8 below the cut"。

### Language propagation

`tree-chain` 在 stage 1 之前**恰好一次**解析 `--lang <tag|auto>`。随后
它把解析得到的具体 `output_language` 标签 —— 而不是 `auto` —— 传给每个
阶段、每个逐项子运行以及每个 framing 子代理。省略 `--lang` 解析为
`en`；`auto` 使用第一阶段主调用/根内容，并遵循
[`ENGINE.md`](ENGINE.md) §1.0 的回退规则。后续产物绝不会触发第二次
检测，所以一条链路不会在语言之间漂移。

`CHAIN_REPORT.md` 会在逐阶段状态旁记录 `language_request`、
`output_language` 与 `language_source`。一次被恢复的链路会复用记录下来
的具体标签。一个相互冲突的显式标签会在下一个阶段运行之前以
`EARLY_STOP=language_mismatch` 停止；没有语言元数据的遗留链路输出被
视为英文。机器键、状态、判定标签、文件名、路径与代码保持规范英文，
即使人类可读的阶段报告使用另一种语言。

### Root 还是 seeds（下一阶段）

- **brainstorm → design**：用 `--seed-from shortlist.md` 运行 `design`
  （不需要新的根 —— `docs/ENGINE.md` §2.3 允许一次带 seed 的运行
  "instead of a fresh root" 起步）。每个被 seed 的想法作为 depth-1
  seed 节点进入，并被展开为具体选项；该想法的 `predictions` /
  `assumptions` 会带入选项节点的目标/约束。
- **design → attack**：被选中的选项文件（其 `option_<id>.md`，带
  `mechanism` + `trade_offs`）作为 attack 阶段的**根 artifact** 传入
  —— attack 的 `root_kind` 是 `artifact`，所以该选项是被批评的对象，
  而不是 seed。（把 `--seed-from` 用于 attack 是保留给 seed *批评*
  的，例如经由 `--from-prior` 从先前的审查报告导入。）
- **anything → code-audit**：只有当某阶段产出了真实的代码路径
  （作为 `code` 根传入）时才有意义；否则跳过并记录原因。

## 一个完整示例

```bash
# 1. Diverge on directions
/cc-tree:brainstorm "ways to cut our API p99 latency" --width 30
#    → brainstorm-out/<ts>__.../shortlist.md  (11 ideas, score-sorted)

# 2. Design the top 3 ideas into concrete options
/cc-tree:design --seed-from brainstorm-out/<ts>__.../shortlist.md
#    → design-out/<ts>__.../options.md

# 3. Attack the single best option before committing
/cc-tree:attack ./design-out/<ts>__.../option_<id>.md
```

`tree-chain` 替你运行这三步，并把各步输出串起来：

```bash
/cc-tree:tree-chain "ways to cut our API p99 latency" \
    --stages brainstorm,design,attack --top-k 3
```

## 串联**不是**什么

- **不是**一次重新验证过程。Seed 以被接受（`advances`）的状态进入；
  重点是在它们下面长出的子树，而不是重新评判它们本身
  （`docs/ENGINE.md` §2.3 + §9 的"re-list known issues"反模式）。
- **不是**跨阶段的自动收敛。每个阶段独立收敛（§6）；`tree-chain`
  只是把它们排序，并在阶段之间施加 top-K 切割。
- **不是**逐阶段的语言检测。链路只解析一次、传播一个具体标签，并把
  它记录在 `CHAIN_REPORT.md` 里。
- **不是**无损的。top-K 切割会刻意丢弃低分尾部条目。这个切割总是被
  记录下来，因此损失是可见的。

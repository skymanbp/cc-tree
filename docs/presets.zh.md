# 撰写一个 cc-tree preset

> 语言：中文。英文规范版：[`docs/presets.md`](presets.md)。如有歧义，以英文版为准。
<!-- i18n-source-sha256: 761ef4e6f8e3e9c14a3cb1c42ee460e708ec8f74999d385349d498a9c45ef9f1 -->

一个 preset 是单个 `.md` 文件，它为一个用例定制那台通用引擎
（[`ENGINE.md`](ENGINE.md)）。它提供六个可覆盖的槽位（词汇 + 配方），
且不削弱引擎的任何一条普适规则。

本文档涵盖：(1) 必需的 frontmatter schema，(2) preset 正文里放什么，
(3) 引擎强制执行的合规规则。

[`../presets/`](../presets/) 中随插件发布的 4 个 preset
（`brainstorm`、`attack`、`design`、`code-audit`）是参考实现 ——
复制其中一个作为起点。

---

## 1. Frontmatter schema

preset 的 YAML frontmatter 声明六个覆盖槽位：

```yaml
---
name: my-preset                    # must match file basename
description: One-paragraph description with "Use when …" triggers.
use-when: |
  - User says "X"
  - User wants to explore Y
  - Domain Z task that needs divergent exploration with adversarial bite

# === Slot 1: root type ===
# topic | artifact | code | design-prompt
root_kind: topic

# === Slot 2: what the engine calls each node ===
# A single word; appears in tree.md and the final report.
subject_label: idea

# === Slot 3: verdict vocabulary (4-tuple, all four roles required) ===
verdict_enum:
  advances: PROMISING       # nodes with this verdict trigger another §3 round
  kept:     MARGINAL        # nodes kept in tree but not re-expanded
  pruned:   DEAD-END        # nodes pruned (kept for reference)
  blocked:  NEEDS-MORE-INFO # incomplete; must be driven to one of the above

# === Slot 4: which verdict counts toward §6.2 convergence ratio ===
# Typically "advances" — engine checks: (last 2 rounds' advances / total) < --min-novelty-ratio
convergence_metric: advances   # must be one of the 4 verdict_enum roles above (verbatim)

# === Slot 5: scoring dimensions (exactly 5; each 0–3) ===
# Inline flow-map entries (shown) and standard block-map list items
# (`- key: S` + indented `name:` / `desc:` lines) both parse.
score_dims:
  - {key: S, name: scientific-value,  desc: "Magnitude of contribution if successful"}
  - {key: N, name: novelty,           desc: "Difference from existing work"}
  - {key: F, name: feasibility,       desc: "Probability of completion within user resources"}
  - {key: K, name: falsifiability,    desc: "Clarity of experimental / computational test"}
  - {key: B, name: branch-potential,  desc: "Number of sub-directions opened on success"}

# === Slot 6: node 12-field schema (exactly 12 entries) ===
node_schema:
  - idea_statement          # field 1: subject (≤ 3 sentences)
  - parent_framing          # field 2: §3.A / §3.B / ... / §3.L
  - derivation              # field 3: full math / mechanism / evidence chain
  - assumptions             # field 4: ≥ 3 explicit assumptions
  - predictions             # field 5: ≥ 1 quantitative falsifiable prediction
  - falsifiability          # field 6: what would refute this
  - novelty_vs_literature   # field 7: comparison to ≥ 3 real refs with DOI/arXiv
  - feasibility             # field 8: data / compute / time / skill
  - risks                   # field 9: ≥ 3 risks, tagged technical/scientific/resource
  - branch_potential        # field 10: ≥ 2 sub-directions if this succeeds
  - external_resources      # field 11: repos / plugins / datasets found via §3.X
  - verdict_provisional     # field 12: verdict label from verdict_enum

# === Output artifact file names ===
output_artifacts:
  primary: shortlist.md     # main deliverable; sorted by score; advances-verdict nodes
  secondary:
    pending: pending.md     # blocked nodes (should be empty at converged time)
    marginal: marginal.md   # kept-verdict nodes

# === Optional: per-framing examples and custom baseline glossary paths ===
glossary_paths:
  - FACTS.md
  - glossary.md
  - CLAUDE.md
---
```

### 必需键 vs 可选键

**必需**（缺失则引擎在 preset 加载时报错）：

- `name`、`description`
- `root_kind`、`subject_label`
- `verdict_enum`（含全部 4 个角色：`advances` / `kept` / `pruned` / `blocked`）
- `convergence_metric`
- `score_dims`（恰好 5 个）
- `node_schema`（恰好 12 个）
- `output_artifacts.primary`

**可选**：

- `use-when`（推荐，便于 slash 命令的可发现性）
- `output_artifacts.secondary.*`
- `glossary_paths`（未设置时默认为 `FACTS.md` / `glossary.md` /
  `CLAUDE.md`）
- 任何 preset 特定的扩展字段（引擎忽略未知的顶层键）

### 引擎强制的合规

`tools/validate_plugin.py` 会拒绝以下情形的 preset：

- `node_schema.length != 12`
- `score_dims.length != 5`
- `verdict_enum` 缺少 4 个必需角色中的任意一个
- 引用了一个不属于 `verdict_enum` 键的 `convergence_metric`
- 有一个未知的 `root_kind`
- `name` 或 `description` 为空
- 文件基名与 `name:` 不匹配

CI 在每次推送时运行验证器；损坏的 preset 会阻止合并。

### 1.1 语言边界

一个自定义 preset 可以用任何语言描述它的基线配方、framing 风味、
反模式、引用与示例。它的 schema 保持为引擎和验证器所消费的英文机器
骨架。以下保持英文、不要翻译：

- frontmatter 键与 `root_kind` 值；
- `verdict_enum` 角色键**及其标签**；
- `convergence_metric`、`score_dims[].key` 与 `score_dims[].name`；
- 每个 `node_schema` 字段名；
- `output_artifacts` 键与文件名；
- framing ID、状态/标记 token、路径、代码、公式与 API 标识符。

自由格式的值，例如 `description`、`use-when`、`score_dims[].desc`、
preset 正文，以及所引或所摘的源材料，可以使用任何语言。它们不会覆盖
本次运行的 `output_language`：生成的节点散文与报告叙述仍遵循
`--lang`，而引文保持逐字，并在其语言与输出语言不同时附加本地化解释。
若一个 preset 翻译或别名化了一个承重的 schema 标识符、而不是使用规范
英文 token，引擎会拒绝它。

---

## 2. preset 正文里放什么

frontmatter 声明词汇；正文声明*配方* —— 尤其是 §2 基线。正文由引擎
按下面的顺序解析。

### §2 基线配方（必需）

告诉引擎去 Read / Grep / WebFetch 什么，来构建根节点。要具体说明
文件类型、命令行调用，以及在哪里找到领域约定。

`code-audit` 的示例：

```markdown
## §2 Baseline (code-audit recipe)

For each `<root>` (file or directory path):

1. **Full Read.** If a file: `Read` the whole file. If a directory:
   `Glob <dir>/**/*.py` (or relevant extension), then `Read` every
   file ≤ 500 lines; spill larger ones via `Read --offset/--limit`.
2. **Test suite / fixtures.** `Glob tests/**/*.py` near the target;
   `Read` the most relevant ≤ 5 test files.
3. **Recent change context.** `Bash git log --oneline --follow
   <target>` for the last 20 commits.
4. **Project conventions.** `Read CLAUDE.md` (if present) and
   `Read .github/CODEOWNERS` (if present) to learn who-owns-what.
5. **Dependency surface.** `Grep "import " <target>` to enumerate
   external-dependency call sites that may need verification.

**Root node fields (5):**

- `target_summary`: 1 sentence describing what the target does.
- `entry_points`: list of public functions/methods/HTTP routes /
  CLI commands.
- `inputs_from_caller`: parameter types, validation present/absent.
- `external_dependencies`: libraries, services, files, env vars.
- `threat_surface`: list (auth bypass / injection / data leak /
  DoS / etc.) with rationale.
```

### §3.A–§3.L 风味（可选但推荐）

[`framings.md`](framings.md) 中每个 framing 都有一节"Per-preset
flavor"。如果你的 preset 足够新颖、以致随发布的风味不能直接套用，
请提供你自己的 —— 引擎会把它们用作该 preset 下节点的 framing 提示。

示例：

```markdown
## §3.D — Adversarial / red team (security-audit flavor)

Adopt a real adversary's perspective at each of:
- unauthenticated outsider (network attacker)
- authenticated low-privilege user (insider)
- authenticated high-privilege user gone rogue
- supply-chain attacker (malicious dependency)
- compromised CI / build pipeline

For each, ask: "what's the highest-impact thing I could do with
the access this category has, leveraging anything in the audited
code?"
```

### preset 特定的反模式（可选）

添加你的 preset 特有的反模式：

```markdown
## Preset anti-patterns (code-audit-specific, in addition to ENGINE.md §9)

- ❌ "Defense in depth" used as `mitigation_present` — must be a *specific*
  mitigation at a *specific* file:line.
- ❌ "Insufficient input validation" as a critique — must specify
  *which* input, *what* validation is missing, and *which* attack the
  missing validation enables.
- ❌ Reporting a finding without `proposed_fix` and without a runnable
  PoC (or a clear path to one) — downgrade to MARGINAL.
```

---

## 3. 槽位语义详解

### `root_kind`

| 值 | 行为 |
|---|---|
| `topic` | `<root>` 是一个字符串；逐字用作根的主题。可以为空（preset 可尝试推断）。 |
| `artifact` | `<root>` 是一个文件路径；引擎在 §2.1 之前 `Read` 整个文件。文件缺失 / 不可读则报错。 |
| `code` | 与 `artifact` 相同，但附加约定：文件扩展名暗示语言，用于 §3.G 替换与 §3.E 约束变化。目录输入 → 递归 Glob+Read。 |
| `design-prompt` | `<root>` 可以是字符串，也可以是文件路径。若是文件，将其作为结构化的 design-prompt 读取（期望有 goals / constraints / context 小节）。 |

### `subject_label`

单个名词，出现在 `tree.md`、REPORT.md 以及最终报告的判定计数中。
挑一个在"the 14 [subject_label]s produced by this run"里读起来自然的
词。示例：`idea` / `critique` / `option` / `finding` / `direction` /
`risk`。

### `verdict_enum` 角色

| 角色 | 语义 | 常见标签 |
|---|---|---|
| `advances` | 在此节点上递归进入又一轮 §3。计入 §6.2 收敛比（除非 `convergence_metric` 覆盖）。 | PROMISING / CONFIRMED / RECOMMENDED |
| `kept` | 留在树中，不重新展开。常为"有趣但现在不可行动"。 | MARGINAL / VIABLE / SECONDARY |
| `pruned` | 不重新展开；保留推导以供参考并防止重新生成。对 `attack` 风格的 preset，这是 REFUTED（有价值的正面记录）。 | DEAD-END / REFUTED / NOT-RECOMMENDED |
| `blocked` | 禁止状态；必须在 §6 收敛之前被推进到其他三者之一。 | NEEDS-MORE-INFO / INCOMPLETE_FORBIDDEN |

### `convergence_metric`

哪种判定的"比率跌破 `--min-novelty-ratio`"会触发 §6.2。**它必须是四个
`verdict_enum` 角色键之一**（`advances` / `kept` / `pruned` /
`blocked`），逐字书写 —— 验证器（`tools/validate_plugin.py`）会拒绝
其他任何东西（不允许 `novelty_ratio` / `confirmed_ratio` 之类的别名）。
对几乎每个 preset，这都是 `advances`："我仍在找到值得展开的新节点"。
领域读法（brainstorm 的 novelty、attack 的 confirmed、design 的
recommended）来自你在 `verdict_enum` 里映射到 `advances` 角色上的
*标签*，而不是来自重命名这个 metric。只有当你的 preset 确实收敛于
一个不同的信号时（罕见），才选择非 `advances` 的角色。

### `score_dims`

每个维度是 `{key, name, desc}`。`key` 是 1–3 个字母，用于 score 报告
（例如 `S=3 N=2 F=3 K=2 B=1 → total=11`）。`name` 是人类可读的。`desc`
是评分标准 —— 0 意味着什么，3 意味着什么。让维度保持正交；如果两个
维度在实践中相关性 > 0.7，它们就没有拉动独立权重。

### `node_schema`

恰好 12 个条目。把每个条目大致对应到 [`ENGINE.md`](ENGINE.md) §4 里的
某个普适槽位类别 —— 槽 1 是主题陈述，槽 2 是父 framing，如此类推。
你可以在名称上有所偏离，但引擎期望有 12 个字段覆盖那些普适类别。对于
根本不同的 schema（例如你需要 14 个字段），请提交一个 issue。

### `output_artifacts`

写入 `<out>/` 的文件名。`primary` 是主产物。`secondary` 是一个映射
（通常键名以用户可能想单独浏览的判定命名，例如 `pending`、
`marginal`、`refuted`）。

---

## 4. 分发你的 preset

两个选择：

1. **本地文件。** 存在任意位置；用 `--preset /path/to/my-preset.md`
   调用。无需改动插件。
2. **随本插件发布。** 添加 `presets/my-preset.md`，可选地再添加
   `commands/my-preset.md`（15 行的 slash 命令封装），提交一个 PR。
   CI 会验证 frontmatter / schema 合规。

关于命令封装，见随发布的 `commands/*.md` 里那个 4 行的模式。

---

## 5. 合规审计清单

在提交一个 preset 之前：

- [ ] Frontmatter 有全部必需键（见 §1）。
- [ ] `node_schema` 长度 = 12。
- [ ] `score_dims` 长度 = 5；每个都有 `key`、`name`、`desc`。
- [ ] `verdict_enum` 有全部 4 个角色（`advances` / `kept` /
      `pruned` / `blocked`）。
- [ ] `convergence_metric` 匹配 `verdict_enum` 键之一（逐字，无别名）。
- [ ] §1.1 中列出的机器标识符保持为规范英文 token；自由格式散文可用
      任何语言。
- [ ] preset 正文的 §2 基线没有 "TBD" / "TODO" 占位符。
- [ ] preset 正文的 framing 风味（若提供）不与
      [`framings.md`](framings.md) 的普适语义相矛盾。
- [ ] `python tools/validate_plugin.py` 在本地通过。
- [ ] （可选但鼓励）`examples/` 下存在一个示例运行，带 `tree.md` /
      `tree.json` / 主输出 —— 在一个玩具级根上演示该 preset。

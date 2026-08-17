# 撰写一个 cc-tree preset

> 语言：中文。英文规范版：[`docs/presets.md`](presets.md)。如有歧义，以英文版为准。
<!-- i18n-source-sha256: 667add2206e38a48243b332524493c88bc6791eb55905b891b8a5304d1a02a9d -->

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

# === Slot 4: which verdict counts toward the §6.1 convergence ratio ===
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

违反以下任意一条的 preset 都会被 `tools/validate_plugin.py` 拒绝。
（这里不写条数：每加一条规则都必须重新对照 `validate_preset_schema`
把清单读一遍，而一句过期的"强制执行八条规则"正是本仓库当作缺陷来处理的
那种漂移。）

1. 上面清单里的任一必需键缺失或为空（这涵盖 `subject_label` 与
   `output_artifacts`，不只是那几个显眼的键）。
2. 文件基名与 `name:` 不匹配。
3. 任何标量字段 —— `description`、`subject_label`、某个判定标签、
   `convergence_metric`、某个产物文件名 —— 实际上不是非空字符串。
   本该是标量的位置上出现嵌套映射会被拒绝，而不是被强制转换。
4. 未知的 `root_kind`。
5. `verdict_enum` 不是恰好含 4 个必需角色的映射，或某个角色的标签为空，
   或两个角色共用同一个标签（重复会让每一份打印判定的报告产生歧义）。
6. `convergence_metric` 不是 `verdict_enum` 角色键之一。
7. `score_dims.length != 5`，或任一条目不是含非空 `key`、`name`、
   `desc` 的映射。
8. 某个 `score_dims` 的 `key` 不是 1–3 个字母，或两个维度共用同一个
   key —— 否则 `S=3 N=2 …` 这行五项评分就读不出来了。
9. `node_schema.length != 12`，或任一条目为空，或两个条目命名同一个字段
   （它们会成为每个节点那 12 个 JSON 键）。
10. `output_artifacts` 没有非空的 `primary`，或任何 `primary` /
    `secondary` 取值不是裸的 `*.md` 文件名 —— 每份产物都写在本次运行的
    `<out>/` 之下，所以路径分隔符或 `..` 会让 preset 写到目录之外去。

CI 在每次推送时运行验证器；损坏的 preset 会阻止合并。
`tools/tests/test_validate.py` 用负例逐条证明这些拒绝确实生效，
并且每个负例都钉住了预期的诊断信息。

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
| `advances` | 在此节点上递归进入又一轮 §3。计入 §6.1 条件 2 的收敛比（除非 `convergence_metric` 覆盖）。 | PROMISING / CONFIRMED / RECOMMENDED |
| `kept` | 留在树中，不重新展开。常为"有趣但现在不可行动"。 | MARGINAL / VIABLE / SECONDARY |
| `pruned` | 不重新展开；保留推导以供参考并防止重新生成。对 `attack` 风格的 preset，这是 REFUTED（有价值的正面记录）。 | DEAD-END / REFUTED / NOT-RECOMMENDED |
| `blocked` | 禁止状态；必须在 §6 收敛之前被推进到其他三者之一。 | NEEDS-MORE-INFO / INCOMPLETE_FORBIDDEN |

### `convergence_metric`

哪种判定的"比率跌破 `--min-novelty-ratio`"满足 §6.1 条件 2。**它必须是四个
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
2. **随本插件发布。** 添加 `presets/my-preset.md` **以及**
   `commands/my-preset.md`（一层薄薄的 slash 命令封装），提交一个 PR。
   CI 会验证 frontmatter / schema 合规，而且这层封装不是可选的：
   发布一个没有同名命令的 preset 会让外壳配对检查失败。

关于命令封装，照抄随发布的 `commands/*.md` 的写法 ——
frontmatter 加几行正文。

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

# cc-tree ENGINE specification（引擎规范）

> 语言：中文。英文规范版：[`docs/ENGINE.md`](ENGINE.md)。如有歧义，以英文版为准。
<!-- i18n-source-sha256: 57d0d9436369a927b83a226019b17454eb60a0998ce8ad19f723f9fd9f3f7a1b -->

> 本文档是**引擎契约（engine contract）**。`/cc-tree:tree` 技能在会话开始时
> 读取本文件（连同当前激活的预设（preset）和 `framings.md`），并将每一节
> 都视为强制约束。预设提供*词汇表*（裁决（verdict）名称、节点（node）字段
> 名称、评分维度名称），但**不得**削弱下文的任何规则——它们只能扩展，不能
> 覆盖。

本引擎是一个递归式辐射树（radial-tree）生成器，以实质性收敛（convergence）
作为其主要终止判据。可以这样在脑海中想象：一棵从单一根（root）向外生长的
系统发生树（phylogenetic tree）：

- **root（中心）** = 用户提供的输入——一个主题（topic）、一个产物（artifact，
  文件/文档）、一个问题陈述，或一个设计提示（design prompt）。由预设的
  `root_kind` 字段决定是哪一种。
- **depth（同心环）** = 一个节点距离根有多少轮框架视角（framing）递归。
- **node（任意点）** = 一个*想法* / *批判（critique）* / *选项（option）* /
  *审计发现（audit-finding）*——具体由预设的 `subject_label` 称呼它们。每个
  节点都遵循同一个 12 字段 schema（§4）。
- **width（最外层弧）** = 最终交付的终端叶节点（leaf）数量。宽度由 §6 收敛
  决定，而非人为指定的上限。

**五个不可约的基本原语（irreducible primitives）**：

1. **§2 基线（baseline）** —— 根必须建立在真实、经过验证的输入之上（Read
   文件、Grep 符号、WebFetch 引用、术语锁定）。预设提供配方；引擎强制执行
   "无未经记录的字段"。
2. **§3 12 个框架视角（12 framings）** —— 每个节点、每一轮都要经受全部 12
   个框架视角 pass。每个 pass 至少产生 1 个子节点。跳过某个框架视角则该
   pass 作废。
3. **§4 12 字段推导（12-field derivation）** —— 每个子节点在计数之前，其全部
   12 个字段都必须填入非含糊、带证据的内容。含糊措辞和
   `defer/future-work/TODO` 之类的占位符会迫使节点进入
   `INCOMPLETE_FORBIDDEN`。
4. **§5 评分 → 裁决 → 递归决策** —— 把 5 个评分维度的分数相加（每项 0–3，
   满分 15）；映射到预设的 verdict_enum；只有 `advances` 裁决才会触发对该
   节点再做一轮 §3。
5. **§6 收敛** —— 6 个同时成立的条件，全部满足才能进入 `CONVERGED` 状态。
   否则就通过用户指定的上限终止（所有叶节点仍然完整），或继续运行。

其余各节（§7 输出、§8 工具、§9 反模式（anti-pattern））讲的是*如何*执行和
报告上述五项。

---

## 0. Data model and growth criterion（数据模型与生长判据）

### 0.1 Tree growth rule（树生长规则）

一个节点在以下情形下生出子节点：
- §3 已在它上面运行过（全部 12 个框架视角）—— 产生 ≥ 12 个候选子节点
  （每个框架视角一个），外加框架视角提示本身额外生成的任何子节点；
- 并且至少有一个子节点通过 §4 + §5 且 `verdict = advances`。

一个节点是**终端叶节点**（计入最终 `width`），当它的裁决使其成为终端：
- `kept` 或 `pruned` —— 按决策即为终端（§5.3）：该节点留在树中且永不
  重新展开，因此它在被评分的那一刻就是一个树梢。被剪掉的树梢（例如
  brainstorm 的 `DEAD-END`）同样计数——它们被完整推导过（§4、§F4），
  在次级交付物中交付，并且 §7.4 的 `leaf_count` / 裁决分布把它们每一个
  都计入；
- `advances` —— 只有在 §3 已对它重新运行、且没有任何框架视角 pass 产生
  能通过 §4 + §5 的子节点之后，才是终端。§6 条件 4 要求在 `CONVERGED`
  之前穷尽每一个 `advances` 叶节点，所以一棵完成的树不存在未展开的
  `advances` 树梢。

被标记为 `INCOMPLETE_FORBIDDEN` 的节点**永远**不计为终端叶节点——它必须
被驱动到完整状态（每个字段非空、非含糊、无 defer 措辞）后，递归才能结束。

### 0.2 Identity, persistence, and incremental write（标识、持久化与增量写入）

每个节点都获得一个稳定的 `id`，形如 `<depth>.<width>.<framing>` 或类似形式
（由预设选择；引擎保证在一个 tree-out 目录内唯一）。节点在**其 §4 字段填好
的那一刻**就被写入磁盘——而不是在最后批量写入。这使得从中断处重启变得
轻而易举：用同一个 `--out <dir>` 重新调用，引擎就从磁盘上已有的最高 id
节点处恢复。

`tree.json` 是真相源（source of truth）；`tree.md` 是人类视图；两者都按节点
原子地追加写入。

---

## 0.5 Top-level forbidden patterns (violation → round invalid)（顶层禁令模式，违反 → 本轮作废）

这八个模式普遍地降低探索质量。它们适用于每一个预设——预设可以添加更多，
但不能移除任何一个。

### F1. No memory-cited claims（不得凭记忆援引断言）

每一个外部断言（文件内容、API 签名、库特性、既有工作、数据集属性、版本号、
错误信息、定理表述）**都必须在同一轮内通过** `Read` / `Grep` / `Bash` /
`WebFetch` 验证。无法验证的断言必须标记为 `[NEEDS_VERIFICATION]` 并降级该
节点；它们**不得**被用作任何下游节点的前提。该标签是一个机器 token
（见 `docs/languages.json`）：必须写成带下划线的形式，绝不能拆成两个词，
这样 `--lang` 翻译与 §5.2 的裁决规则才能匹配到它。

这条禁令在**每一种输出语言中都是语义性的**，而不是一份逐字的英文/中文子串
白名单。任何用不确定、凭记忆、凭惯例或无根据的概率来替代已验证证据的等价
措辞，在 `assumptions` 字段之外都被禁止（`assumptions` 字段正是把猜测*明确*
记录为猜测的地方）。示例包括：

> 应该 / 大概 / 我相信 / 通常 / 可能 / 也许 / 或许 / probably / maybe /
> I recall / I believe / typically / usually / in my experience

### F2. No pseudo-divergence（不得伪发散）

两个仅在同义词替换或语序调整上不同的子分支是**同一个分支**。把它们合并，
保留得分较高的一侧；把另一侧标记为 `MERGED_INTO=<id>`。合并阈值是主题陈述
上的余弦相似度 ≥ 0.85，但人类判断可以覆盖——如果两个陈述描述的是同一个
底层机制，则无论相似度分数如何都要合并。

一个新分支必须**至少**提供以下之一：
- 一个不同的可检验预测（prediction）或可观测后果，
- 一条不同的证伪（falsification）/ 失效路径，
- 一份不同的资源画像（数据 / 算力 / 时间 / 人力）。

### F3. No derivation skipping（不得跳过推导）

"这个方向看起来有意思"不是裁决。每个节点都必须有完整的 §4 推导链（数学 /
机制 / 依赖追踪——由预设决定）。`derivation` 字段不能包含 `details
omitted`、`easy to show`、`obvious`、`略`、`自明` 或等价表述。

对于数值类断言，引擎**必须**通过 `Bash` 运行一次性的
`python (sympy/numpy)` 完整性检查（sanity check），并把输出粘贴进该字段。
检查失败或无法运行会把裁决从 CONFIRMED / PROMISING / RECOMMENDED 至多
下调一档。

### F4. No risk aversion (each framing pass must include 1 high-risk branch)（不得规避风险，每个框架视角 pass 必须包含 1 个高风险分支）

某些框架视角 pass（尤其是 §3.K 非对称回报）存在的目的就是强制探索
高风险 / 高回报分支。跳过或搁置这个高风险槽位（"太投机"、"超出范围"）会使
该 pass 作废。高风险分支即使最终落到 `DEAD-END`，也必须被**完整地**推导
（§4 12 字段）——价值在于推导本身，而非裁决。

### F5. No pseudo-convergence（不得伪收敛）

"我生不出新想法了"不是 §6 收敛。收敛有六个同时成立的条件（§6）；六个全部
必须满足。具体而言，引擎必须已经：
- 在根上对每一个 §3.A–§3.L 框架视角至少各运行过一次，
- 把每一个 `advances` 裁决的叶节点至少重新展开过一次，
- 产生了 ≥ 1 个被完整探索过的高风险分支（§3.K），
- 把每一个 `INCOMPLETE_FORBIDDEN` 节点驱动到了完整状态，
- 观察到 `convergence_metric` 比率在最近 2 轮内降到了
  `--min-novelty-ratio` 之下（默认 0.15）。

### F6. No user-interrupt decisions (full-auto contract)（不得中途打断用户征询，全自动契约）

一旦 `/cc-tree:tree` 以一个解析好的根和一个加载好的预设被调用，引擎就
运行至收敛（或触顶上限），其间不再进一步征询用户。歧义通过**选择信息密度
最高的分支**来解决并继续推进。仅在以下情况停止：
- 达到了某个 §F7 用户指定的上限**且**所有在途节点均已完整，
- 因为根无法解析而无法构建 §2 基线（报告
  `EARLY_STOP=root_unparseable`），或预设要求的根字段无法填满（报告
  `EARLY_STOP=root_underspecified`，见 §2.1），
- 一次被恢复的运行收到的显式语言标签与其持久化的 `output_language` 冲突
  （在产生下一个节点之前报告 `EARLY_STOP=language_mismatch`），
- 来自 cc-enforcer 或沙箱策略的工具 DENY 阻断了一次必要的读取（报告被
  阻断的内容；不得静默切换策略）。

唯一的征询例外是 §2.0 术语表 grill，它运行在**根节点存在之前**：一个未解决
的 MISSING 或 AMBIGUOUS 术语会被问一次，术语表 CONFLICT 则停下来等待裁定。
在那里敲定的术语此后不再重新讨论——从 §2.1 写下根节点的那一刻起，本条规则
无任何例外地生效。

### F7. Resource caps default to ∞; can only narrow via flags（资源上限默认为 ∞，只能通过 flag 收窄）

默认的 `--width / --depth / --rounds / --max-branches` 全都是 ∞ 或
`conv`。引擎**不得**在内部收窄它们。当用户设置了一个有限上限并且该上限被
触及时，引擎仍要把每一个在途节点驱动到完整的 §4 状态，然后才报告触顶
状态——可见的叶节点集合**永远**是完整的。

只有 `--width / --depth / --rounds` 是*可报告的*上限：它们各自有一个状态
token（§6.2）和一条 §6.1 条件 6 的检验。`--max-branches` 抬高的是每个节点的
上限，而它的下限已由 §3 固定在 12；它永远不会终止一次运行，所以不存在
`BRANCHES_CAP_REACHED`，§6.1、§6.2 与 §7.4 也都没有命名这样一个状态。

### F8. Hard ban on deferred / incomplete leaves（对 deferred / 不完整叶节点的硬性禁令）

这条禁令在**每一种输出语言中都是语义性的**。任何把工作推迟、省略、外包，
或把未解决的工作留作终端结果的措辞，都会强制 `INCOMPLETE_FORBIDDEN`；把一次
搁置翻译成别的语言并不能绕过此规则。以下是示例，而非一份穷尽的措辞白名单：

> defer / deferred / 待定 / 留后 / 待确认
> 因成本限制 / 因算力限制 / 因时间限制 / 时间不够 / 算力不够
> future work / 留作 future work / TODO / FIXME
> 暂不展开 / 略 / details omitted / 省略 / 暂略
> 应该 / 大概 / 我相信 / 通常 / 可能（in non-`assumptions` fields）
> NEEDS-MORE-INFO 永久挂起 / 无法判定 / 看作者意思 / 得问作者

如果该字段确实需要外部资源才能填写，引擎**必须**在同一轮内通过
`WebFetch` / `Read` / `Bash` / `WebSearch` 获取它们。如果获取失败，则该
节点通过 §3.E（约束变换）被改道到一个*能够*用现有资源填写的兄弟节点，而
原节点在完成之前保持 `INCOMPLETE_FORBIDDEN`。

这是引擎最大的单一行为杠杆；没有它，每一次探索都会退化成"10 个有希望的
方向；细节留作 future work"。

---

## 1. Invocation（调用）

```
/cc-tree:tree <root> --preset <name|path> [flags]
```

### 1.0 输出语言解析与 schema 边界（Output-language resolution and schema boundary）

在**预设加载与 §2 基线之前**解析本次运行的语言，其间不做任何中途征询：

1. 通过 `--lang <tag>` 传入的显式 BCP-47 式标签胜出（示例：`en`、`zh`、
   `zh-Hans`、`zh-Hant`、`fr-CA`）。标签按其请求的原样保留，只是校验时的
   匹配对大小写不敏感。
2. `--lang auto` 检测主调用/根内容的主导自然语言。混合、无法识别、纯路径
   以及纯代码的输入会确定性地回退到 `en`。
3. 如果一次全新运行省略了 `--lang`，则使用 `en`。

`zh` 是受维护的简体中文惯例。繁体中文不会从 `zh` 推断；请用 `zh-Hant`
显式请求。一个具体的 `output_language` 在一次运行内绝不改变。

在写入根节点之前，把以下英文元数据键同时持久化到 `tree.json` 和
`tree.md` 的运行头部：

- `language_request`：显式标签、`auto` 或 `omitted`；
- `output_language`：解析得到的具体标签；
- `language_source`：`explicit`、`auto-detected`、`default`、`resume` 或
  `legacy-default`。

**机器骨架（始终为英文，并在适用处逐字节稳定）：** 命令与 flag 名称；
frontmatter 与 JSON 键；`root_kind` 值；裁决角色键**及标签**；评分键/名称；
`node_schema` 字段名；框架视角 ID；状态/标签 token；输出文件名；路径；代码；
方程；以及 API 标识符。这些 token 绝不被翻译或起别名。

**本地化散文（`output_language`）：** 节点陈述、推导、证据解释、假设、预测、
风险、修复、警告、人类可读的报告标题/叙述，以及终端摘要。

**任意语言输入：** 根文本、产物、源代码注释、术语表、领域画像正文、自定义
预设的自由格式散文、引用，以及被引证据。逐字保留引文。当一段引文的语言与
`output_language` 不同时，保留原文引文并补充一段本地化解释；不要用译文替换
证据本身。

在产生任何新节点之前，恢复（resume）会针对持久化的元数据来解析：

- 省略 `--lang` 或 `--lang auto` 会复用记录下来的 `output_language` 并把
  `language_source` 设为 `resume`（不重新检测）；
- 与记录标签相等的显式标签正常恢复；
- 相互冲突的显式标签以 `EARLY_STOP=language_mismatch` 退出；
- 没有语言元数据的遗留输出被视为 `en`，`language_source=legacy-default`。

`tree-chain` 在 stage 1 之前施加同一套解析恰好一次，并把具体标签转发给每个
阶段和每个逐项子运行；见 [`chaining.md`](chaining.md)。每个框架视角子代理的
提示都会收到具体的 `output_language` 以及上面的机器/散文边界。

### 1.1 Root resolution（根解析）

`<root>` 按预设的 `root_kind` 来解释：

| `root_kind` | `<root>` 的解释 |
|---|---|
| `topic` | 一个字符串。逐字用作根节点的 "subject" 行。 |
| `artifact` | 一个文件路径（`.md`/`.tex`/等）。在构建根之前完整 Read 该文件。 |
| `code` | 一个文件或目录路径。完整 Read，或递归 Glob+Read。 |
| `design-prompt` | 一个字符串或 `.md` 文件。若为文件则完整 Read；按带有目标 / 约束 / 上下文的结构化提示处理。 |

如果 `<root>` 为空：
- 允许推断的预设（`brainstorm` 的 research 模式）可以从当前项目状态推导
  （Read `CLAUDE.md` / `README.md` / 最近的 `git log`）；
- 否则引擎发出 `EARLY_STOP=root_unparseable` 并退出。

### 1.2 Preset resolution（预设解析）

`--preset <name>` 解析为本插件安装目录下的 `presets/<name>.md`。
`--preset <path>` 解析为一个字面文件路径（绝对路径，或相对于调用者
CWD 的路径）。无论哪种方式，预设都在 §2 基线之前被完整 Read。

### 1.3 Flag table（flag 表）

`--lang <tag|auto>` 是一个通用 flag，默认值为 `en`；它完整的解析、持久化、
恢复与链式语义在 §1.0 中具有约束力。

（完整表格见 `skills/tree/SKILL.md`；此处适用相同的语义。引擎对未知 flag
必须报错，而不是静默忽略。预设及其 command wrapper 可以记录额外的预设
特定 flag——例如 `attack` 的 `--focus <section|claim|equation>`——由
当前激活预设或其 wrapper 记录在案的 flag 不算"未知"。）

---

## 2. §2 Baseline construction（基线构建）

预设提供配方；本节定义引擎的通用契约。

### 2.0 Glossary grill prelude (mandatory unless `--no-grill`)（术语 grill 预热，除非 `--no-grill` 否则强制执行）

> 借自 `mattpocock-skills:grill-with-docs`。建立在草率术语之上的根会产生
> 一千个叶节点，去解决一个用户根本没问的问题。

步骤：

1. **定位术语表来源。** Read 以下中第一个存在的：
   - `--glossary <path>`（如果显式提供）；
   - 预设的 `glossary_paths` 列表（预设 frontmatter）；
   - 项目根目录下的 `FACTS.md` / `glossary.md` / `CLAUDE.md`；
   - 如果都不存在，则标记 `[NEEDS_GLOSSARY]` 并继续（§6 收敛会添加一条
     警告）。

2. **分解根的名词。** 从 `<root>` 中提取名词短语。单个抽象词 → 跳过；
   带技术含义的多词名词短语 → 逐个 grill。

3. **逐词决策矩阵**（按 `grill-with-docs` 惯例，一次只问一个问题）：
   - **EXACT MATCH**（术语表中精确匹配）→ 静默采用术语表定义，记录到
     `<out>/glossary-anchors.md`。
   - **ALIAS**（别名）→ 静默替换为规范名称，把别名记录到
     `glossary-anchors.md`。
   - **MISSING**（缺失）→ 向用户提问一次，≤ 3 个选项 + 一个推荐答案。
   - **AMBIGUOUS**（歧义，≥ 2 个术语表条目匹配）→ 带具体 `file:line`
     指针提问一次。
   - **CONFLICT**（冲突，`<root>` 的用法与术语表矛盾）→ **停止**引擎；
     等待用户裁定（改根 vs 更新术语表）。不得静默推进。

4. **产出 `glossary-anchors.md`**，其中包含每一个被 grill 的术语 + 其
   选定定义 + `file:line` 证据。后续每一个引入新名词短语的 §3 框架视角
   都要追加到此文件。

`--no-grill` 跳过本步骤；根节点术语被标记为 `unverified`；§6 收敛会添加
一条警告 "no glossary grill performed; strong-convergence claim not
allowed"。

### 2.1 Root construction (preset-determined)（根构建，由预设决定）

遵循预设的基线配方，用预设指定的字段集合（通常 5–8 个）填充根节点。每个
字段需要：
- 一句话的事实陈述，并且
- 一个 `file:line` 引用，或 URL，或命令输出引用。

根中不允许出现含糊 / 未验证的条目——引擎会反复重跑基线步骤，直到根被
完全落地（grounded）。

如果在经过有据可查的努力之后根仍有空字段：
- 允许推断的预设（`brainstorm` research-mode）从最接近的可用项目状态推断
  出缺失字段，并将其标记为 `[INFERRED — verify with user]`；
- 其余每一个预设 —— 即除 `brainstorm` research-mode 之外的全部；
  当前发布的集合是 `attack`、`code-audit` 与 `design` —— 发出
  `EARLY_STOP=root_underspecified` 并退出。

根在任何 §3 pass 运行之前被写入 `<out>/tree.md` + `<out>/tree.json`。

### 2.2 Field profile (optional, `--field <name|path>`)（领域画像，可选）

**领域画像（field profile）**提供领域感知的审稿人加权，使引擎以该领域资深
从业者的方式去攻击/探索，而不仅仅以 LLM 通用训练分布的方式。它与预设
无关——任何预设都能受益。

解析方式（镜像 `--preset`）：
- `--field <name>` → 本插件安装目录下的 `field-profiles/<name>.md`。
  以 `_` 开头的文件（如 `_template.md`）是脚手架，不是可选择的领域——
  `--field _template` 解析为 `[FIELD_PROFILE_NOT_FOUND]`；
- `--field <path>` → 一个字面文件路径；
- 如果两者都无法解析到一个可读文件 → 发出一条**警告**
  （`[FIELD_PROFILE_NOT_FOUND]`）并继续。领域加权是一种增强，绝不是
  阻断项（与 `--no-grill` 同样的非阻断契约）。

当一个画像加载时，在 §2 基线期间完整 `Read` 它，并把它的四个列表带入
消费它们的框架视角 pass：
- **Reviewer concerns（审稿人关切）** → 让 §3.C（跨学科）和 §3.D
  （红队）优先朝所列关切倾斜。
- **Field consensuses（领域共识）** → 用所列共识及其已知的失效区间为
  §3.I（contrarian）播种（seed）。
- **Common failure modes（常见失效模式）** → 为 §3.J（失效驱动）候选
  播种。
- **Evidence bar（证据门槛）** → 把 §3.X / §4 的引用标准提高到该领域所
  认可的强证据水平。

领域画像**绝不**放松任何通用规则（§0.5）——它只是重新排序哪些分支被
优先探索。其撰写格式见
[`field-profiles/README.md`](../field-profiles/README.md)；
[`field-profiles/_template.md`](../field-profiles/_template.md) 是一个
领域中立的起点模板。

### 2.3 Seed-from (chaining substrate, `--seed-from <primary.md>`)（seed-from，链式基底）

`--seed-from <path>` 让本次运行从**上一次运行的主交付物**出发，而不是
（或除了）一个全新的根。这是跨预设链式调用（chaining）的通用基底
（[`chaining.md`](chaining.md)）。

- `<path>` 指向上一次运行的 `shortlist.md` / `options.md` /
  `confirmed.md`（或任何主题行列表）。
- 每个列出的条目作为一个 **depth-1 种子节点**进入新树，其
  `verdict_provisional` 被设为预设的 `advances` 标签，然后用完整的 §3
  pass 重新展开以寻找子节点。
- 种子节点**不**像新节点那样被重新验证——它们的内容被当作既定；价值在于
  在它们之下生长出来的子树（参见 `--from-prior` 反模式：不要把种子重新
  列为新发现）。
- `--seed-from` 与正常的 `<root>` 组合使用：根为本次运行定调，种子为
  depth-1 打底。

`--from-prior`（历史上由 `attack` / `code-audit` 预设使用）是
`--seed-from` 的**别名**，行为完全相同。

---

## 3. §3 framing pass (12 universal framings)（框架视角 pass，12 个通用框架视角）

> 完整细节 + 各预设示例见
> [`framings.md`](framings.md)。下面是每个框架视角的一段话摘要。每个节点
> 在它被展开的每一轮都运行**全部 12 个**。

### §3.A — First-principles（第一性原理）
列出该节点承重的假设。对每一个假设，问"剥掉这个假设之后，什么仍然为真？"
输出：≥ 1 个子节点，其主题是去掉假设之后的残余 / 最小断言。

### §3.B — Inversion（反演）
该节点论证 / 提出 X。探索 ¬X、其对偶、X 失效的边界。输出：≥ 1 个翻转极性
的子节点。

### §3.C — Cross-disciplinary（跨学科）
列出 ≥ 3 个出现同一结构性问题的外部领域（生物学 / 经济学 / CS / 数学 /
语言学 / …）。输出：≥ 1 个从另一领域移植工具的子节点，并记录其失效代价。
如果加载了 `--field` 画像（§2.2），在通用移植之前先处理其所列的
"reviewer concerns"。

### §3.D — Adversarial / red team（对抗 / 红队）
采取一个试图证伪的审稿人立场。列出 3 个最具杀伤力的反论点。输出：≥ 1 个
子节点，把最强的反论点转化为一个证伪实验（brainstorm/design），或一条
已确认或已驳倒的批判（attack/code-audit）。

### §3.E — Constraint variation（约束变换）
列出该节点的显式和隐式约束（数据、算力、时间、API、受众）。对每一个，问
"如果放松它会改变什么？"和"如果收紧它会改变什么？"。输出：≥ 2 个子节点
（一个放松，一个收紧）。

### §3.F — Scale extrapolation（尺度外推）
当前该节点在尺度 S 上运作。外推到 1000×、0.001×，以及一个领域边界
（普朗克 / 宇宙学 / 单粒子，或预设领域的类比边界）。输出：≥ 1 个子节点，
暴露某个特定区间的失效或机会。

### §3.G — Substitution（替换）
替换该节点结构的每个主要组件（数据集、算法、目标指标、受众、依赖），并
观察变化。输出：≥ 1 个子节点，其中某一处替换产生了一个非平凡的新方向。

### §3.H — Office-hours 6Q（办公室时间 6 问）
一次 YC 式的六问拷问：
1. 需求现实：具体谁会受益，有多少人？
2. 现状：他们今天是怎么应付的？
3. 锐化：最窄的那一片"必须、现在、为此"是什么？
4. 最小楔子：验证整个方向的最小实验是什么？
5. 既有工作：谁已经在做了？
6. 未来契合：这件事 5 年后还重要吗？

输出：≥ 1 个子节点，它要么通过全部 6 个问题，要么明确说明它在哪里失败。

### §3.I — Contrarian（逆共识）
识别该节点隐含依赖的 ≥ 3 个主流共识。对每一个，问"在什么区间下这个共识
可能是错的？"输出：≥ 1 个子节点，把某一个这样的共识作为真正的研究 /
批判 / 设计问题来攻击。当加载了 `--field` 画像（§2.2）时，从它的
"field consensuses" 列表及其已知失效区间为本 pass 播种。

### §3.J — Failure-driven（失效驱动）
列出 ≥ 3 个具体的*当前*失效（不是"可以更好"，而是具体可复现的问题——
`file:line`、Fig. N、命令输出不匹配）。对每一个，问"这个失效本身是不是
我们应该提出的一个问题？"输出：≥ 1 个把某个失效重新框定为新节点的子节点。

### §3.K — High-risk asymmetric payoff（高风险非对称回报）
强制产生 ≥ 3 个候选分支，它们的期望值由一个小概率的范式级成功所主导。
挑出最具体的那个并完整推导。输出：≥ 1 个子节点。引擎**不得**跳过这个
框架视角（F4）。

### §3.L — Meta (LLM blind-spot self-audit)（元层：LLM 盲点自审）
自审，七问：
1. 我所有的分支是不是都来自训练分布里高频的框架视角？
2. 我有没有把"我能写出来的东西"和"实际上重要的东西"混为一谈？
3. 什么对人类专家很重要、但在 LLM 训练数据里很罕见？
4. 我的行文是不是"太顺滑"了？真实的研究 / 设计 / 批判是粗糙的、矛盾的、
   片面的。
5. 我是不是在回避数学密集型的分支？补一个。
6. 我是不是在回避实验密集 / 代码密集型的分支？补一个。
7. 树里最古怪的那个分支真的够古怪吗？不够就再强制加一个。

输出：≥ 1 个来自该自审盲点清单的子节点。

### §3.X — External resource cross-check (per node, unless `--no-online`)（外部资源交叉核对，逐节点，除非 `--no-online`）

对每个节点，在 §3.A–§3.L 之外，再运行一次外部交叉核对。
**查询集由预设决定**——逐预设的风味见
[`framings.md` §3.X](framings.md)。简而言之：brainstorm/design 寻找既有
工作 + 可调用的工具；attack 寻找已发表的批判 / 勘误 / 被歪曲的引用；
code-audit 寻找 CVE / 安全公告 / 仓库中别处的同一模式。

通用步骤：
1. `WebSearch` 预设相应的查询集（基线 `<subject> arxiv` /
   `<subject> github` + 预设的专用查询）。
2. `WebFetch` 每个有希望的 URL 以确认其实际内容——一个 `WebSearch`
   片段本身永远不够（§F1）。
3. 把发现记录到该节点的外部字段——字段名由当前预设的 `node_schema` 决定：
   brainstorm 用 `external_resources`，design 用 `external_dependencies`，
   attack 用 `external_check`，code-audit 用 `related_findings`。写进该预设
   自己的字段名，不要另造第 13 个字段。

`--no-online` 跳过 §3.X；节点被标记 `external_resources_unchecked=true`。

---

## 4. §4 per-node derivation (12-field schema)（逐节点推导，12 字段 schema）

每个节点——根以及每个子节点——都有一个 12 字段 schema。名称因预设而异
（例如 brainstorm 的 `idea_statement` vs attack 的 `critique_statement`），
但每个预设都必须恰好提供 12 个具名字段，引擎对每个字段强制执行非空 +
非含糊 + 无 defer。

通用字段类别：

| 槽位 | 通用用途 | 各预设示例 |
|---|---|---|
| 1 | 主题陈述（≤ 3 句） | `idea_statement` / `critique_statement` / `option_statement` / `finding_statement` |
| 2 | 父框架视角（§3.A–§3.L） | 始终为 `parent_framing` |
| 3 | 位置 / 目标 | attack 用 `artifact_position`；brainstorm 不适用 |
| 4 | 推导 / 证据 | `derivation` / `evidence` / `mechanism` / `repro_steps` |
| 5 | 假设（≥ 3） | 始终为 `assumptions` |
| 6 | 预测 / 后果 | `predictions` / `observable_consequences` |
| 7 | 应答 / 反防御 | `falsifiability`（brainstorm）/ `artifact_defense`（attack）/ `mitigation_present`（code-audit）/ `trade_offs`（design） |
| 8 | 与既有工作 / 现状的比较（预设可选） | `novelty_vs_literature`（brainstorm）/ `alternative_interpretations`（attack、code-audit）/ `prior_art`（design） |
| 9 | 成本 / 可修复性 / 可行性 | `feasibility`（brainstorm）/ `proposed_fix`（attack、code-audit）/ `implementation_cost`（design） |
| 10 | 风险 / 陷阱（预设可选） | brainstorm 用 `risks`，design 用 `operational_risks`；attack 与 code-audit 把风险放进 `artifact_defense` / `threat_model_context` |
| 11 | 分支潜力（预设可选） | `branch_potential`（brainstorm）/ `sub_critique_potential`（attack）；design 与 code-audit 把这个槽位用在 `migration_path` / `threat_model_context` 上 |
| 12 | 临时裁决 | 始终为 `verdict_provisional` |
| — | §3.X 外部核查 | `external_resources`（brainstorm）/ `external_dependencies`（design）/ `external_check`（attack）/ `related_findings`（code-audit） |

**槽位**列是一个类别索引，不是 `node_schema` 中的位置。预设提供恰好 12 个
具名字段并可自由排序；只有类别是通用的，而标注为*预设可选*的类别在预设把
该字段用于领域专属关注点时可以缺席。

最后一行刻意没有槽位编号。§3.X 要求每个预设都为它的外部交叉核查命名一个
字段，但预设是从同样的 12 个字段里挪出一个来放它，而不是加第 13 个 ——
所以它是一个必需的*类别*，占据预设腾得出来的那个槽位。上表中的每一个示例
都是某个已发布预设真正声明过的字段；一个类别的示例指向不存在的字段，
正是这张表以前发生漂移的方式。

适用于每个字段的严格要求：

1. **非空。** 空白字段强制 `INCOMPLETE_FORBIDDEN`。
2. **非含糊。** §F1 的禁用措辞（在 `assumptions` 之外）强制
   `INCOMPLETE_FORBIDDEN`。
3. **无 defer 措辞。** §F8 的禁用措辞强制 `INCOMPLETE_FORBIDDEN`。
4. **引用。** 任何关于外部状态的断言都必须就地携带 `file:line` / URL /
   命令输出证据。
5. **数值自检。** 任何数字、方程或常数都必须在同一轮内通过一次性的
   `python (sympy/numpy)` Bash 调用验证；检查失败会下调裁决。

长字段（derivation > 100 行，evidence > 100 行）溢出到 `nodes/<id>.md`，
主 `tree.md` 携带一个 `→ nodes/<id>.md` 指针。

---

## 5. §5 scoring, verdict, recursion decision（评分、裁决、递归决策）

### 5.1 Scoring（评分）

每个节点沿预设的 `score_dims` 获得 5 个分数。每个维度是 **0–3 的整数**，
没有半分。总和 `score = d1 + d2 + d3 + d4 + d5`，最大值为 15。

维度因预设而异；常见模式：

- brainstorm：S=scientific-value（科学价值），N=novelty（新颖性），
  F=feasibility（可行性），K=falsifiability（可证伪性），B=branch-potential（分支潜力）
- attack：S=severity（严重度），P=specificity（具体性），
  R=reproducibility（可复现性），F=fixability（可修复性），B=sub-critique-fan-out（子批判扇出）
- design：V=value（价值），R=reversibility（可逆性），C=cost（成本），
  F=fit-with-constraints（与约束的契合度），E=evidence-strength（证据强度）
- code-audit：S=severity（严重度），P=position-specificity（位置具体性），
  R=reproducibility（可复现性），F=fixability（可修复性），X=exploit-likelihood（可利用性）

### 5.2 Verdict mapping（裁决映射）

每个预设声明一个四元组 `verdict_enum = (advances, kept, pruned,
blocked)`。映射规则为：

- `score ≥ 11`（外加任何预设特定的额外关卡，例如 attack 的
  "未发现 artifact_defense"）→ `advances`
- `8 ≤ score ≤ 10` → `kept`（留在树中但不重新展开）
- `score ≤ 7` → `pruned`（置灰，推导保留以供参考）。标签取该预设映射到
  `pruned` 角色上的那个——对 `attack` 与 `code-audit` 是 REFUTED，
  而不是 brainstorm 的 DEAD-END。
- 任何字段被标记 `[NEEDS_VERIFICATION]` 且占主导 → `blocked`
  （= `INCOMPLETE_FORBIDDEN`；不能计入终端宽度）

四个裁决标签由预设提供：

| Preset | advances | kept | pruned | blocked |
|---|---|---|---|---|
| brainstorm | PROMISING | MARGINAL | DEAD-END | NEEDS-MORE-INFO |
| attack | CONFIRMED | MARGINAL | REFUTED | INCOMPLETE_FORBIDDEN |
| design | RECOMMENDED | VIABLE | NOT-RECOMMENDED | NEEDS-MORE-INFO |
| code-audit | CONFIRMED | MARGINAL | REFUTED | INCOMPLETE_FORBIDDEN |

注意 brainstorm 与 attack 之间的不对称：attack 的 `pruned` 是 `REFUTED`，
意味着*引擎发现产物已经能够防御该批判*——这是**有价值的信息**，该节点
作为一条正面记录留在树中。

### 5.3 Recursion decision（递归决策）

在 §4 + §5 之后：
- `advances` → 把该节点作为下一轮另一次 §3 pass 的根入队。
- `kept` → 留在树中，不重新展开。
- `pruned` → 留在树中（置灰），不重新展开。
- `blocked` → 引擎必须在宣布 §6 收敛之前把它驱动到其他三种之一；在此
  之前它阻断终止。

### 5.4 Sibling merging（兄弟节点合并）

在同一父节点的子节点之间：如果任意两个兄弟节点在其 `subject_statement`
（字段 1）上有 ≥ 0.85 的余弦相似度，外加重叠或相同的 `position/target`
（字段 3，在适用时），它们合并：
- 保留得分较高的一侧；
- 把另一侧标记为 `MERGED_INTO=<id>`；
- 被合并掉的节点在 `tree.md` 中仍然可见，但不再进一步展开。

人类判断可以覆盖余弦相似度——如果两个兄弟节点*讲的是同一个底层机制*，即使
评分 < 0.85，也要合并。

---

## 6. §6 convergence（收敛）

> "看起来做完了"不是收敛证据。下面六个条件必须**同时**为真，引擎才能宣布
> `CONVERGED`。

### 6.1 The six conditions（六个条件）

1. **所有节点完整。** 当前没有任何节点状态为 `INCOMPLETE_FORBIDDEN`。
   §F8 在此约束。
2. **收敛比率已下降。** 在最近 2 个展开轮里，
   `(裁决为 advances 的新节点) / (新节点总数) < --min-novelty-ratio`
   （默认 0.15）。
3. **全部 12 个框架视角已被运行。** §3.A 到 §3.L 在根上各触发了 ≥ 1 次。
4. **所有 `advances` 叶节点已被重新展开。** 每一个曾经持有 `advances`
   裁决的节点都被当作根做了 ≥ 1 次后续 §3 pass，且该 pass 没有再产生
   `advances` 子节点。
5. **§3.K 分支存在。** 树中至少存在一个被完整推导（§4 12 字段）、经过
   §5 评分的高风险分支（无论其最终裁决如何）。它不得是由 §F4 强制塞进去
   的占位符。
6. **用户指定的上限未触顶。** 如果 `--width / --depth / --rounds` 被设为
   有限值，没有一个被触及。如果有任何一个被触及，引擎转而报告
   `WIDTH_CAP_REACHED` / `DEPTH_CAP_REACHED` / `ROUNDS_EXHAUSTED`，并且
   所有可见叶节点仍然必须完整（§F7）。

### 6.2 Termination decision table（终止决策表）

每轮自上而下评估；第一个匹配的行胜出：

| 条件 | 报告的状态 | 要求 |
|---|---|---|
| 上述 6 个条件全部成立 | `CONVERGED` | — |
| `--width N` 上限触及 + 所有叶节点完整 | `WIDTH_CAP_REACHED` | 每个可见叶节点上 §4 + §5 均完整 |
| `--depth N` 上限触及 + 所有叶节点完整 | `DEPTH_CAP_REACHED` | 同上 |
| `--rounds N` 上限触及 + 所有叶节点完整 | `ROUNDS_EXHAUSTED` | 同上 |
| 任何上限触及但仍有 `INCOMPLETE_FORBIDDEN` 叶节点 | *（无状态——**引擎不得停止**）* | 先把这些叶节点补完，然后重新评估本表 |
| §2 基线中根无法解析 | `EARLY_STOP=root_unparseable` | 仅在 §3 开始前有效 |
| 预设要求的根字段无法填满（§2.1） | `EARLY_STOP=root_underspecified` | 仅在 §3 开始前有效；允许推断的预设改为标注 `[INFERRED — verify with user]` |
| 沙箱 / 工具 DENY 阻断必要读取 | `EARLY_STOP=tool_blocked` | 报告被阻断的内容 |

当 `CONVERGED` / `*_CAP_REACHED` / `ROUNDS_EXHAUSTED` 中任何一个达到时，
写出 §7 最终报告并退出。`EARLY_STOP` 退出时不写最终报告（没有完成任何
探索），但磁盘上的部分 `tree.md` 仍然保留。

"探索成本太高" / "用户可能等太久了" / "讲道理的人到这儿就会停"**都不是**
停止条件（§F7 + 引擎的设计意图）。如果用户想要短跑，他们传 `--width 20`
或类似的——引擎随后如实报告 `WIDTH_CAP_REACHED`，而不是 `CONVERGED`。

---

## 7. §7 output（输出）

### 7.1 Incremental write contract（增量写入契约）

引擎在**每个节点完成时**写入磁盘，而不是批量写入：

- `tree.md` 被追加（每个节点一条 ≤80 字符的大纲条目）。
- `tree.json` 被追加（每个节点一个完整的 12 字段对象）。
- 如果任何字段超过 100 行，`nodes/<id>.md` 被创建/替换。

如果引擎崩溃 / 被中断 / 上下文窗口填满，磁盘上的状态在最后一次节点写入处
保持一致。用同一个 `--out <dir>` 重新调用即可恢复。

### 7.2 Output directory layout（输出目录布局）

```
<out>/
├── tree.md             # outline of every node; primary human view
├── tree.json           # full data for every node; machine source of truth
├── glossary-anchors.md # §2.0 prelude output (if --no-grill wasn't set)
├── <primary>.md        # preset's "advances" deliverable
│                       #   brainstorm: shortlist.md
│                       #   attack:     confirmed.md
│                       #   design:     options.md (recommended)
│                       #   code-audit: findings.md
├── <secondary>.md*     # preset's marginal / pending / refuted lists
├── <per-item>.md*      # per-item detail files a preset's body declares
│                       #   design: option_<id>.md (mechanism + trade_offs);
│                       #   this is what a design→attack chain hands over
├── REPORT.md           # §7.4 final-report block (also echoed to stdout)
└── nodes/
    └── <id>.md         # long-field spillovers
```

`output_artifacts` frontmatter 只命名每次运行固定的那几份交付物，因为它的取值
必须是校验器能限制在 `<out>/` 之内的字面文件名。带 `<id>` 的逐项文件因此改在
预设正文里声明 —— 但它们同样属于输出契约，而且
[`chaining.md`](chaining.md) 正是依赖它们。

### 7.3 `tree.md` per-node format（`tree.md` 逐节点格式）

```markdown
### <id>  <subject_statement[:80]>
- **parent**: <parent_id> | **framing**: §3.X | **score**: d1=_ d2=_ d3=_ d4=_ d5=_ → total=_
- **verdict**: <advances|kept|pruned|blocked label>
- **<field-2>**: …
- **<field-3>**: …  (or `→ nodes/<id>.md` if long)
- **<field-4>**: …
- …
- **children**: [id1, id2, ...]
```

（确切的字段名来自预设的 `node_schema`。上面的模板展示了通用脚手架；引擎
会代入预设的标签。）

### 7.4 Final report（最终报告）

终止后发射到 stdout（并保存到 `<out>/REPORT.md`）：

```
## cc-tree report — <root summary> — preset=<name>

### Status
- termination: CONVERGED / WIDTH_CAP_REACHED / DEPTH_CAP_REACHED / ROUNDS_EXHAUSTED / EARLY_STOP=<reason>
- mode: <preset's mode label if applicable>
- tree: max_depth=D, leaf_count=W (= final width), total_nodes=N
- verdict distribution: advances=A, kept=K, pruned=P, blocked=0
  (if blocked > 0 → report is INVALID; engine returned to §4)
- rounds: R
- triggers: <which §6 conditions fired or which cap tripped>
- user caps: width=<N|∞>, depth=<N|∞>, rounds=<N|conv>

### Top deliverables (advances, sorted by score desc)
1. [id] <subject_statement> — score=…
   - <key field excerpts>
   - first concrete action / experiment / fix: …
2. ...

### Kept-but-not-expanded (kept verdict)
[list with score and one-line summary; useful for "consider later"]

### Pruned (pruned verdict, kept for reference)
[just IDs and one-line summary]

### §3.L meta self-audit
- Weirdest branch: <id> — <one-line>
- §3.K high-risk yield: <one-line>
- Blind spots the engine couldn't escape (honest declaration): <one-line>

### F8 completion self-audit
- All visible leaves are fully derived (no defer / future-work / TODO / NEEDS-MORE-INFO language anywhere): YES / NO
- If NO → report is INVALID; engine returned to §4

### Suggested next steps (1–3 only)
1. <action with file:line / URL evidence>
2. ...
```

---

## 8. Tool-usage projection（工具使用投影）

引擎按下面这个映射使用 Claude Code 的标准工具。预设**可以**用预设特定的
工具要求来扩展（例如 `code-audit` 围绕 `Grep` + AST 式审查添加要求），但
不能削弱这个通用映射。

| 引擎任务 | 必需工具 | 禁止的捷径 |
|---|---|---|
| §2 基线构建 | `Read` / `Glob` / `Grep` / `Bash(git log)` | "我记得项目状态" |
| §2.0 术语查找 | `Read`（完整读术语表文件） | "我猜这个术语的意思" |
| §3 框架视角 pass —— 文献核查 | `WebFetch`（arXiv abs / DOI / 规范页面） | 把 `WebSearch` 片段当作结论 |
| §3 框架视角 pass —— 代码 / 数据核查 | `Read`（完整文件）/ `Grep` / `Bash`（运行复现） | 只读 diff 或一个搜索命中 |
| §4 数值自检 | `Bash + python (sympy / numpy)` | "易于验证" / "一眼可知" |
| §4 artifact_defense / mitigation_present 核查（attack/code-audit） | `Grep` 横跨 ≥ 5 个主要章节 + 对每个命中 `Read` | 只检查相邻段落 |
| 宽度 ≥ 5 时的并行框架视角 pass | `Agent(Explore)` 或 `Agent(general-purpose)` 子代理 | 在墙钟时间要紧时仍然串行 |
| 增量树写入 | 在 `tree.md` + `tree.json` 上直接 `Write` / `Edit` | 攒到"运行结束时"再批量写 |

### 8.1 Sub-agent dispatch (MANDATORY when a node's expected fan-out ≥ 5)（子代理派发，当节点预期扇出 ≥ 5 时强制）

当一个节点在某一轮将产生 ≥ 5 个子节点时——**对根而言永远成立**（12 个
框架视角），对任何热点叶节点也成立——引擎**必须**把 §3 框架视角 pass 跨
子代理并行化，而不是串行运行它们。在那种扇出下的串行执行是一个缺陷，而非
风格选择（§9 反模式"串行运行 §3"）。在预期子节点少于 5 个时（深层、大多
偏边缘的叶节点）允许串行：框架视角本身廉价，真正的成本是其后的 §4 推导。

**派发协议：**

1. 为每个框架视角 pass 生成一个 `Agent(Explore)`（或
   `Agent(general-purpose)`）——或者每个 agent 批处理 2–3 个框架视角以
   保持在并发上限之内。每个子代理提示都是**自包含的**：
   - 该节点完整的 §4 字段（子代理本来看不到的上下文）；
   - 该框架视角 pass 的提示（来自 [`framings.md`](framings.md) 的
     §3.A–§3.L 正文）；
   - 该预设的逐框架视角风味示例；
   - 输出契约：返回 ≥ 1 个子节点，其字段 1（主题）、4（推导/证据）、
     5（假设）、6（预测）、7（应答）已草填，**外加它所依据的每一个
     `file:line` / URL**，以便主代理重新验证。
2. 主代理**合并**返回的子节点：跨子代理应用 §F2 / §5.4 去重（两个 agent
   常常浮现同一个分支），然后补完剩余的 §4 字段，并对幸存者运行 §5 评分。
3. 主代理在子节点计数之前**重新验证子代理返回的每一个引用**（`file:line`
   仍然说着 agent 所声称的内容；被 WebFetch 的 URL 仍然支持该论点）——
   cc-enforcer 规则 04 传递性地适用；子代理未经验证的断言不算证据。

一个返回不了任何可用东西（所有分支伪发散或不可验证）的子代理**不**成为
跳过那个框架视角的借口——主代理改为就地（inline）运行它。全部 12 个框架
视角仍然必须触发（§F4）。

---

## 9. Anti-patterns (full list)（反模式，完整清单）

除了 §0.5 的八个禁令模式之外：

- ❌ **"我生成了 10 个方向，每个一行。"** §4 12 字段未填 → 分支不是节点。
- ❌ **"我相信这项工作已经被做过 / 还没被做。"** 必须 `WebFetch` 确认；
  仅凭 `WebSearch` 片段不够。
- ❌ **"推导太长，见注释。"** 溢出到 `nodes/<id>.md`——每个字节都保存在
  磁盘上。
- ❌ **"看起来我们收敛了，最近这一轮很慢。"** §6 有六个条件；六个全验。
- ❌ **"高风险分支太投机了，跳过 §3.K。"** 违反 §F4 + §3.K；整个 pass
  作废。
- ❌ **"为了省上下文，我只展示高分分支。"** 树在磁盘上；上下文不限制
  输出。
- ❌ **"`WebSearch` 没返回任何东西 → 它是新颖的。"** 试 ≥ 3 个关键词
  组合；检查相邻字段；若预设领域有此必要则检查非英文来源。
- ❌ **"用户没要求并行，串行运行 §3。"** 在宽度 ≥ 5 时，子代理派发是
  性能上的必需，而非偏好。
- ❌ **"树太大显示不下，我裁剪一下。"** 用户要的是穷尽；裁剪违反
  `--width` / `--depth` 语义。
- ❌ **"跑了框架视角 A–D，够了。"** 下限是 12 个框架视角（§F4 +
  `--min-frameworks 12`）；低于此 pass 作废。
- ❌ **"留作 `NEEDS-MORE-INFO` 让用户决定。"** §F8 + §6.1 禁止。引擎必须
  把阻断节点驱动到三个终端裁决之一。
- ❌ **"成本太高，提前停止。"** §F7 + §F8 禁止。上限如实触顶；成本不是
  上限。
- ❌ **"用户只要批判，跳过 `proposed_fix`。"** `attack` 和 `code-audit`
  预设要求 `advances` 裁决的节点带 `proposed_fix`——没有修复，裁决下调到
  `kept`。
- ❌ **"被驳倒的批判是噪声，丢掉。"** `attack` / `code-audit` 预设把
  `refuted` 节点作为正面记录保留（产物处理过这个攻击角度）——对准备应答
  有用。
- ❌ **"把上一次 pass 已知的问题重新列一遍。"** 如果预设有
  `--from-prior <report>` flag（有些有），上一次的条目作为*种子节点*
  进入，而不是被重新验证的清单项。重点是扩展，不是重复。

---

## 10. Preset extension surface (what a preset author can override)（预设扩展面，预设作者能覆盖什么）

一个预设可以：
- 命名四个裁决（`verdict_enum`）；
- 命名 12 个节点字段（`node_schema`）；
- 命名 5 个评分维度（`score_dims`）；
- 选择哪个裁决计入 §6.1 条件 2 的比率（`convergence_metric`）；
- 选择 `root_kind`（topic / artifact / code / design-prompt）；
- 命名输出交付文件（`output_artifacts`）；
- 提供一个自定义的 §2 基线配方（在预设正文中）；
- 为 §3.A–§3.L 各提供预设特定的示例（在预设正文中）；
- 添加预设特定的反模式（在预设正文中）。

一个预设**不可以**：
- 移除任何 §0.5 禁令模式；
- 把 `--min-frameworks` 降到 12 以下；
- 削弱 §F8（defer / future-work / TODO 禁令）；
- 改变 §6 的六条件收敛测试；
- 替换 §5 的 "score ≥ 11 → advances" 映射（它可以在 11 之上添加额外
  关卡，但不能降低这个下限）。

如果一个预设的 frontmatter 声明的字段数 != 12，引擎在预设加载时报错。
如果一个预设的 `verdict_enum` 条目数 != 4，同样。校验器
（`tools/validate_plugin.py`）在 CI 时捕获这些。

---

## 11. Compliance audit checklist（合规审计清单）

一位维护者审计某个预设的引擎合规性时：

- [ ] frontmatter 含有全部必需的键（`name`、`description`、`root_kind`、
      `subject_label`、`verdict_enum`、`convergence_metric`、`score_dims`、
      `node_schema`、`output_artifacts`）；
- [ ] `node_schema` 恰好有 12 个条目；
- [ ] `verdict_enum` 恰好有 4 个条目，四个键齐全；
- [ ] `score_dims` 恰好有 5 个条目，每个都有 `key`、`name`、`desc`；
- [ ] `convergence_metric` 匹配 `verdict_enum` 的某个键（通常是
      `advances`）；
- [ ] 预设正文的 §2 基线配方说明了要 Read / Grep / WebFetch 什么——没有
      "TBD" 占位符；
- [ ] 预设正文的框架视角示例不与 §3 通用语义矛盾（例如一个预设声称
      §3.B "Inversion" 指的是不同于本文档所述的东西，则不合规）。

随附的 4 个预设是这些规则的参考实现。

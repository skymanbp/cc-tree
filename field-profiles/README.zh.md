# 领域画像（Field profiles）

> 语言：中文。英文规范版：[`field-profiles/README.md`](README.md)。如有歧义，以英文版为准。
<!-- i18n-source-sha256: 6773638efa197fa7fa3ed80164b77160085fa4d5d24a3af9ad66194b17a060cb -->

**领域画像（field profile）**是一个可选的 markdown 文件，它为
cc-tree 引擎提供领域感知的审稿人加权。它让 12 个 framing 以某一特定
领域资深从业者的方式去攻击与探索 —— 优先处理该领域惯常关心的问题、
共识与失败模式 —— 而不是只依赖模型泛化的训练分布。

领域画像是**与 preset 无关的**：同一份画像（比如你自己写的
`physics.md`）既能帮 `attack` 审一篇物理论文，也能帮 `brainstorm`
探索物理研究方向，还能帮 `code-audit` 审一段物理仿真代码。

插件内置了一份具体画像：[`physics.md`](physics.md)
（ApJ/MNRAS/PRD 审稿人加权，偏弱引力透镜/宇宙学口味）。对于其他任何
领域，请从 [`_template.md`](_template.md) 出发自己撰写（见下方"如何
撰写一份"）；一个无法解析的 `--field <name>` 会给出
`[FIELD_PROFILE_NOT_FOUND]` 警告并在无加权的情况下继续运行。

## 使用一份画像

```bash
# By name — resolves to field-profiles/<name>.md in this plugin
# (physics ships built-in; other names need authoring first)
/cc-tree:attack ./paper.tex --field physics

# By path — any file you control
/cc-tree:brainstorm "research directions" --field ./my-lab-profile.md
```

如果画像找不到，引擎会警告（`[FIELD_PROFILE_NOT_FOUND]`）并在无加权的
情况下继续 —— 画像是一种增强，绝非必需。

## 一份画像包含什么

四张简短、具体的清单（见 [`_template.md`](_template.md)）。下面列出的
必需小节标题保持为规范英文标识符，以便引擎和验证器能确定性地找到它们；
清单正文、描述、引用与所引证据可以使用任何语言。它们不会改变由
`--lang` 选定的运行 `output_language`。

| 小节（Section） | 馈入（Feeds） | 用途（Purpose） |
|---|---|---|
| Reviewer concerns | §3.C 跨学科、§3.D 红队 | 该领域审稿人最先攻击什么 |
| Field consensuses | §3.I 唱反调 | 该领域默认假设什么 + 它在哪里失效 |
| Common failure modes | §3.J 失败驱动 | 此处工作在实践中如何出错 |
| Evidence bar | §3.X 外部核查、§4 引用 | 什么算强证据、什么算弱证据 |

## 如何撰写一份

1. 把 [`_template.md`](_template.md) 复制到
   `field-profiles/<your-field>.md`（或任意位置，然后传入该路径）。
2. **把 `field:` 键改成新的文件基名**，并重写 `description:`。
   验证器要求 `field` 与文件名一致，所以保留 `field: _template` 的副本
   会被拒绝 —— 而让模板自身获得豁免的那个下划线，不会豁免你的文件。
3. 用**具体、可核查**的条目填满每张清单。"要严谨"不携带任何加权
   信号；"报告效应量并附 95% CI"才携带。
4. 保持简短 —— 那三张枚举式清单各 3–6 条。画像是重新排序优先级；
   它不替代 framing。

一份领域画像**不能**削弱任何普适引擎规则（`docs/ENGINE.md`
§0.5）。它只改变分支被探索的*顺序*并抬高证据门槛 —— 它绝不允许一处
含糊其辞、一个被搁置的叶子，或一条未经核实的引用。

> 以 `_` 开头的文件（如 `_template.md`）是脚手架，不是可选的领域。

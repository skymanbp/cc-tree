# cc-tree documentation

> 语言：中文。英文规范版：[`docs/README.md`](README.md)。如有歧义，以英文版为准。
<!-- i18n-source-sha256: 82919ee18c2c1ae19dd863c44751b0bc1bf4e78782914c90c985e27dbfc835c6 -->

这里收录了所有用于**规定、讲解、论证**这台引擎的文档。项目总览在上一层的
[`../README.md`](../README.md)；本页是其余文档的带注索引。

## Start here

| 文档 | 什么时候读它 |
|---|---|
| [`../README.md`](../README.md) | 你想要总览、安装命令和完整功能清单 |
| [`ENGINE.md`](ENGINE.md) | 你想要有约束力的契约：从 §0 数据模型一直到 §11 合规检查清单 |
| [`framings.md`](framings.md) | 你想要 12 个 framing 的完整提示词，以及每个 preset 的实例演示 |
| [`../examples/attack/README.md`](../examples/attack/README.md) | 你想看真实的输入、真实的产物，以及如何自己复现一遍 |

如果你只读一份，就读 `ENGINE.md`。技能文件
([`../skills/tree/SKILL.md`](../skills/tree/SKILL.md)) 只是一份七步导航，
一切以引擎规范为准；每个 preset 都只能在它之上扩展，谁也不能削弱它。

## Authoring

| 文档 | 什么时候读它 |
|---|---|
| [`presets.md`](presets.md) | 你要写一个 preset —— frontmatter schema、正文各节、合规规则 |
| [`../field-profiles/README.md`](../field-profiles/README.md) | 你要为 `--field` 写一个领域视角档案 |
| [`chaining.md`](chaining.md) | 你要把多个 preset 串成流水线，手工串或用 `tree-chain` |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | 你准备向本仓库提一个 pull request |

## Background

| 文档 | 什么时候读它 |
|---|---|
| [`EVALUATION.md`](EVALUATION.md) | 你想知道设计理据：为什么是一台引擎加四个 preset、为什么是 12 个 framing、为什么要下那些硬禁令，以及哪些替代方案被否掉了 |
| [`../CHANGELOG.md`](../CHANGELOG.md) | 你想要逐版本的历史，包括每一轮 debug 扫荡究竟查出了什么 |

## Machine-readable sources

| 文件 | 负责什么 |
|---|---|
| [`languages.json`](languages.json) | 双语文档清单：每一对英文/中文文档、每一个仅保留英文的例外及其理由、必需的运行时 flag，以及翻译永远不得本地化的固定机器 token |
| [`assets/`](assets/) | 生成出来的图。`cc-tree-radial-tree.svg` 由 [`../tools/gen_radial_tree.py`](../tools/gen_radial_tree.py) 生成，只能重新生成，绝不手工编辑 |

## Documentation conventions

不带后缀的 `X.md` 是规范英文版。`X.zh.md` 是持续维护的中文平行版，每一份都在
头部区块里记录了英文源（换行归一化后）的 SHA-256 摘要。因此，只要改动英文文档，
它的译文摘要就会失效，CI 会一直失败到中文一侧被复核并刷新摘要为止 —— 正是这套
机制让译文不会悄悄地还在描述上个月的行为。没有译文的文档必须在 `languages.json`
里连同理由一起声明，而不是默认放着不管。

形如 `§N`、`§N.M`、`§FN` 的章节指针是指向 `ENGINE.md`、技能文件或某个 preset 的
正文引用。它们是被校验的：每一个都必须解析到真实存在的标题，所以给章节重新编号
会直接让 CI 失败，而不是留下一堆悬空指针。

## Verifying a change

```bash
python tools/validate_plugin.py     # 7 check groups; what CI runs first
python tools/tests/test_validate.py # preset schema + frontmatter parser cases
python tools/tests/test_i18n.py     # bilingual contract cases
python tools/tests/test_checks.py   # every check group vs a synthetic repo
```

细节（包括如何刷新译文摘要）见
[`../CONTRIBUTING.md`](../CONTRIBUTING.md)。

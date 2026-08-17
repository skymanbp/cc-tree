# 示例 —— `attack` preset

> 语言：中文。英文规范版：[`examples/attack/README.md`](README.md)。如有歧义，以英文版为准。
<!-- i18n-source-sha256: 7da30884bb8344f94c612056438d02ba529e0bb85bb2cb42e1468559990b3509 -->

一个精简的**演示性**示例：把 `attack` preset 用在一个玩具级
artifact 上。

- [`sample-claim.md`](sample-claim.md) —— 被攻击的 artifact：一段
  五点论证，内含三个刻意埋下的缺陷（一处过度泛化的基准测试、一处
  自相矛盾的时效性声明，以及一个无视并发的"可上生产"结论）。
- [`expected-out/confirmed.md`](expected-out/confirmed.md) —— 主产物：
  三条 CONFIRMED 批评，每条都带有 `file:line` 位置、证据，以及一个
  具体的 `proposed_fix`。
- [`expected-out/tree.md`](expected-out/tree.md) —— 同样这三条批评，
  但以 `docs/ENGINE.md` §7.3 的节点格式呈现（根节点 + 3 个叶子）。

> ⚠️ `expected-out/` 下的文件是一次**真实受限运行被手工裁剪后的输出**
> （`--width 3 --depth 1 --no-online --no-grill`），削减到只剩根节点
> + CONFIRMED 叶子，用来说明输出格式。缺的那部分是被裁掉的，不是因为
> 加了上限：**任何**真实运行 —— 无论有没有上限 —— 都会额外写出
> `tree.json`、`marginal.md`、`refuted.md`、一份 `REPORT.md`，
> 以及每个节点完整的 12 字段推导，因为 `docs/ENGINE.md` §F7 要求
> 即使触顶上限，每一片可见叶子也必须是完整的。一次不受限的运行
> （`/cc-tree:attack ./sample-claim.md`）的区别在于它会探索得更远，
> 所以可能揭示出比这里展示的三条更多的批评。CI 会把这些
> 文件里每一处 `file:line` 引用与 `sample-claim.md` 做边界核对
> （`tools/validate_plugin.py` 交叉引用）。这些 fixture 是规范英文
> 快照；`--lang <tag|auto>` 可以本地化一次重新生成运行的叙述文字，
> 而机器键、判定标签、状态、文件名和引用仍保持英文。

## 真正重新生成它

```bash
/cc-tree:attack ./examples/attack/sample-claim.md --out ./attack-out/example/
```

输出落到仓库里已经被 gitignore 的 `attack-out/`，而不是挨着 fixture 放：
维护一份被忽略的输出目录名单，比维护两份更容易保持正确。然后把
`attack-out/example/confirmed.md` 与 `expected-out/confirmed.md` 对比：
上面那三个埋下的缺陷都应当作为 CONFIRMED 出现，且带有指向
`sample-claim.md` 的 `file:line` 位置。

# The 12 framings（12 个框架视角）

> 🌐 English (canonical): [framings.md](framings.md) · 本文是中文平行翻译，若有歧义以英文版为准。

本文档把 [`ENGINE.md`](ENGINE.md) 中的 §3.A–§3.L 展开为可操作的
prompt，并配有**按 preset 区分的示例**。引擎对每个节点、每一轮都会
运行全部 12 个框架视角，每个框架视角产出 ≥ 1 个子分支。跳过或弱化
任一框架视角即作废该轮。

下面每个框架视角都遵循相同的结构：
1. **一句话目的**（通用）。
2. **可操作 prompt**（通用——引擎在每个节点向自己提出的问题）。
3. **按 preset 区分的风味**（`brainstorm` / `attack` / `design` /
   `code-audit`）——在每种语境下子分支具体长什么样的实例。
4. **输出要求**（始终 ≥ 1 个子分支，并草填 §4 field-1；完整的 §4
   推导在 pass 完成后进行）。

---

## §3.A — First-principles（第一性原理）

**Purpose.** 逐条剥离节点承重的假设，并追问每次剥离后还有什么仍然
成立。

**Prompt.** 列出当前节点所依赖的每一条假设（若存在则载入 §4
`assumptions` 字段）。对每一条，在脑中移除它并追问：*"这条假设没有
了，还剩下什么在结构上仍然牢靠？"* 产出一个以残余 claim 为主题的
子分支。

**Per-preset flavor:**

- **brainstorm.** "如果我们放弃暗物质晕呈球形这一假设，次峰信号
  就成为三轴取向的函数——存在一条取决于观测者角度的新
  SNR_resolved 推导，值得探索。"
- **attack.** "论文的核心 claim 假设透镜互相关噪声是高斯的（§3, line
  412）。若放弃该假设，χ² 拟合优度退化为置换检验，所报告的 4.2σ
  变成 2.1σ。"
- **design.** "auth flow 假设单租户。放弃它，JWT 方案就需要按租户
  作用域的密钥轮换——多了两个配置旋钮，但让同一份代码可服务
  B2B。"
- **code-audit.** "[upload.py:42](#L42) 假设上传文件声明的 MIME-type
  与其内容相符。剥离该假设 → 在存储前加一次 magic-byte 嗅探，以防
  content-type-spoofing → polyglot 上传。"

**Output.** ≥ 1 个子分支，其主题为*移除假设后的 minimum-claim*，并在
field-5 `assumptions` 中明确写出被移除的假设。

---

## §3.B — Inversion (negation / dual / boundary-of-failure)（反演：否定 / 对偶 / 失效边界）

**Purpose.** 节点正在探索 / 断言 / 提议 X。去探索 ¬X、X 的对偶，或
X 失效的边界。

**Prompt.** 当前节点方向的反面是什么？它的对偶（在数学 / 范畴 / 系统
意义上）是什么？这个方法在哪里会机械性地崩溃？产出一个探索这些反面
之一的子分支。

**Per-preset flavor:**

- **brainstorm.** "我们一直在看*透镜*如何告诉我们暗物质的信息。
  对偶：暗物质亚结构如何以光度残差能在无显式透镜测量下检测到的
  方式*改变*透镜 PSF？"
- **attack.** "论文声称方法 M 优于基线 B。反演：B 在哪里优于 M？§5
  只展示高 SNR 区间的结果——那 z > 0.8、M 训练数据稀疏的区间呢？"
- **design.** "当前提议：自建 auth 服务。反演：完全外包 auth（如
  Auth0 / Clerk），只持有 user-mapping 层。成本的权衡方式不同。"
- **code-audit.** "[parser.py:88](#L88) 通过静默丢弃字节来处理畸形
  UTF-8。反演：大声抛错。权衡：堵住一个罕见的 upload-stuck bug，但
  会破坏任何混合编码的历史数据。"

**Output.** ≥ 1 个探索反面的子分支，明确陈述反演内容，并给出一个
显式与原方向作对比的 `falsifiability` / `artifact_defense`。

---

## §3.C — Cross-disciplinary（跨学科）

**Purpose.** 从节点本学科之外的领域借用工具、框架，或证据标准。

**Prompt.** 列出 ≥ 3 个出现*结构同构*问题的外部领域。对每个领域
追问：*"该领域的标准工具是什么，把它移植过来管用吗？"* 围绕最有
希望的移植产出一个子分支。

**Per-preset flavor:**

- **brainstorm.** "WGL 亚结构检测在结构上类似于 (1) 基因组 CNV 检测
  （对带噪 1D 信号上隆起的统计检测）、(2) 引力波事件检测（针对模板库
  的匹配滤波）、(3) 工业传感器流中的异常检测。来自 GW 的匹配滤波
  方法或许可以移植，配以从 N-body 模拟改编的模板。"
- **attack.** "一位 ML reviewer 会以*数据泄漏*攻击 §4 的评估方法：
  train/test split 按 halo ID 划分，却未考虑跨实现（realization）的
  相关性。一位计量经济学 reviewer 会以*内生性（endogeneity）*攻击
  同一节——模拟选择同时制约了 M 和测试指标。"
- **design.** "auth-service 设计与限流（rate-limiting）设计平行。标准
  限流器模式（token bucket + Redis cluster）暗示了一种类似的
  auth-token 模式（short-lived bucket + refresh ring），这是我们之前
  没考虑过的。"
- **code-audit.** "一位数据库工程师 reviewer 会攻击
  [migrations/0042.sql:15](#L15) 在建索引时缺少 `CONCURRENTLY`——在
  热表上长时间加锁的迁移。一位分布式系统 reviewer 会攻击同一行不
  幂等——迁移中途重启会留下部分状态。"

**Output.** ≥ 1 个移植外部领域方法的子分支，并在 `assumptions` 中
列出移植中可能被打破的不变量。

---

## §3.D — Adversarial / red team（对抗 / 红队）

**Purpose.** 采取一位主动试图反驳 / 攻破 / 破坏当前节点的 reviewer
（或攻击者）的立场，并产出最强的反驳论证。

**Prompt.** "对这个节点**最具杀伤力的 3 条**反驳论证是什么？每条都
必须具体（指向 file:line / 一个机制 / 一个具体的失效）——不要含糊
的『可能无法泛化』。" 把最强的反驳产出为一个子分支，重述为反驳
实验（brainstorm/design）或一个 confirmed-or-refuted 的 critique
（attack/code-audit）。

**Per-preset flavor:**

- **brainstorm.** "对『通过 shape-bias 残差检测亚结构』的最强反驳：
  残差信号可能完全由内禀对齐（intrinsic-alignment）污染解释，而非
  亚结构。测试设计：模拟两个 halo 含量相同但 IA 强度不同的宇宙；
  若所提方法混淆了二者，该方向死亡。"
- **attack.** "对论文核心 claim 的最强反驳：Fig. 5 表明方法在 z <
  0.5 有效，但测试集 z > 0.8 的结果未出现在正文中，只出现在补充
  材料里。这是一种选择性报告（selective-reporting）模式。"
- **design.** "对『自建 auth』的最强反驳：password-reset + 2FA +
  SAML 支持的维护成本约为 0.5 个工程师-年/年，而团队本已人手不足。
  反驳：估算未来 4 个季度 auth 维护的实际工时。"
- **code-audit.** "对『[upload.py:42](#L42) 是安全的』的最强反驳：
  magic-byte 嗅探只检查前 4 个字节。ZIP 炸弹有标准 magic bytes。
  反驳：试一下——10 分钟内就该是一个 CVE。"

**Output.** ≥ 1 个携带最强反驳的子分支，将反驳论证表述为一个可
证伪的测试，或一个带 `proposed_fix` 的具体 critique。

---

## §3.E — Constraint variation (relax / tighten)（约束变换：放松 / 收紧）

**Purpose.** 列出节点的显式与隐式约束，然后同时探索放松（打开了
什么？）和收紧（暴露出什么新结构？）。

**Prompt.** 枚举围绕当前节点的约束（数据可得性、计算预算、时间、
受众、API、对称性假设、监管……）。对每一条：(1) 放松它——什么变得
可能？(2) 收紧它——什么新需求出现？产出 ≥ 2 个子分支——一放松、
一收紧。

**Per-preset flavor:**

- **brainstorm.** "放松：去掉对 Σ_crit 的宇宙学先验约束 → 打开一条
  model-independent 的 SNR_resolved 路线。收紧：不仅假设 Λ-CDM 而是
  一个特定的 bispectrum 先验 → 暴露出 f_NL 与亚结构质量谱之间的一个
  新简并。"
- **attack.** "放松：论文的 S/N 判据要求 5σ。在 3σ 下，所报告检测的
  一半被剔除——剩下的样本长什么样？收紧：在 7σ 下结果增强但样本量
  减半——5σ 这个选择是不是事后（post-hoc）优化出来的？"
- **design.** "放松：去掉 99.9% 正常运行时间 SLO → 打开一个简单得多
  的单区域架构。收紧：99.99% SLO 需要多区域 active-active，而当前
  提议并不支持。"
- **code-audit.** "放松：支持 > 100MB 的文件 → 暴露出
  [upload.py:42](#L42) 在哈希前把整个文件载入内存。收紧：支持 <
  1KB 的文件 → 暴露出另一个 bug，streaming 路径完全跳过了 magic-byte
  嗅探。"

**Output.** ≥ 2 个子分支（一放松、一收紧），各自在 field-5
`assumptions` 中写出被改变的约束。

---

## §3.F — Scale extrapolation（尺度外推）

**Purpose.** 把节点的运行区间在任一方向推动若干数量级（并推入域
边界），以暴露区间特有的失效或机会。

**Prompt.** 节点在尺度 S 上运行（在任何自然的维度上——负载、信号
幅度、数据规模、红移、延迟预算、用户数……）。在 1000× S 会发生
什么？在 0.001× S 呢？在某个域边界（Planck 尺度 / 宇宙学尺度 /
单粒子 / 无界用户增长 / 0 用户情形）呢？为暴露出新物理 / 新行为的
那个外推产出 ≥ 1 个子分支。

**Per-preset flavor:**

- **brainstorm.** "亚结构检测当前针对 ~10⁸ M_sun。推到 10¹¹：
  太阳质量晕逼近星系团范围，即恒星引力透镜主导的区间。推到 10⁵：
  暖暗物质截断区间内的子晕——可能是一个 WDM 约束的角度。"
- **attack.** "方法在 z < 0.5 验证过。外推到 z > 2：光度 SNR 下降到
  §3 噪声模型失效的程度；论文声称没有外推，但 Fig. 7 的 z-演化面板
  隐含地做了外推。"
- **design.** "当前设计假设 10K 日活用户。外推到 10M：对 auth-service
  的同步 JWT 验证调用成为系统瓶颈。外推到 10（onboarding 期间）：
  缓存无关紧要；设计应转而优化首次请求延迟。"
- **code-audit.** "[upload.py:42](#L42) 在单用户负载下测过。外推到
  1000 并发上传：内存中的哈希计算触发 OOM。外推到大小为 0 的上传：
  边界情形未处理——空文件被存储时带着一个损坏的哈希。"

**Output.** ≥ 1 个聚焦于最具揭示性外推的子分支，并明确写出新区间。

---

## §3.G — Substitution（替换）

**Purpose.** 替换节点结构的某个主要组件（数据集、算法、目标指标、
依赖、受众）并观察发生的变化——既包括引擎从这次替换中学到了什么，
也包括替换打开了什么新的非平凡分支。

**Prompt.** 列出节点结构的主要组件（通常 4–8 项）。对每一项追问：
*"如果我把它换成最接近的合理替代品，节点的结论是否仍然成立，且该
替代品是否打开一个新分支？"*

**Per-preset flavor:**

- **brainstorm.** "把 Halofit 非线性功率谱替换为 HMcode → SNR_resolved
  估计是否改变？若改变，就有一个值得探索的 model-dependence 子节点。"
- **attack.** "论文用了 MICE-grand-challenge mocks。替换为
  EuclidEmulator2 mocks → 方法所引用的 bias 是否会变？若会，那个
  bias 估计就是 mock-dependent 的，论文的稳健性 claim 被削弱。"
- **design.** "把所提的 Postgres 后端替换为文档存储（如 Mongo）→
  关系查询变得别扭，但多租户 schema 变得更简单。值得拿出来的权衡。"
- **code-audit.** "把 [upload.py:42](#L42) 的 SHA-256 替换为 BLAKE3
  → 热路径上快 3 倍。把 bcrypt cost=10 的口令哈希替换为 Argon2id →
  符合现代 OWASP 推荐。"

**Output.** ≥ 1 个围绕最清晰地打开一个新结构方向的替换构建的子分支。

---

## §3.H — Office-hours 6Q（办公室时间 6 问）

**Purpose.** 对节点施加 YC 风格的 6 问拷打，聚焦于*需求真实性*与
*具体的窄度*。

**Prompt.** 用硬证据（而非空谈）回答每个问题。每个『没有好答案』
本身就是一个子分支——节点的暴露点。

1. **Demand reality（需求真实性）.** 具体地，谁受益，有多少人？
2. **Status quo（现状）.** 他们今天如何应对？
3. **Sharpening（锐化）.** 最窄的"must, now, for this"切片是什么？
4. **Minimum wedge（最小楔子）.** 能验证整体的最小实验是什么？
5. **Prior art（先有技术）.** 谁已经在做（`WebSearch` 强制）？
6. **Future-fit（面向未来）.** 这在 5 年后还重要吗？

产出 ≥ 1 个子分支，要么强有力地通过全部 6 问，要么明确记录一个
失败点。

**Per-preset flavor:**

- **brainstorm.** "Q1（需求）：亚结构检测惠及 WGL 理论家 +
  DM 粒子物理学家；全领域 ≤ 200 人。Q3（锐化）：『must』是约束
  DM 粒子质量——一条很窄的科学 claim。Q4（楔子）：单个 Subaru-HSC
  星系团在 4σ 的次峰检测就是楔子。"
- **attack.** "Q5（先有技术）：我们发现 Smith et al.（2023, arXiv
  2305.xxxxx）在 9 个月前用了本质相同的方法——论文没有引用他们。
  这是一条重大 critique。"
- **design.** "Q1（需求）：内部 admin 工具服务 12 名工程师，目前
  没有人要求 SSO。Q3（锐化）：『must』只是跨机器重启的 session
  存活——并非所提议的完整 SSO 范围。"
- **code-audit.** "Q6（面向未来）：[upload.py:42](#L42) 处理器位于
  一个我们将在 6 个月内弃用的服务里。bug 的严重性不变，但优先级
  变了——作为 context 浮现出来。"

**Output.** ≥ 1 个子分支，浮现出最可付诸行动的弱点或强点所对应的
那个问题。

---

## §3.I — Contrarian（逆共识）

**Purpose.** 浮现出节点对 ≥ 3 个领域主流共识的隐式依赖，并探索其中
某一个共识出错的区间。

**Prompt.** "该领域目前一致认同、而这个节点所依赖的 3 件事是什么？"
对每一件："在什么区间下这个共识可能是错的，节点在那里会发生什么？"
为最可能在某处出错的那个共识产出一个子分支。

**Per-preset flavor:**

- **brainstorm.** "共识 1：WGL 信号由 shape-noise 主导。该共识可能
  出错的区间：在非常大的尺度上，转而由宇宙方差（cosmic-variance）
  主导。分支：构建一个尺度相关的噪声模型并重新推导最优性界。"
- **attack.** "论文所依赖的共识：光度红移误差可由高斯卷积很好地
  建模。已知该共识出错的区间：SDSS 风格模板拟合在 z > 1.2 处的
  灾难性离群（catastrophic outliers）。论文的分析正处于那个区间；
  引用并攻击（cite-and-attack）。"
- **design.** "共识：『OAuth 是 B2B SSO 的标准。』该共识出错的区间：
  客户在 Active Directory 上，除 SAML 外什么都不接受。分支：一个
  SAML-first 的变体设计。"
- **code-audit.** "共识：『参数化查询能防止 SQL 注入。』该共识出错
  的区间：无法参数化的动态表名，如 [analytics.py:201](#L201)。
  分支：确认表名白名单是否穷尽。"

**Output.** ≥ 1 个针对在相关区间下最可能被打破的那个共识的子分支。

---

## §3.J — Failure-driven（失效驱动）

**Purpose.** 把具体的*当前*失效（而非假想的"本可以更好"）转化为
新的研究 / critique / 设计 / 审计问题。

**Prompt.** 列出节点当前拥有的 ≥ 3 个具体失效——每个都锚定到一个
`file:line`、Fig. N，或命令输出不匹配。对每一个："这个失效本身
是否是一个值得问的问题？"

**Per-preset flavor:**

- **brainstorm.** "失效：我们当前的 pipeline 漏掉了 10⁹–10¹⁰ M_sun
  区间内 30% 的子晕（最新报告的 Fig. 3）。这不是『本可以改进』
  ——它是一个具体量化的缺口。新分支：一个专门针对这个质量段、配以
  量身定制检测方案的子方向。"
- **attack.** "论文 Fig. 5 中观察到的失效：重建在 SNR < 3 处崩溃，
  而图注或正文均无说明。critique：论文所述的『跨所有 SNR 稳健』
  在机械意义上为假；修订或加 caveat。"
- **design.** "当前 admin 工具中观察到的失效：session 每 30 分钟
  过期，杀死进行中的工作。具体失效计数：本周 4 条愤怒的 Slack
  消息。新分支：把 session 存活优先于所提议的范围扩张。"
- **code-audit.** "观察到的失效：生产日志显示 [upload.py:42](#L42)
  在过去一个月抛出 `MemoryError` 12 次，总是发生在 80–100MB 之间
  的文件上。具体缺口，非假想。分支：streaming-hash 路径即是修复。"

**Output.** ≥ 1 个围绕最可付诸行动的当前失效构建的子分支。

---

## §3.K — High-risk asymmetric payoff（高风险非对称回报）

**Purpose.** 强制探索 ≥ 3 个候选分支，其期望值由一个*范式级*成功
的小概率所主导。挑出最具体的一个并完整推导它。

**Prompt.** 哪 3 个分支若成功，将代表节点的一次质的跃迁（而非增量
胜利）？多数在完整推导后将是 `DEAD-END`，但价值在于已经探索过。
跳过此框架视角是被禁止的（引擎 §F4）。

**Per-preset flavor:**

- **brainstorm.** "High-risk 1：通过单个背景星系上随时间变化的透镜
  特征对单个子晕的直接检测。若成真，单凭一己之力解决 WDM vs CDM。
  可行性概率低（需要微透镜级别的灵敏度），但值得完整推导以界定其
  可观测性需求。"
- **attack.** "High-risk 致命 critique：论文的核心结果取决于一个
  数值常数，沿 pipeline 追溯，它来自一个打错字的 CSV 单元格。若
  成真：需要全面撤稿。推导这条追溯链；若该常数实际正确，落到
  REFUTED。无论哪种，审计价值都很高。"
- **design.** "High-risk：完全放弃所提议的框架，转用一个托管服务
  （如 Workspace/Clerk + Workato 处理 workflow 部分）。若客户接受
  我们之前没考虑过的供应商锁定（vendor lock-in）权衡，这就快 5 倍
  上线、便宜 10 倍维护。推导所需的客户对话。"
- **code-audit.** "High-risk：不是『一个缓冲区溢出』，而是『通过
  针对负载均衡器的 HTTP header smuggling 完全绕过认证』。具体测试
  步骤：构造一个 `Transfer-Encoding: chunked\r\nContent-Length: 0`
  请求并观察下游行为。若可利用，则是 critical CVE 级别的发现。"

**Output.** ≥ 1 个完整推导的子分支（§4 全部 12 个字段），即便
verdict 落在 `DEAD-END` / `REFUTED` / `NOT-RECOMMENDED`。为合规而
塞进去的占位分支不计数。

---

## §3.L — Meta (LLM blind-spot self-audit)（元层：LLM 盲点自审）

**Purpose.** 抓住引擎自身产出训练分布形状输出的习惯。

**Prompt.** 自审，7 个问题，当作强制内省（而非打勾）：

1. **Distribution check（分布检查）.** 我所有的分支是否都来自
   训练分布中高频的框架视角（LLM 常说的那些）？在本领域*不常见*、
   但人类专家会期待的框架视角是什么？
2. **Writable vs important（可写 vs 重要）.** 我是否把"我能流畅写出
   散文的东西"与"实际重要的东西"混为一谈？
3. **LLM-rare-but-human-obvious（LLM 罕见但人类显然）.** 本领域的
   资深人类专家会立刻说出、而 LLM 训练数据稀薄的东西是什么？
4. **Smoothness check（流畅度检查）.** 我的输出是否在修辞上太
   流畅？真实的研究 / critique / 设计讨论是*粗糙的*、矛盾的、
   片面的。我在哪里显得可疑地连贯？
5. **Math-heavy branches（数学密集分支）.** 我是否在回避那些需要
   真正符号推导 / 数值模拟的分支？加一个。
6. **Implementation-heavy branches（实现密集分支）.** 我是否在回避
   那些需要运行代码 / 抓取数据 / 做实验的分支？加一个。
7. **Weirdness check（古怪度检查）.** 树里*最古怪*的那个分支是否
   真的古怪，还是只是乔装打扮的安全选项？若不古怪，强制再来一个。

**Per-preset flavor:**

- **brainstorm.** "自审揭示：我一直在生成信号检测分支（训练高频）
  但没有数据采集 / 仪器设计分支（训练罕见、人类显然）。新子分支：
  『什么样的望远镜时间分配提案能最好地测试方向 X？』"
- **attack.** "自审：我一直在生成统计批评分支（LLM 高频）但没有
  reviewer 在真实报告里实际会写的呈现质量 / 图表可读性分支。新
  子分支：攻击 Fig. 6 中遮蔽主要结果的排版 / 配色选择。"
- **design.** "自审：我一直在产出框架对比分支但没有
  『谁来建它』分支。新子分支：『能持有这个东西 3 年的最小团队
  是什么？』"
- **code-audit.** "自审：我一直在找标准 CWE 模式但没有
  『谁能利用这个』分支。新子分支：威胁模型——在什么攻击者能力下
  （内部人员 / 已认证用户 / 未认证 / 网络层）该发现才重要？"

**Output.** ≥ 1 个源自该自审盲点清单的子分支。它必须是一个*新*
分支，而非对树中已有内容的改写。

---

## §3.X — External resource cross-check (per node, unless `--no-online`)（外部资源交叉核对，逐节点，除非 `--no-online`）

**Purpose.** 针对外部状态——文献、仓库、数据集、工具、既有批评
——核验节点，这些外部状态可能已经做过相关工作或暴露出相关问题。
**搜什么由 preset 决定**（见下方 flavor）：brainstorm 节点搜寻先有
技术与可调用的工具；attack 节点搜寻针对该 artifact claim 的已发表
批评与勘误。用错查询集（例如在审计一篇论文时搜"langchain tool"）
就浪费了这次 pass。

**Steps.**

1. 用 preset 适配的查询集做 `WebSearch`（见 **Per-preset flavor**）。
   始终把 `<node subject> arxiv` / `<subject> github` 作为基线纳入；
   在其之上叠加该 preset 的专门查询。
2. 对每个有希望的命中，`WebFetch` 实际页面（而非 snippet）以确认
   内容与搜索描述相符——`WebSearch` snippet 本身永远不够（§F1）。
3. 把发现追加到节点的 §4 external 字段（brainstorm/design 用
   `external_resources`，attack/code-audit 用 `external_check` /
   `related_findings`），附 URL + 一行描述。

**Per-preset flavor:**

- **brainstorm.** 先有技术与*可调用的工具*：`<subject>
  arxiv` / `<subject> github` / `<subject> dataset` / `<subject>
  benchmark`，外加 `<subject> claude code plugin` / `<subject> mcp
  server` / `<subject> langchain tool`。目标："有人建过这个吗，
  我能复用吗？"
- **attack.** *针对该 artifact claim 的已发表批评*：`<claim
  keywords> erratum` / `<claim> arxiv comment` / `<claim> reply` /
  `<method> failure mode` / `<method> irreproducible`。同时
  `WebFetch` 该 artifact 自己引用的先有工作，以确认它确实说了
  artifact 所声称的内容——被歪曲的引用是一条高严重性 critique。
- **design.** *生产事后复盘与模式权衡*：
  `<pattern> architecture tradeoffs` / `<pattern> postmortem` /
  `<vendor/service> limits` / `<pattern> at scale`。目标："谁上线
  过这个，他们栽在哪里？"
- **code-audit.** *已知漏洞与公告*：
  `<dependency> CVE` / `<dependency> advisory` / `<pattern> CWE` /
  `<library> <version> security`。同时在仓库其他地方交叉 `Grep`
  同一模式（喂给 `related_findings`）。

**Output.** 把核验过的发现追加到节点的 external 字段。`--no-online`
模式跳过步骤 1–2；给节点打上 `external_resources_unchecked=true`
标记（§6 收敛仍然期待该标记——它不是免死金牌）。

---

## Notes on running the framings（运行框架视角的说明）

### Sequence vs parallelism（顺序 vs 并行）

- 对于预期宽度 ≥ 5 个子节点的节点（在根节点以及热叶节点处常见），
  可以通过把每个框架视角派发给一个 `Agent(Explore)` 子代理来并行
  运行这 12 个框架视角。每个子代理拿到节点的 §4 字段 + 框架视角
  prompt + 该 preset 的 flavor 示例。主代理合并结果并完成 §4 + §5。
- 对于较小的宽度（在树的深处、多数叶节点都边缘的地方），顺序运行
  即可——框架视角本身很廉价；成本在于其后的 §4 推导。

### Per-framing failure modes（各框架视角的失效模式）

- **A** "每条假设看起来都承重；一条都移除不了" → 节点的
  `assumptions` 字段欠规范；回到 §4 浮现出更多假设。
- **B** "反演是平凡的 / 空洞的" → 要么节点处于反演没有良好定义的
  域边界（声明之并继续），要么节点主题太含糊（锐化它）。
- **C** "没有跨领域有类似问题" → 真实的可能性；在声明前认真检查
  ≥ 3 个领域。负结果是可以的，且有信息量。
- **D** "最强的反驳很弱" → 暗示节点稳健；这本身就是有用的证据，
  但在声明前再尝试 ≥ 2 个反驳立场来核实。
- **K** "想不出 high-risk 分支" → 被禁止的结论（§F4）。逼自己来；
  价值在于*尝试*，即便所有 3 个候选在完整推导后都落到 DEAD-END。
- **L** "自审什么也没显示" → 被禁止的结论。自审本就该让人不适；
  若不让人不适，你就是在走过场。用更狠的问题重做。

### Calibration across rounds（跨轮校准）

在第 N+1 轮，重新展开一个 `advances` 叶节点时，引擎*应当*观察到
收益递减——`convergence_metric` 比值应当下降。若不下降，要么是
框架视角击中了真正肥沃的疆域（好——继续），要么是引擎在生成父节点
的伪发散变体（坏——更激进地应用 §F2 + §5.4 合并）。

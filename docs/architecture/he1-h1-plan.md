# H1 实施计划（草案）：封闭执行对象与身份

- 状态：**草案，non-normative**。评审通过后，规范决策写入 `ADR-0127`；本文件
  保留为实施计划、验收映射和待审问题清单。
- 基线：`d42125d`（H0 已提交，工作树干净）。文中行号均取自该提交。
- 上游：`ADR-0125`；`ADR-0126`（身份分层与构建收据）；`docs/architecture/he1-horizontal-extension.md` §8（不可变
  执行边界）、§13「H1」、§14（`HE-T02`/`HE-T03`/`HE-T04`/`HE-T20`）、§15.1。
- 完成定义：`HE-AC-06` 连同 `HE-T02`、`HE-T03`、`HE-T04` 由运行期测试或编译期
  测试证明；旧 128 个产物逐字节不变（`research/he1/compatibility-results.json`）。

本文件不宣称任何代码已经改动。H1 的产品代码改动尚未开始。

---

## 0. 一句话

把「验证过的定义」和「验证过的计划」变成**不可伪造的执行凭证**：执行所用的定义、
执行事实和对外身份来自同一份不可变快照；旧入口仍然可用，但不能再绕过验证。

## 1. 在 `d42125d` 上的实测现状

### 1.1 要关闭的缺口

| 缺口 | 证据 | H1 是否关闭 |
|---|---|---|
| 已加载定义可在内存中改写，摘要不变 | `tests/he1_identity_characterization.rs::a_loaded_definition_can_be_re_encoded_under_its_original_digest`（运行即复现） | 关闭 |
| 计划身份覆盖原始文档，不覆盖解析后的操作数 | 同文件 `a_parsed_operand_can_change_under_a_stable_fingerprint`（运行即复现） | 关闭 |
| 验证用的定义与执行用的定义是两个独立参数，可以不同 | 读签名即可见：`fmp_materialize::materialize(plan: &Plan, definition: &Definition)`（`fmp-materialize/src/lib.rs:343`）。**静态事实，不是测试**：类型上不阻止传另一份定义 | 关闭 |
| 一个未被选中的 `*.json` 决定整个加载成败 | `an_unselected_file_in_the_definition_directory_breaks_loading`（运行即复现） | 否 — H3 |
| 新 ISA 命名空间需要改核心 match | `a_synthetic_namespace_is_rejected_by_the_loader`（运行即复现；`definition.rs:714-756`） | 否 — H3 |
| 深层 JSON 无界 | `tools/he1_baseline.py --probes` 的 `deep-json` 探针：退出 `3221225725`（**不是**六个 Rust 测试之一） | 否 — H4 |

H0 报告最初写「五个测试以记录漏洞的方式通过」，这是**错误分类**：那六个测试实际是
**4 个缺口 + 2 个对照**（摘要失配拒绝、非对象顶层拒绝），深层 JSON 的证据来自
Python 探针。缺口本身不变，错的是归类；`ADR-0126` 已在 `H0-report.md` §6 更正。
H1 只翻转前两条（定义重编码、稳定指纹），这一点写进 `ADR-0127`，避免验收时把
H3/H4 的条目算进 H1。

### 1.2 受影响的公共面（在 `d42125d` 上计数）

| 符号 | 定义位置 | 调用点 |
|---|---|---|
| `fmp_materialize::materialize(&Plan, &Definition)` | `fmp-materialize/src/lib.rs:343` | 19 处（`fmp-cli/src/main.rs` 1、`fixtures.rs` 2、`determinism.rs` 4、`planner_api.rs` 3、`he1_identity_characterization.rs` 4、`fmp-materialize` 自身 5） |
| `fmp_materialize::fingerprint(&Plan, &Definition)` | 同文件 `:919` | 11 处 |
| `Registry::load_dir` | `fmp-model/src/definition.rs:788` | 8 处 |
| `Definition` 的公开字段读写 | `definition.rs:21-30` | `forms`/`digest`/`namespace`/`version`/`target`/`definition_format` 共约 30 处 |
| `Plan`/`Instruction`/`Operand` 的公开字段 | `plan.rs:21-33`、`:136-166` | 大量；H1 **不**封闭它们（见 §2.3） |

已确认的三个事实，后面每条设计都依赖它们：

1. `Definition.digest` 是**加载时**由 `canonical_digest(document)` 算出的
   （`definition.rs:217`），不是外来字符串；H0 的缺口来自 `forms` 是文档的
   可写投影，而不是摘要算法本身。
2. `Definition.document` 被保存但**从未读取**（全仓库只有 `definition.rs:219`
   一处写入）：同一事实存在两份拷贝，是「两个权威来源」的现成入口。
3. 编码后仍可能失败的是 `E-SIZE-001`（`lib.rs:583`）与 `E-BYTE-001`
   （`lib.rs:597`）；负例里有 2 个和 1 个分别命中它们。宿主故障不在
   `materialize` 内，它由 CLI 的 `Failure::Io` 承担（`main.rs:45-48`，exit 2）。

## 2. 目标类型生命周期

### 2.1 图

```text
definition bytes --read--> Definition（字段私有、无 &mut、无公开构造）
                                   |
plan bytes --read--> Plan（公开 DTO，可以可变）        |
                                   |                   |
                                   +--- bind ----------+--> ValidatedPlan
                                        （摘要比对 + check + 身份）
                                                              |
                                                              v
                                                        materialize
                                                              |
                                                    Artifact（DTO，envelope 不变）
                                                              |
                                           artifact_digest / ExecutionIdentity
```

### 2.2 四个身份

| 身份 | 类型（拟） | 覆盖什么 | 缺它的具体反例 | 反例来源 |
|---|---|---|---|---|
| plan | `fmp_model::identity::PlanIdentity` | 解析后的全部计划字段，除 `provenance` 与已删除的 `document` | 改 `operands[1].payload.reg`，身份不变 → 同一凭证对应不同机器码 | **已实测**（H0 测试 2） |
| definition | 现有 `namespace`/`version`/`digest` 的只读访问 | 定义文档的 canonical 摘要 | 改模板保留摘要 → 同一凭证执行未验证规则 | **已实测**（H0 测试 1） |
| artifact | `fmp_materialize::artifact_digest(&Artifact)` | `Artifact::to_json()` 的 canonical sha256 | 产物变化但身份不变 → 回放无法证明同一输出 | 由 `he1_baseline.py` 的 `artifact_root` 实现验证 |
| implementation | `fmp_model::identity::ImplementationIdentity` | `env!("CARGO_PKG_NAME")` + `env!("CARGO_PKG_VERSION")`，编译期常量 | 构建版本变化无法追踪（`HE-T20`） | 当前 envelope 只有 `materializer_version` |

`ExecutionIdentity` 由 `bind` 产出并挂在 `ValidatedPlan` 上，含前两项与
implementation；artifact 身份在产物存在后才能算，单独提供。

**不新增 envelope 成员。** `fixtures/x86_64/positive/X86-P71` 的
`expected-artifact.json` 固定了整个 envelope 形状（`fixtures.rs:143-153`），
加字段会让它和 128 项基线同时失败。新身份只出现在新的 API 返回值里，H3 建
run receipt 时才决定是否需要写进新协议。

### 2.3 哪些类型封闭、哪些不封闭

- **封闭**：`Definition`（字段私有、删除 `document`、不实现 `Clone`，由
  `Arc<Definition>` 共享）。理由：它是执行凭证的一半，`HE-AC-06` 直接点名它。
- **不封闭**：`Plan`、`Instruction`、`Operand`、`Fixup`。设计 §8.2 允许公开 DTO
  可变，只要它**不是执行凭证**。这样 `planner_api.rs` 里大量「解析后改一个字段
  造负例」的写法继续成立，改动面从 ~1500 行降到 ~20 处。
- `ValidatedPlan` 是唯一凭证：私有字段、无 `&mut`、无公开构造、不实现 `Clone`
  （克隆会制造第二份可独立演进的事实，收益为零）。

## 3. 改动清单

### 3.1 `fmp-model`

| 文件 | 改动 |
|---|---|
| `src/definition.rs` | `Definition` 字段全部私有：`document` 删除，`forms`/`digest`/`namespace`/`version`/`target`/`definition_format` 改为只读方法；`bind_document`（`:177-227`）仍是唯一构造点；`Registry` 改存 `Vec<Arc<Definition>>`，`find` 返回 `Arc<Definition>` |
| `src/identity.rs`（新增） | `plan_facts(&Plan) -> Vec<u8>`：定长、无 map、无浮点、无宏；`PlanIdentity::of(&Plan)`；`ImplementationIdentity::{name, version}` |
| `src/lib.rs` | 导出 `identity` 模块与 `PlanIdentity`、`ImplementationIdentity` |
| `src/definition.rs` 测试 | 现有 22 个模型测试按访问器改；新增「同一字节两次加载摘要相同」 |

`plan_facts` 的编码规则（写进 `ADR-0127`，因为它定义身份含义）：

- 每个节点一个 tag 字节；字符串/数组以 `u64` 小端长度前缀；`i128` 写 16 字节
  二进制补码；对象按**结构体字段声明顺序**写出，不排序；`Option` 写 1 字节
  presence。
- 排除：`Plan.document`、`Plan.provenance`。其余全部包含，包括 `path`
  （诊断用指针）。包含 `path` 是有意选择：身份只需**至少**覆盖执行事实，多覆盖
  一个确定性字段不产生歧义；若将来证明 `path` 会误伤，仍需新 ADR 才能改。

### 3.2 `fmp-validate`

| 项 | 改动 |
|---|---|
| `ValidatedPlan`（新增） | `{ plan: Plan, definition: Arc<Definition>, identity: ExecutionIdentity }`；唯一构造 `bind(plan: Plan, definition: Arc<Definition>) -> Result<Self, Vec<Diagnostic>>` |
| `bind` | 复用现有顺序：先摘要比对（现 `materialize` 的 `:349-359`），再 `check`，最后 `diagnostic::sort`。顺序不变是负例门禁的前提 |
| `check` | 签名不变，内部改走访问器 |
| `ExecutionIdentity`（新增） | `{ plan: PlanIdentity, definition: DefinitionIdentity, implementation: ImplementationIdentity }` |
| `Model` | 不变（只读视图） |

`bind` 承接今天的摘要错误，因此负例里那条 `E-DEF-001`
`/definition_identity/digest` 的输出必须逐字节相同。

### 3.3 `fmp-materialize`

| 项 | 改动 |
|---|---|
| `materialize` | 改为 `materialize(&ValidatedPlan) -> Result<Artifact, MaterializationFailure>`，不再接收 `&Plan`/`&Definition`，也**不再重复**摘要比对与 `check` |
| `MaterializationFailure`（新增） | `Rejected(Vec<Diagnostic>)`、`Assertion(Vec<Diagnostic>)`（`E-SIZE-001`/`E-BYTE-001`）、`Internal(Diagnostic)`（`E-INTERNAL-001`）。三者都是计划/定义决定的；宿主故障留在 CLI exit 2，不设不可构造的变体 |
| `fingerprint` | **算法与输出逐字节不变**，文档注释改为「legacy envelope 身份，按 `ADR-0123` 解释；不覆盖解析后的操作数；不可用于新身份」 |
| `artifact_digest`（新增） | `canonical_digest(&artifact.to_json())` |
| `lookup`（`:881`） | 走 `definition.forms()` |
| `legacy::materialize`（新增，`#[deprecated]`） | `(&Plan, Arc<Definition>)`：内部 `bind` 后调用新 `materialize`。存在意义是给一份过渡期入口，且测试证明它同样拒绝摘要不符 |

### 3.4 `fmp-cli`

`main.rs:100-110` 改为 `Registry::load_dir` → `plan::read` → `Registry::find`
（得 `Arc<Definition>`）→ `bind` → `materialize`。失败仍把完整诊断数组写到
stderr、exit 1；`MaterializationFailure` 的三个变体都按同一格式打印，负例输出
不变。

### 3.5 测试改造

| 文件 | 改动 |
|---|---|
| `he1_identity_characterization.rs` | 2 条翻转成拒绝测试；其余 4 条保留，文件头加「所属阶段」表（H1 关 2 条、H3 关 2 条、H4 关 1 条、1 条对照） |
| `fixtures.rs`、`determinism.rs`、`planner_api.rs` | `materialize` 改走 `bind`；`find` 返回 `Arc` 后约 8 处加 `&` |
| `fmp-materialize` 单测 | 5 处 `materialize` + 4 处 `fingerprint` 按新签名改 |

## 4. 测试计划

### 4.1 编译期（`HE-T02`/`HE-T04`，「API 不可表达」）

用 `compile_fail` doctest，零新依赖：

| 位置 | 断言 |
|---|---|
| `fmp-model` crate 文档 | 外部 crate 不能写 `definition.forms`，不能 `Definition { .. }` |
| `fmp-validate` crate 文档 | 不能 `ValidatedPlan { .. }`，不能 `Clone`；`materialize` 只接受一个参数，无法「用 A 验证、传 B 执行」 |

限制：`compile_fail` 只证明「编译失败」，不证明失败**原因**。计划在 doc 注释里
写明这一点，并在评审时人工核对一次失败信息。

### 4.2 运行期

| 测试（拟名） | 断言 | 对应 |
|---|---|---|
| `a_definition_reloads_to_the_same_digest` | 同一字节两次加载摘要相同；换行/键序不同但 canonical 相同则摘要相同 | `HE-T03` |
| `a_tampered_definition_document_is_rejected_by_bind` | 改模板保留计划中的旧摘要 → `E-DEF-001` `/definition_identity/digest` | `HE-T03` |
| `a_mutated_operand_changes_the_plan_identity` | 改 `payload.reg` → `PlanIdentity` 变 | `HE-T02`/`HE-T04` |
| `plan_identity_covers_every_parsed_field` | 逐字段 mutation 表（section/instruction/operand/modifier/fixup/symbol/output/target），每项都必须改变身份 | 硬规则 2 的逐字段反例 |
| `plan_identity_ignores_provenance` | 只改 `provenance` → 身份不变（与 legacy `fingerprint` 的排除一致） | §12 |
| `artifact_digest_follows_the_bytes` | 改一个操作数 → 字节变 → artifact 身份变 | `HE-T20` |
| `legacy_facade_rejects_a_digest_mismatch` | 二参 facade 同样拒绝（H0 的对照测试迁到这里） | `HE-T04` |
| `bind_reports_the_definition_it_bound` | `identity.definition.digest` 等于实际执行定义的摘要 | `HE-AC-06` |

### 4.3 金样与既有门禁

| 门禁 | 保证什么 |
|---|---|
| `python tools/he1_baseline.py --check research/he1/compatibility-results.json` | 128 个产物、104 个定义摘要、计数、oracle 状态全不变 |
| `cargo test --workspace` 的 `fixtures`/`planner_api` | 619 个负例的诊断数组**逐一相等**（含新增的 3 条编码后失败） |
| `fixtures.rs` 的 Level-1 用例 | envelope 形状未被新身份污染 |
| `tools/oracle/rerun.py` | 122 条仍可复现 |

## 5. 兼容性影响

| 项 | 结论 |
|---|---|
| 128 个正例产物 | 不变（`artifact_root` 不变） |
| 旧 `fingerprint` | 不变；语义标注为 legacy |
| Artifact envelope | 不加字段 |
| 619 个负例诊断 | 不变；`bind` 保持「先摘要、后 check、再排序」 |
| 定义文件与形态 | 不改；`definitions/**` 一个字节不动 |
| 错误码 | 不新增。`E-DEF-001`/`E-SIZE-001`/`E-BYTE-001`/`E-INTERNAL-001` 均已注册 |
| 计数 | 不改 `STATUS.md` 的 v0 计数；测试数会变（6 个 characterization 里 2 个改名/翻转） |
| 依赖方向 | 不变：`validate → model`，`materialize → validate + model` |

## 6. 提交拆分与门禁

| 提交 | 内容 | 每步必过 |
|---|---|---|
| H1a | `Definition` 封闭 + `Registry` 用 `Arc` + `identity` 模块 + 逐字段 mutation 测试 | `fmt`、`test --workspace`、`baseline --check`、`check_ids` |
| H1b | `ValidatedPlan` + `bind` + 新 `materialize` 签名 + `MaterializationFailure` + facade + 调用点迁移 + 2 条测试翻转 | 同上 + `oracle` + `check_definition` |
| 同 PR | `docs/adr/0126-*.md` + 本文件改为「已采纳」+ `research/he1/H1-report.md` | `check_ids`、`git diff --cached --check` |

一个 PR 两个提交：`ADR-0125` 决策 1 要求 H1 是一个阶段，§13.1 要求阶段内可回归。

## 7. 风险与回滚

| 风险 | 处置 |
|---|---|
| 身份算法写错，导致不同事实同身份 | 逐字段 mutation 表；`plan_facts` 是纯函数，可单测 |
| `plan_facts` 与 `bind` 漂移成两个权威来源 | 只从 `Plan` 读数，不读 `document`；`document` 字段直接删除 |
| 诊断顺序变化，负例面扩大 | 619 个负例的等式门禁；`bind` 内顺序照抄现实现 |
| `Arc` 改动扩散 | 编译器引导，约 8 处；`Registry` 仍保持确定性顺序 |
| 有人继续用二参入口绕过 | facade 内部就是 `bind`；另加一条测试证明摘要不符仍被拒 |
| envelope 意外新增字段 | Level-1 夹具 + `artifact_root` |

回滚：整个 PR 可整体撤回。H1 不动定义文件、不动协议版本，没有需要迁移的持久
状态。

## 8. 明确不在 H1 内

- bundle/package 格式、`fmp-definition` crate（H2）。
- `fmp/0.2`、命名空间化的 ISA 身份、零操作数 form（H3）。
- `load_dir` 全目录扫描、`check_form_id` 白名单（H3）。
- 解析深度上限、64 MiB 映像上限（H4）。
- fixup profile 与新原语（H4）。
- 任何指令覆盖扩张。

## 9. 待审决策

| # | 问题 | 推荐 | 备选与代价 |
|---|---|---|---|
| D1 | `Definition` 就地封闭还是改名 `VerifiedDefinition` | **就地封闭**；H2 由 `fmp-definition` 的 `VerifiedBundle` 包装 | 现在改名会让 ~40 处调用点动一次，H2 再动一次 |
| D2 | `Registry::find` 返回 `Arc<Definition>` | **是** | 返回 `&Definition` 则需要另一条「取所有权」的路径，等于两个入口 |
| D3 | 身份覆盖「除 `provenance` 外全部解析字段」 | **是**（含 `path`） | 只覆盖影响字节的字段：身份更窄，逐字段反例表更难写清 |
| D4 | 错误分类三变体（`Rejected`/`Assertion`/`Internal`） | **是**，不加宿主变体 | 加 `HostFailure` 会产生一个永不可构造的分支 |
| D5 | 是否保留 `legacy::materialize` | **保留一个阶段**，`#[deprecated]`，内部走 `bind` | 直接删除：所有调用点必须一次改完，回滚变难 |
| D6 | 旧 `fingerprint` 是否改算法 | **不改**，标注 legacy，新身份不复用它 | 改算法会移动 128 个产物 → 违反 `HE-AC-10` |
| D7 | `plan_facts` 手写还是复用 `fmp-plan` 序列化 | **手写**在 `fmp-model` | `fmp-plan` 有第二套 DTO（`fmp-plan/src/lib.rs:155-280`），复用会把第二个权威来源带进执行路径 |

## 10. 证据状态

| 结论 | 依据 | 状态 |
|---|---|---|
| 六个缺口中的三个由 H1 关闭 | H0 测试 + `HE-T` 表 | 高（测试已复现） |
| `Definition.digest` 在加载时由文档算出 | 读 `definition.rs:217` | 高 |
| `Definition.document` 从未被读取 | 全仓库 grep `.document`：只有写入处 | 高 |
| 编码后失败只有 `E-SIZE-001`/`E-BYTE-001` | 读 `lib.rs:583`、`:597`；负例计数 2 与 1 | 高 |
| envelope 不能加字段 | `fixtures.rs:143-153` 固定整份 artifact | 高 |
| 调用点数量 | 在 `d42125d` 上 grep 计数 | 高（会随实现变动） |
| `compile_fail` doctest 能覆盖 API 约束 | 未在本仓库跑过 | **未验证** — 第一个提交时先证明它能触发 |
| 两个提交都全绿 | 尚未实施 | 未验证 |

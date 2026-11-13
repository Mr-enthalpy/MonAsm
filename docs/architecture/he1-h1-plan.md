# H1 实施计划：封闭执行对象与身份

- 状态：**已采纳（H1a 与 H1b 已落地；H1 验收待三主机 CI）**。规范决策在
  `docs/adr/0127-execution-identity.md`；本文件保留为实施计划、验收映射和
  待审问题清单。H1a/H1b 的实现范围与实测证据见 `research/he1/H1-report.md`。
- 基线：`d42125d`（H0 已提交，工作树干净）。文中行号均取自该提交；H1a 新增
  代码的行号取自 `he1/h1a-identity-core` 的落地提交。
- 上游：`ADR-0125`；`ADR-0126`（身份分层与构建收据）；
  `docs/architecture/he1-horizontal-extension.md` §8（不可变执行边界）、
  §13「H1」、§14（`HE-T02`/`HE-T03`/`HE-T04`/`HE-T20`）、§15.1。
- 完成定义：`HE-AC-06` 连同 `HE-T02`、`HE-T03`、`HE-T04` 由运行期测试或编译期
  测试证明；旧 128 个产物载荷（`payload/0.1` 投影）逐字节不变
  （`research/he1/compatibility-results.json` 的 `payload_root`）。

H1a（§6 表第一行）已落地并全绿：`Definition` 封闭、`Registry` 改用
`Arc<Definition>`、`identity` 模块与 `plan-identity/0.1`、`Plan.legacy_document`
改名、`plan::check_structure`、validator 的 `u128`/`u64`/`checked_*` 硬化、
`page ⇒ pcrel_page` 规则、九条直接调用 `check_structure`/`check` 的测试函数
（计划里的八类反例加寄存器宽度复现）、`internal(...)` 前提表与编码后失败阶段
实测。H1b（§6 表第二行）也已落地：`ValidatedPlan`、`bind`、新的
`materialize`、`ExecutionReceipt`、`MaterializationFailure`、CLI 失败分流和
facade 都已实现并被测试覆盖；`bind`/`materialize` 的 doctest 把「只能传
`ValidatedPlan`」写成编译期负例。H1 的**验收**仍未宣称完成：
`FMP_BUILD_ID` 仍为 `None`，debug/release 载荷一致性未测，三主机 CI 尚未运行。

---

## 0. 一句话

把「验证过的定义」和「验证过的计划」变成**不可伪造的执行凭证**：执行所用的定义、
执行事实和对外身份来自同一份不可变快照；旧入口仍然可用，但不能再绕过验证。

## 1. 在 `d42125d` 上的实测现状

### 1.1 要关闭的缺口

| 缺口 | 证据 | H1 是否关闭 |
|---|---|---|
| 已加载定义可在内存中改写，摘要不变 | `tests/he1_identity_characterization.rs::a_loaded_definition_can_be_re_encoded_under_its_original_digest`（运行即复现） | 关闭 |
| 计划身份覆盖原始文档，不覆盖解析后的操作数 | 同文件 `a_parsed_operand_can_change_under_a_stable_fingerprint`（运行即复现） | 关闭 — 由 `ParsedPlanIdentity`/`ExecutionReceipt` 覆盖解析后事实；旧 `fingerprint` 仍不变是**保留的 legacy 行为**，不是待翻转的缺陷 |
| 验证用的定义与执行用的定义是两个独立参数，可以不同 | 读签名即可见：`fmp_materialize::materialize(plan: &Plan, definition: &Definition)`（`fmp-materialize/src/lib.rs:343`）。**静态事实，不是测试**：类型上不阻止传另一份定义 | 关闭 |
| 一个未被选中的 `*.json` 决定整个加载成败 | `an_unselected_file_in_the_definition_directory_breaks_loading`（运行即复现） | 否 — H3 |
| 新 ISA 命名空间需要改核心 match | `a_synthetic_namespace_is_rejected_by_the_loader`（运行即复现；`definition.rs:714-756`） | 否 — H3 |
| 深层 JSON 无界 | `tools/he1_baseline.py --probes` 的 `deep-json` 探针：退出 `3221225725`（**不是** Rust 测试之一） | 否 — H4 |
| 旧指纹依赖解析器丢弃的原始文档字段 | `a_legacy_fingerprint_covers_document_fields_the_parser_drops`：加 `source_trace` 后解析结果不变、指纹改变 | **必须保留**（约束，不是缺口；`D12`） |

H0 报告最初写「五个测试以记录漏洞的方式通过」，这是**错误分类**：那批测试实际是
**4 个缺口 + 1 个约束 + 2 个对照**（摘要失配拒绝、非对象顶层拒绝），深层 JSON 的
证据来自 Python 探针。缺口本身不变，错的是归类；`ADR-0126` 已在 `H0-report.md` §6
更正，第二轮评审后又补了那条约束测试（`H0-report.md` §7）。
H1 不再「翻转稳定指纹」：第一条按 §4.1 改成 `compile_fail` + 重载测试；第二条
（解析后操作数变化、旧指纹不变）保留为 legacy 行为，由 `ParsedPlanIdentity` 与
`ExecutionReceipt` 覆盖新事实。H1 保留约束测试，这一点写进 `ADR-0127`，避免验收时
把 H3/H4 的条目算进 H1。

第七轮的两项发现（`bind` 未比 namespace/version、`page` 缺 PC reference）不属于这张
H0 缺口表：它们来自**新信任边界**的职责划分，记在 §3.2 与 D15/D16，不改变「H1 关闭
三个 H0 缺口」的计数。

### 1.2 受影响的公共面（在 `d42125d` 上计数）

| 符号 | 定义位置 | 调用点 |
|---|---|---|
| `fmp_materialize::materialize(&Plan, &Definition)` | `fmp-materialize/src/lib.rs:343` | 19 处（`fmp-cli/src/main.rs` 1、`fixtures.rs` 2、`determinism.rs` 4、`planner_api.rs` 3、`he1_identity_characterization.rs` 4、`fmp-materialize` 自身 5） |
| `fmp_materialize::fingerprint(&Plan, &Definition)` | 同文件 `:919` | 14 处（`d42125d` 上 11 处；H0 的 legacy 约束测试多 3 处） |
| `Registry::load_dir` | `fmp-model/src/definition.rs:788` | 8 处 |
| `Definition` 的公开字段读写 | `definition.rs:21-30` | `forms`/`digest`/`namespace`/`version`/`target`/`definition_format` 共约 30 处 |
| `Plan`/`Instruction`/`Operand` 的公开字段 | `plan.rs:21-33`、`:136-166` | 大量；H1 **不**封闭它们（见 §2.3） |

已确认的三个事实，后面每条设计都依赖它们：

1. `Definition.digest` 是**加载时**由 `canonical_digest(document)` 算出的
   （`definition.rs:217`），不是外来字符串；H0 的缺口来自 `forms` 是文档的
   可写投影，而不是摘要算法本身。
2. `Definition.document` 被保存但**从未读取**（全仓库只有 `definition.rs:219`
   一处写入）：同一事实存在两份拷贝，是「两个权威来源」的现成入口。
3. `emit`/`apply` 的失败路径**不止** `E-SIZE-001` 与 `E-BYTE-001`：
   `E-FIXUP-002`、`E-RANGE-003`、`E-FIXUP-003` 也只在编码阶段产生；而
   `E-SIZE-001` 的两个负例先被 `validate` 拒绝，不进入 `emit`。`emit` 还调用
   `try_reserve_exact`，所以分配失败是**物化器内部**的宿主事实，不是 CLI 独有。
   每条路径最终归入哪个阶段由 H1a 实测（§4.3）；D4 的 `HostFailure` 以此为前提。

### 1.3 已撤回的旧结论

以下两句曾作为「当前事实」写在本节，后续评审已推翻；保留在此仅作修订历史，
**不得**再作为 H1 的实施前提：

| 旧结论 | 为什么撤回 | 取代它的当前事实 |
|---|---|---|
| 「编码后仍可能失败的只有 `E-SIZE-001` 与 `E-BYTE-001`」 | 只读了 `emit` 的两个返回点；`apply` 的 `E-RANGE-003`/`E-FIXUP-003`/`E-FIXUP-002` 也是编码阶段失败，且 `E-SIZE-001` 的负例实际由 `validate` 拒绝 | §1.2 第 3 条与 §4.3 的阶段表；集合由 H1a 实测决定 |
| 「宿主故障不在 `materialize` 内，由 CLI 的 `Failure::Io` 承担」 | `emit` 的 `try_reserve_exact` 是物化器内的分配；没有 I/O 不等于没有宿主故障 | `MaterializationFailure::HostFailure(HostFault)`（D4）；CLI 只负责映射到 exit 2 |

## 2. 目标类型生命周期

### 2.1 图

```text
definition bytes --read--> Definition（字段私有、无 &mut、无公开构造）
                                   |
plan bytes --read--> Plan（公开 DTO，可以可变）        |
                                   |                   |
                                   +--- bind ----------+--> ValidatedPlan
                                        （摘要比对 + check + BindIdentity）
                                                              |
                                                              v
                                                         materialize
                                                              |
                                          Artifact + ExecutionReceipt
                                     （implementation 与 payload 由物化器附加）
```

依赖方向只有两条边，且不新增第三条：

- `fmp-validate → fmp-model`（现状，`fmp-validate/Cargo.toml` 只依赖模型）；
- `fmp-materialize → fmp-validate + fmp-model`。

所以**构建身份不能出现在验证器里**。`bind` 产出 `BindIdentity { plan, definition }`；
`ImplementationIdentity` 与载荷身份由 `fmp-materialize` 在真正执行、产物存在之后附加，
组成 `ExecutionReceipt`。分层依据是「谁才知道它」：验证器不可能知道将来由谁执行。

### 2.2 四个身份

四者分开，因为混在一起会让「构建变了」和「编码变了」无法区分——H0 的
`artifact_root` 就是这个错误（`ADR-0126`）。

| 身份 | 类型（拟） | 定义位置 | 覆盖什么 | 缺它的具体反例 | 反例来源 |
|---|---|---|---|---|---|
| plan | `fmp_model::identity::ParsedPlanIdentity` | `fmp-model` | 解析后的全部计划字段，除 `provenance` 与 `legacy_document`；算法名 `plan-identity/0.1` | 改 `operands[1].payload.reg`，身份不变 → 同一凭证对应不同机器码 | **已实测**（H0 测试 2） |
| definition | 现有 `namespace`/`version`/`digest` 的只读访问 | `fmp-model` | 定义文档的 canonical 摘要（加载时算出） | 改模板保留摘要 → 同一凭证执行未验证规则 | **已实测**（H0 测试 1） |
| artifact | `fmp_materialize::payload_digest(&Artifact)` | `fmp-materialize` | `payload/0.1` 投影的 canonical sha256：artifact 去掉 `materializer_version` | 只哈希 `bytes_hex`：改一个 fixup 的 target/addend 而字节不变 → 回放声称同一输出 | `ADR-0126` 决策 1 的反例栏 |
| implementation | `fmp_materialize::ImplementationIdentity` | **物化器构建层**，不是 `fmp-model` | `{name, version, build: Option<String>}`；`build` 来自 `option_env!("FMP_BUILD_ID")` | 取 `fmp-model` 的 `CARGO_PKG_*`：名字是 `fmp-model`、版本是 workspace 的 `0.0.0`，两个不同提交的身份会相同（`HE-T20` 不满足） | 读 `prototype/Cargo.toml`；`ADR-0126` Context 第 1 条 |

命名上的一处收紧：plan 身份叫「**解析快照**身份」（`ParsedPlanIdentity`），不叫
「机器语义身份」。它覆盖 `path`（诊断指针），而 `path` 不是编码决策；叫成「语义
身份」会让人以为身份变了一定意味着机器码变。

`bind` 只产出计划与定义的绑定身份，挂在 `ValidatedPlan` 上：

```text
BindIdentity      { plan: ParsedPlanIdentity, definition: DefinitionIdentity }   // fmp-validate
ExecutionReceipt  { bind: BindIdentity, implementation: ImplementationIdentity,
                    payload: PayloadIdentity }                                     // fmp-materialize
```

`ValidatedPlan` 里没有 implementation 字段。**这条不是风格选择**：`fmp-validate`
引用 `fmp-materialize` 的类型会形成 crate 环（后者已经依赖前者）；就算绕开环，让
验证结果依赖「谁在验证」也违反 `INV-05`——同一计划的验证结论必须与宿主无关。
`ExecutionReceipt` 由 `materialize` 返回（§3.3），因此「执行过」和「有收据」是同一
件事，不存在忘记调用的空档。

**`BindIdentity` 不是完整产物的身份。** 反例：计划 B 只是在原始文档里多一个
`source_trace`。`ParsedPlanIdentity(A) == ParsedPlanIdentity(B)`，
`DefinitionIdentity(A) == DefinitionIdentity(B)`，但 `source_trace` 进入旧
`fingerprint`，而 `fingerprint` 是 Artifact 的字段，所以
`payload_digest(A) != payload_digest(B)`。完整收据（含 `PayloadIdentity`）能区分
两者；`BindIdentity` 不能。任何缓存、重放或「同一份输入」判断都必须用完整收据，
或者额外绑定 `legacy_document` 的摘要。这条写进 `ADR-0127`，并由
`a_bind_identity_does_not_identify_the_legacy_artifact` 实测。

`ImplementationIdentity` 取不到 `FMP_BUILD_ID` 时记为 `build: None`，并**不再宣称**
满足 `HE-T20`——只有记录了 `build` 的构建才满足。它是编译期常量
（`option_env!`），运行期不读环境变量、主机名或时间，所以不触碰 `INV-05`。

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
  **但「公开可变」不等于「可信」**：`plan::read` 施加的结构约束（`payload_hex`
  必须是偶数长度的小写十六进制，以及 `lsb`/`width`/`bits`/`align_bits`/
  `transform_shift` 五个数值边界）不会随类型进入 DTO。`bind` 必须用
  `plan::check_structure(&Plan)` 重新验证这些非类型化不变量，再生成
  `ValidatedPlan`（§3.2、D13）。信任来自重新验证，不来自「它曾经由解析器构造」。
- **`Plan.legacy_document` 保留，但只有一个读者**：`Plan.document` 改名为
  `legacy_document`，注释写明「只供 `fingerprint()`；`bind`、`ParsedPlanIdentity`
  与编码/布局/fixup 决策都不得读取」。它不参与编码、布局或 fixup 决策，但旧
  `fingerprint()` 是 Artifact 的字段，所以它经 `fingerprint` 仍影响
  `payload_digest`——这两句话必须同时成立（§2.2 的反例）。它不能删：解析 DTO 不
  保留 `source_trace`、`symbol.type`、`symbol.size`，而旧 `fingerprint()` 哈希的是
  原始文档（`fmp-materialize/src/lib.rs:920`），删掉字段就没法保持旧指纹逐字节
  不变。`a_legacy_fingerprint_covers_document_fields_the_parser_drops` 已实测这一点。
  要删除它，必须先改指纹算法并新开 ADR——不能用「删一个没人读的字段」的名义做。
- `ValidatedPlan` 是唯一凭证：私有字段、无 `&mut`、无公开构造、不实现 `Clone`
  （克隆会制造第二份可独立演进的事实，收益为零）。

## 3. 改动清单

### 3.1 `fmp-model`

| 文件 | 改动 |
|---|---|
| `src/definition.rs` | `Definition` 字段全部私有：`document` 删除，`forms`/`digest`/`namespace`/`version`/`target`/`definition_format` 改为只读方法；`bind_document`（`:177-227`）仍是唯一构造点；`Registry` 改存 `Vec<Arc<Definition>>`，`find` 返回 `Arc<Definition>` |
| `src/identity.rs`（新增） | `plan_facts(&Plan) -> Vec<u8>`：定长、无 map、无浮点、无宏；`ParsedPlanIdentity::of(&Plan)`，算法名 `plan-identity/0.1`。**不放** `ImplementationIdentity`——它属于物化器层 |
| `src/plan.rs` | `Plan.document` 改名 `legacy_document`，字段注释限定为「旧 `fingerprint()` 的唯一输入」；新增 `pub fn check_structure(&Plan) -> Vec<Diagnostic>`：重放 `plan::read` 中**未被类型强制**的结构规则（`format_version`、`FragmentBody::Data` 的 `payload_hex`、以及下表五个数值边界），只读计划字段、不读 `legacy_document`；不加任何新访问器 |
| `src/lib.rs` | 导出 `identity` 模块与 `ParsedPlanIdentity`；**不**导出 `ImplementationIdentity` |
| `src/definition.rs` 测试 | 现有 22 个模型测试按访问器改；新增「同一字节两次加载摘要相同」 |

`check_structure` 的范围要写死，避免变成第二个 `check`。它只重放**类型系统接不住**
的解析规则，分三类：

1. `String` 内容规则：`format_version == fmp/0.1`；每个 `FragmentBody::Data` 的
   `payload_hex` 是偶数长度小写十六进制。
2. 数值上界比 DTO 类型窄的字段。下表是第五轮评审（`cb1e4ad`）要求补全的五项；
   它们都能在内存中绕过 `plan::read`，而现有 `check` 并不完整复查：

| 可变字段 | 解析器边界 | DTO 类型 | 现有 validator 复查 | 越界后的具体风险 |
|---|---|---|---|---|
| `Fixup.field_descriptor[i].lsb` | 0–127（`plan.rs:928`，域标签 `u7`） | `u32` | 无 | `field.lsb + field.width` 在 `validate/src/lib.rs:963`、`:1274`、`:1532` 以 `u32` 相加，可溢出 |
| `Fixup.field_descriptor[i].width` | 1–64（`plan.rs:929`，`u7`） | `u32` | 无 | 同上；`write_descriptor` 的 `remaining -= field.width`（`materialize/src/lib.rs:849`）会下溢，`write_bits` 可做异常大的逐位循环 |
| `Fixup.range_constraint.bits` | 1–64（`plan.rs:941`，`u7`） | `u32` | 无 | `1i128 << (bits - 1)` 在 `bits == 0` 时下溢，`bits > 127` 时移位溢出（`validate/src/lib.rs:833-840`） |
| `Fixup.range_constraint.align_bits` | 0–12（`plan.rs:942`，`u4`） | `u32` | 无 | `1i128 << align_bits`（`validate/src/lib.rs:821`）在 `align_bits >= 128` 时 panic（debug）或掩码（release） |
| `Fixup.transform_shift` | 0–63（`plan.rs:859`，`u6`） | `Option<u32>` | 只查「`scale` 时存在」，不查范围 | 后续按 `u32` 移位/缩放时位宽越界 |

3. 由这些字段派生的、可能在 validator 中溢出的算术。H1a 同时把 `fmp-validate`
   里剩余的 `u32` 描述符算术改为 `u64`/`checked_add`（`:963`、`:1274`、`:1284`、
   `:1532`），作为第二道防线；`check_structure` 是**第一道**，必须在 `check` 与
   任何摘要、移位或求和之前运行。

不在 `check_structure` 里重复的：

- JSON 的对象形态、字段存在性、整数域、枚举字符串已在 `bind_document` 里转成
  具体类型（`u64`、`u8`、`Payload` 等），再查一遍没有意义。
- `payload_hex` 的**字节数**是否等于 `fragment.size` 仍归 `check_fragments`
  （`E-LAYOUT-002`）；`bind` 顺序执行两者，并集仍覆盖编码器依赖的全部前提。
- `range_constraint.bits` 是否等于描述符宽度和仍归 `check_fixup_descriptor`
  （`E-FIXUP-001`）；`check_structure` 只保证两边都在解析器允许的域内，使求和
  不会溢出。

诊断码、Pointer 与 detail key 逐字沿用解析器：`format_version` 用
`E-PLAN-001`（`/format_version`，`found`/`supported`），坏十六进制与越界数值用
`E-PLAN-002`（字段自身的 Pointer；`path_type` 为解析器的域标签 `u7`/`u6`/`u4`，
`found_kind` 为 `"integer {value}"`，例如 `"integer 128"`）。这样经 `plan::read`
的合法计划输出不变，只有绕过解析器的可变 DTO 会新增拒绝。

`plan_facts` 的编码规则（写进 `ADR-0127`，因为它定义身份含义）：

版本与域分隔：

- 算法名 `plan-identity/0.1`；哈希输入是 `b"plan-identity/0.1\0" ++ facts`，输出
  `sha256:<64 hex>`。域分隔串与算法名是同一个字面量：换算法必须同时换它，否则
  两套事实会落进同一哈希域。
- `ADR-0127` 必须写全下表；本计划只给初始分配。改 tag 或改字段顺序都是算法变更。

| tag | 原语 | 载荷 |
|---|---|---|
| `0x01` | u8 / bool | 1 字节 |
| `0x02` | u64 | 8 字节小端 |
| `0x03` | i128 | 16 字节小端，二进制补码 |
| `0x04` | str | u64 字节长度 + UTF-8 |
| `0x05` | option-none | 无 |
| `0x06` | option-some | 后跟一个值 |
| `0x07` | vec | u64 元素数 + 元素 |
| `0x08` | struct | 后跟各字段值 |
| `0x09` | enum | u32 变体号（按声明顺序）+ 负载 |

- **结构体字段顺序与枚举变体号是协议，不是实现细节。** Rust 的声明顺序会随重构
  变化，所以 `ADR-0127` 要把每个被覆盖类型的字段列表和每个枚举的变体号写成规范
  性文本；逐字段 mutation 表只证明「都覆盖了」，不证明「编号稳定」。
- **固定测试向量。** `ADR-0127` 至少给出 3 个固定计划的十六进制摘要，其中一个由
  Python 独立实现重算（硬规则 5：两个独立来源）。只由 Rust 实现生成、再用同一
  实现验证的向量不算证据。
- 排除：`Plan.legacy_document`、`Plan.provenance`。其余全部包含，包括 `path`
  （诊断用指针）。包含 `path` 是有意选择：身份只需**至少**覆盖执行事实，多覆盖
  一个确定性字段不产生歧义；若将来证明 `path` 会误伤，仍需新 ADR 才能改。
- **穷尽解构，不用 `..`，枚举不写 `_ =>` 兜底。** 被覆盖的每个结构体都列全字段：

  ```rust
  // 要求：列全，编译器盯着
  let Plan { legacy_document: _, provenance: _, format_version, target, definition,
             output, sections, symbols, instructions, fixups } = plan;
  let Instruction { instruction_id, section_id, offset, form_id, operands,
                    expected_size, expected_digest, path } = instruction;
  // 禁止：`..` 会把新字段静默吞掉，身份于是继续"成功"
  // let Instruction { form_id, operands, .. } = instruction;
  ```

  给 `Instruction`/`Fixup`/`OutputContract` 加字段、给任何被覆盖的枚举加变体时，
  身份代码**编译失败**，而不是等人工核查或等下一次 bug。逐字段 mutation 表是
  第二层证据（证明语义），不承担防遗漏。

  这条是本轮新增的硬约束（§9 的 D7 修订）。代价：结构体一改，`identity.rs` 必然
  出现在 diff 里；这是想要的。

### 3.2 `fmp-validate`

| 项 | 改动 |
|---|---|
| `ValidatedPlan`（新增） | `{ plan: Plan, definition: Arc<Definition>, identity: BindIdentity }`；字段私有、无 `&mut`、无公开构造；唯一构造 `bind(plan: Plan, definition: Arc<Definition>) -> Result<Self, Vec<Diagnostic>>` |
| `bind` | 固定顺序：**先 `plan::check_structure(&plan)`**（拒绝可变 DTO 的结构破坏：`format_version`、`payload_hex`、五个数值边界与描述符派生算术的前提），再**完整定义身份比对**（`namespace`/`version`/`digest` 三项；现 `materialize` 的 `:349-359` 只比 digest，而 `Registry::find` 的 namespace/version 约束不在 `bind` 的输入上，见 D15），再 `check`，最后 `diagnostic::sort`。`check_structure` 在**任何** validator 移位/求和之前完成；前三步都只读计划，不产生编码；新加的结构诊断只能是 `E-PLAN-001`/`E-PLAN-002`，身份错配沿用已注册的 `E-DEF-001`，所以既有负例输出不变 |
| `check_structure` 的使用 | 返回非空即视为绑定失败：`diagnostic::sort` 后原样返回 `Vec<Diagnostic>`，不包装成 `Internal`（它是**调用者提交的 DTO 非法**，不是程序不变量破坏）。它不消耗 `Plan`，调用者修正后可以重试 |
| `check` | 签名不变，内部改走访问器 |
| 描述符算术与逐位循环（H1a 硬化） | (1) 描述符局部算术提升到 `u64`：`:963` 的 `lsb + width`、`:1274` 的重叠比较、`:1284` 的宽度和、`:1532` 的 `end`。(2) fixup 绝对位位置（`offset * 8 + lsb`）改用 `u128`，或 `checked_mul`/`checked_add`：`:1309-1312` 不再直接乘。(3) `check_one_writer` `:1426` 与 `check_fixup_ownership` `:1475` 的逐位循环截断到 `0..form.bits()`，宽度只访问模板内位；`u32::MAX` 宽度也必须有限步返回。(4) 合法输入输出逐字节不变。这一层是第二道防线：即使有路径绕过 `check_structure`，也不会 panic 或无界循环。(5) **入口边界不因第二道防线而改变**：两个 `width = u32::MAX` 是结构非法输入，`bind` 必须由 `check_structure` 以 `E-PLAN-002` 拒绝，不得到达 `check`；H1a 直接调用 `check` 只验证绕过 `bind` 时仍有界返回 |
| `check_fixup_kind` 补 `page` 前提（H1a） | `Transform::Page` 要求 `pc_reference_rule = pcrel_page`（`03_fixup_model.md` §4/§6：`page` 的 `P` 来自 `adrp`）。今天 `check_fixup_kind`（`:1153-1246`）只钉了 `pcrel_lo12`↔`pcrel_hi`、`hi20`↔`none`、`pcrel_hi`→`pcrel_lo12` 和 `scale`↔`transform_shift`，没有 `page` 这一对，所以 A64-P6 把 `fixups[0].pc_reference_rule` 改成 `none` 后仍通过 `check`，直到 `emit` 的 `:725-733` 才以 `internal(...)` 失败。H1a 在 `check_fixup_kind` 加 `E-FIXUP-001`，Pointer 为 `/fixups/i/pc_reference_rule`。不写 AArch64 专用分支：约束按「变换所需的输入」表达 |
| `BindIdentity`（新增） | `{ plan: ParsedPlanIdentity, definition: DefinitionIdentity }`。**没有** implementation 字段，也没有 `PayloadIdentity`：两者都要在产物存在后才知道。`definition` 从**绑定的 `Arc<Definition>`** 取，不从 `plan.definition` 的声明取（D15） |
| `Model` | 不变（只读视图） |

`bind` 的定义身份检查逐字段进行，Pointer 是 `/definition_identity/namespace`、
`/definition_identity/version`、`/definition_identity/digest`。前两条是新诊断，
用已注册的 `E-DEF-001`；digest 那条的 Pointer 与 detail key（`declared`/`actual`/
`reason`）保持现状，所以 `fixtures.rs`/`planner_api.rs` 的 619 负例输出不变。

依赖守卫：`fmp-validate` 的 `[dependencies]` 只允许 `fmp-model`。`ADR-0127` 加一条
可执行的检查（`cargo tree -p fmp-validate --edges normal` 不得出现
`fmp-materialize`），并在评审时人工确认一次；这条检查比口头约定便宜。

`bind` 承接今天的摘要错误，因此负例里那条 `E-DEF-001`
`/definition_identity/digest` 的输出必须逐字节相同。

### 3.3 `fmp-materialize`

| 项 | 改动 |
|---|---|
| `materialize` | 改为 `materialize(&ValidatedPlan) -> Result<Materialization, MaterializationFailure>`，不再接收 `&Plan`/`&Definition`，也**不再重复**摘要比对与 `check` |
| `Materialization`（新增） | `{ artifact: Artifact, receipt: ExecutionReceipt }`。返回 receipt 而不是另设一个「记得调用」的函数：执行过就必须有收据 |
| `ImplementationIdentity`（新增） | `{ name: "fmp-materialize", version: env!("CARGO_PKG_VERSION"), build: option_env!("FMP_BUILD_ID").map(str::to_string) }`。物化器层独有；`fmp-validate` 不引用它 |
| `ExecutionReceipt`（新增） | `{ bind: BindIdentity, implementation: ImplementationIdentity, payload: PayloadIdentity }`，由 `materialize` 在产物生成后组装 |
| `MaterializationFailure`（新增） | 三个变体：`PostEncodeAssertion(Vec<Diagnostic>)`（只在产物字节生成后才能发现）、`Internal(Diagnostic)`（`E-INTERNAL-001`）、`HostFailure(HostFault)`。**不设 `Rejected`**：`bind` 之后不应再有静态拒绝，给一个不可达变体只会造出语义模糊的分支。这条主张以 §4.2 的 `internal(...)` 前提表为前提：H1a 必须把**可由计划触发**的内部故障清零（D16），否则 `Internal` 会变成一条隐藏的拒绝路径 |
| `HostFault`（新增） | 初始只有一个变体 `ImageReservation { requested: usize }`。它描述「这台机器没能满足一次请求」，不描述计划；诊断文本由 CLI 组装，不带可变字节。H4 若加入新的主机相关限制，是新变体，不是新 crate |
| 宿主故障的归属 | **没有 I/O 不等于没有宿主故障。** `emit` 在 `:400` 的 `try_reserve_exact(size)` 就是一次分配，源码注释 `:397-399` 已经写明「a failed reservation here is a host limit, not a plan property」；64 MiB 上限**已经存在**于 `fmp-validate/src/lib.rs:18`（检查在 `:285`），不是 H4 才引入。分配失败取决于主机资源状态，既不是计划属性，也不是 `E-INTERNAL-001`——该码的意思是「不变量被破坏」，而这里不变量成立、只是主机给不出内存。设计 §8.3 明确要求把主机分配失败独立归类为 `HostFailure`。CLI 把 `HostFailure` 映射到 exit 2 的宿主通道（与 `Failure::Io` 同级），而不是 exit 1 |
| 分配失败的测试 | 把 `try_reserve_exact` 抽成 `fn allocate_image(size: usize) -> Result<Vec<u8>, HostFault>`，`emit` 只调用它。测试传入一个在指定 size 上返回 `Err(ImageReservation { .. })` 的同签名函数参数。**不用**全局开关、环境变量或真的耗尽内存：前者是隐藏输入（`INV-05`），后者不稳定且会拖垮 CI。断言 `MaterializationFailure::HostFailure`，并断言它不是 `Internal`、不是诊断数组 |
| `post-encode` 的成员必须先实测 | `emit` 今天还能返回 `E-FIXUP-002`（`:689`、`:833`）、`E-RANGE-003`（`:710`）、`E-FIXUP-003`（`:766`）。它们是「`check` 没拦住」还是「只能在此刻发现」，H1a 必须先跑一遍负例确认，再决定归入哪一个变体；**不猜**。若某条在 `check` 已拒绝，它属于 `bind` 的 `Vec<Diagnostic>`。`emit` 另有 15 处 `internal(...)`（`:384`、`:393`、`:401`、`:425`、`:470`、`:500`、`:566`、`:675`、`:729`、`:748`、`:777`、`:803`、`:809`、`:812`、`:839`）；H1a 为每一处填「由哪项验证保证」的 `ADR-0127` 表格，填不出的就是缺口，先补检查（`:729` 的 `page` 缺 PC reference 已确认是缺口，见 §3.2），只剩确实不可由计划触发的分支归入 `Internal`；`:401` 的分配失败改判 `HostFailure` |
| `fingerprint` | **算法与输出逐字节不变**，唯一输入是 `Plan.legacy_document`；文档注释改为「legacy envelope 身份，按 `ADR-0123` 解释；不覆盖解析后的操作数；不可用于新身份」。`a_legacy_fingerprint_covers_document_fields_the_parser_drops` 钉住它对 `source_trace` 的敏感性 |
| `payload_digest`（新增） | `payload/0.1` 投影的 canonical sha256：`to_json()` 去掉 `materializer_version`。**不是** `canonical_digest(to_json())`——那会把构建身份算进载荷（`ADR-0126`） |
| `lookup`（`:881`） | 走 `definition.forms()` |
| `legacy::materialize`（新增，`#[deprecated]`） | `(&Plan, Arc<Definition>)`：内部 `bind` 后调用新 `materialize`，只返回 `artifact`、丢掉 receipt。它**不是源码兼容入口**：路径和参数类型都变了；它的作用是保留一个「两参数形状且无法绕过检查」的过渡函数（§5） |

### 3.4 `fmp-cli`

`main.rs:100-110` 改为 `Registry::load_dir` → `plan::read` → `Registry::find`
（得 `Arc<Definition>`）→ `bind` → `materialize`。返回的 `Materialization` 里
CLI 只打印 `artifact`；`receipt` H1 不落盘（H3 建 run receipt 时才决定协议）。

失败出口按**谁错了**分流，不按「诊断长什么样」分流：

| 失败 | 含义 | 出口 |
|---|---|---|
| `bind` 返回诊断 | 计划或定义非法（含 `check_structure` 的 DTO 结构破坏） | exit 1，完整诊断数组到 stderr |
| `MaterializationFailure::PostEncodeAssertion` | 计划在编码后未满足自己的断言（`E-SIZE-001`/`E-BYTE-001` 等） | exit 1，诊断数组到 stderr |
| `MaterializationFailure::Internal` | **实现不变量被破坏**（`E-INTERNAL-001`），不是用户输入错误 | exit 2，走独立的内部故障通道：stderr 先打一行 `internal fault:` 再打完整诊断，**不**复用 `Failure::Rejected` 的退出路径 |
| `MaterializationFailure::HostFailure` | 主机资源失败（分配/映像大小不适用） | exit 2，宿主通道（与 `Failure::Io` 并列） |

`Internal` 单独成一支的理由：冻结错误规范对 `E-INTERNAL-001` 的定义是「内部
不变量违反（bug），永不用于用户输入」。把它映射成 exit 1 会让同一个「程序坏了」
在 CLI 上看起来像「用户提交了非法计划」，也破坏 `0/1/2` 三分法的可依赖含义。
实现上给 `Failure` 加一个 `Internal(Diagnostic)` 变体，并在 `main` 里把
`Failure::{Rejected, Internal}` 分开匹配；`Internal` 的 2 不是 `Io` 的 2，
stderr 文本不同，CI 可以区分。

为让出口本身可测，`main` 的「失败 → 退出码」抽成纯函数
`fn exit_code(failure: &Failure) -> u8`，单测三类；端到端测试只覆盖 `bind` 拒绝
与 usage，不为了制造一次真的内部故障而注入 panic。

### 3.5 测试改造

| 文件 | 改动 |
|---|---|
| `he1_identity_characterization.rs` | H1a 改定义可变性那条（见 §4.1）：字段私有化后它无法编译，改成 `compile_fail` + 「改文档后重载得到新摘要」。H1b **不翻转** `a_parsed_operand_can_change_under_a_stable_fingerprint`：它证明旧指纹仍不变，这个行为必须保留；新身份由 `a_legacy_fingerprint_is_not_a_trusted_cache_key` 与 `a_mutated_operand_changes_the_plan_identity` 覆盖。其余 5 条保留（H3 关 2 条缺口、1 条 legacy 约束、2 条对照），文件头加「所属阶段」表；深层 JSON 属 H4，证据是 Python 探针，不是该文件的测试 |
| `fixtures.rs`、`determinism.rs`、`planner_api.rs` | `materialize` 改走 `bind`；`find` 返回 `Arc` 后约 8 处加 `&` |
| `fmp-materialize` 单测 | 5 处 `materialize` + 4 处 `fingerprint` 按新签名改 |

## 4. 测试计划

### 4.1 编译期（`HE-T02`/`HE-T04`，「API 不可表达」）

用 `compile_fail` doctest，零新依赖；**每条断言放在能正常引用被测符号的 crate 里**，
并配一个使用相同导入路径的正向可编译对照：

| 位置 | 断言 | 正向对照 |
|---|---|---|
| `fmp-model` crate 文档（H1a） | 外部 crate 不能写 `definition.forms`，不能 `Definition { .. }` | 同路径读取 `namespace`/`version`/`digest` 的示例必须编译 |
| `fmp-validate` crate 文档（H1b） | 不能 `ValidatedPlan { .. }`，不能 `Clone` | 同路径调用 `bind`/访问只读方法的示例必须编译 |
| `fmp-materialize` crate 文档（H1b） | `materialize` 只接受一个 `&ValidatedPlan` 参数，不能「用 A 验证、传 B 执行」 | `use fmp_materialize::materialize;` 后以单个 `&ValidatedPlan` 调用的示例必须编译 |

`materialize` 的签名负测**不能**放在 `fmp-validate` 的文档测试里：`fmp-validate`
不依赖 `fmp-materialize`，那里的 `use fmp_materialize::…` 会先因找不到 crate 而失败；
`compile_fail` 只要求失败，于是签名退化回不安全的两参数形式时测试仍会绿。放在
`fmp-materialize` 自己的文档测试里，导入与签名同属一个 crate，失败原因才是签名。
限制仍然成立：`compile_fail` 只证明「编译失败」，不证明失败**原因**；正向对照保证
导入路径本身可用，人工核对只作为补充，不替代这条结构。

H1a 的定义可变性改造具体是：把现在直接写 `definition.digest` / `forms` /
`template` 的那条测试拆成两半——编译期 `compile_fail` 证明字段不可写；运行期
`a_definition_edit_reloads_to_a_new_digest` 改定义**文档字节**后重新 `read`，
断言摘要变了、且旧计划按摘要被拒。这样既保留了「摘要覆盖内容」的实测，又不依赖
被封闭的字段。

### 4.2 运行期

阶段边界按**被测 API** 划分，不按反例内容划分：H1a 的负例直接调用
`plan::check_structure`（或 `fmp_validate::check`），**不调用 `bind`**，因为 `bind`
要到 H1b 才存在；H1b 再经 `bind` 测一次端到端拒绝。这样 H1a 可以独立全绿，不需要
为了「测试已落地」提前引入半成品 `bind`。

**输入可以复用，但预期拒绝阶段跟随入口。** `bind` 先跑 `check_structure`；结构非法
的输入不会到达 `check`，也不得为了让 H1b 按表通过而放宽第一道检查。只有类型合法、
语义不合法的输入（极大 `offset`、`page` 缺 PC reference）才由 `check` 拒绝。

| 输入 | H1a：直接调用 | H1b：经 `bind` |
|---|---|---|
| 奇数长度或非十六进制 `payload_hex` | `check_structure` → `E-PLAN-002` | `E-PLAN-002`，不到 `check` |
| `align_bits = 128`、`transform_shift = 128`、`lsb`/`width`/`bits` 越界 | `check_structure` → `E-PLAN-002` | `E-PLAN-002`，不到 `check` |
| 两个 `field_descriptor.width = u32::MAX` | `check` 有界返回诊断（第二道防线） | `check_structure` → `E-PLAN-002`，不到 `check` |
| `offset = u64::MAX`（类型合法） | `check` 返回诊断 | `check` 返回同一诊断 |
| `page` + `pc_reference_rule = none` | `check` → `E-FIXUP-001` | `check` → `E-FIXUP-001` |

若将来需要验证「各字段合法、但描述符总宽与 form 不匹配」的语义拒绝，应另建一个
反例；不要复用 `u32::MAX` 这个结构非法案例，也不要把它的预期写成「由 `check`
拒绝」。

`bind` 的身份三元组比对（D15）属于 H1b 的绑定入口；`page` 的 PC reference 前提与
`internal(...)` 前提表（D16）属于 H1a，因为前者要在 `check` 里拒绝、后者决定哪些
分支还能留在 `Internal`。两边都用既有正例的内存变体，不改冻结夹具。

| 测试（拟名） | 断言 | 对应 |
|---|---|---|
| `a_definition_reloads_to_the_same_digest` | 同一字节两次加载摘要相同；换行/键序不同但 canonical 相同则摘要相同 | `HE-T03` |
| `a_tampered_definition_document_is_rejected_by_bind` | 改模板保留计划中的旧摘要 → `E-DEF-001` `/definition_identity/digest` | `HE-T03` |
| `a_mutated_operand_changes_the_plan_identity` | H1b：改 `payload.reg` → `ParsedPlanIdentity` 变；同一计划的旧 `fingerprint` **仍不变**（legacy 行为，见 `a_legacy_fingerprint_covers_document_fields_the_parser_drops`），断言新身份的变化不依赖旧指纹变化 | `HE-T02`/`HE-T04`、D3/D12、第六轮 P1 |
| `a_data_fragment_with_odd_length_hex_is_rejected_by_check_structure` | H1a 直接调用 `check_structure`：取 X86-P71 的四字节数据片段，内存中把 `payload_hex` 改为 `"aabbccdd0"`（长度 9，`9 / 2 == 4`，所以旧 `check_fragments` 不会拒绝）→ 在该 fragment 的 `/payload_hex` 返回 `E-PLAN-002`；断言物化器未被调用、没有 panic | D13、第四轮 P1 |
| `a_data_fragment_with_non_hex_payload_is_rejected_by_check_structure` | H1a 直接调用 `check_structure`：同样片段改为 `"zzzzzzzz"`（长度与字节数都合法，`decode_hex` 的 `digit()` 会把 `z` 当 0）→ 返回 `E-PLAN-002`；断言既没有产物，也没有静默替换的字节 | D13、第四轮 P1 |
| `an_alignment_outside_the_parser_bound_is_rejected_by_check_structure` | H1a 直接调用 `check_structure`：取 `A64-P4-beq-btype`（其 fixup 带 `transform_shift`），内存中把 `fixups[0].range_constraint.align_bits` 改为 128 → 在 `/fixups/0/range_constraint/align_bits` 返回 `E-PLAN-002`（`path_type: "u4"`，`found_kind: "integer 128"`）；断言 `1i128 << align_bits` 未执行、没有 panic | D13、第五轮 P1 |
| `a_transform_shift_outside_the_parser_bound_is_rejected_by_check_structure` | H1a 直接调用 `check_structure`：同一计划把 `fixups[0].transform_shift` 改为 `Some(128)` → 在 `/fixups/0/transform_shift` 返回 `E-PLAN-002`（`path_type: "u6"`）；断言不进入缩放路径 | D13、第五轮 P1 |
| `a_field_range_outside_the_parser_bound_is_rejected_by_check_structure` | H1a 直接调用 `check_structure`：依次设置 `field_descriptor[0].lsb = 128`、`.width = 0`、`.width = 65`、`range_constraint.bits = 0`、`.bits = 65` → 每项都在对应 Pointer 返回 `E-PLAN-002`；断言这些计划在到达 `check_fixup_descriptor` 的求和/循环前就被拒绝 | D13、第五轮 P1 |
| `a_descriptor_width_sum_cannot_overflow` | H1a 在 `fmp-validate` 内直接调用 `check`（不经 `bind`）：把两个 `field_descriptor.width` 设为 `u32::MAX` → 断言旧的 `u32` 宽度求和与 `field.lsb + field.width` 不再 panic，且函数在有限步内返回诊断（逐位访问被 `form.bits()` 截断，不是遍历 40 亿位）。这是第二道防线；同一输入经 `bind` 时由 `check_structure` 拒绝（见上表），本测试**不**主张它能到达 `check` | D13/D14、第五轮 P1、第六轮 P1 |
| `two_huge_fixup_offsets_do_not_overflow` | H1a 从**合法解析的 JSON** 计划进入 `fmp_validate::check`（不是手改 DTO）：同一 section 的两个 fixup，`offset` 分别设为 `u64::MAX` 与 `u64::MAX - 8` → `check` 在有限步内返回诊断（site 不匹配任何 instruction），debug 与 release 都不 panic；断言 `offset * 8` 要么用 `u128`，要么用 checked 乘法，溢出时不会进入比较 | D14、第六轮 P1 |
| `a_page_transform_without_a_page_pc_rule_is_rejected` | H1a 直接调用 `check`：取 A64-P6（首个 fixup 是 `page` + `pcrel_page`），把 `fixups[0].pc_reference_rule` 改为 `none`、其余不变 → 在 `/fixups/0/pc_reference_rule` 返回 `E-FIXUP-001`；断言不返回 `E-INTERNAL-001`、物化器未被调用 | D16、第七轮 P2 |
| `every_internal_branch_names_its_static_precondition` | 不是运行测试：`ADR-0127` 列出 `emit` 的 15 处 `internal(...)` 与各自的保证者；H1a 提交时必须逐项填完，任一可由合法计划触发且无检查的分支都要先补检查 | D16、第七轮 P2 |
| `the_negatives_are_rejected_at_the_stage_their_boundary_requires` | H1b 按上表把同一批输入各跑一次 `bind`：六条结构非法输入（两条 hex、对齐、`transform_shift`、字段边界、`u32::MAX` 宽度和）全部由 `check_structure` 在对应 Pointer 返回 `E-PLAN-002`，**不进入 `check`**；极大 `offset` 与 `page` 前提由 `check` 拒绝。物化器均未被调用；预期阶段按上表逐项给出，不沿用 H1a 直接调用时的那一行 | D13/D14/D16、第六轮与第七轮 P1、第八轮 P1 |
| `a_validated_plan_is_the_only_materialize_input` | H1b：`fmp-materialize` 的正向可编译对照——`use fmp_materialize::materialize;` 后以单个 `&ValidatedPlan` 调用成功编译；同一 crate 的 `compile_fail` 文档测试断言「`Plan` + `Definition` 两参数」不再可调用。两者使用同一导入路径，排除「导入本身就失败」的假通过 | `HE-T04`、第八轮 P2 |
| `a_declared_namespace_must_match_the_bound_definition` | H1b：取正例，只把 `definition.namespace` 改成另一个字符串（`version`/`digest` 不动），传入真实定义 → `bind` 在 `/definition_identity/namespace` 返回 `E-DEF-001`；物化器未被调用 | D15、第七轮 P1 |
| `a_declared_version_must_match_the_bound_definition` | H1b：只改 `definition.version`（`namespace`/`digest` 不动）→ 在 `/definition_identity/version` 返回 `E-DEF-001`；同时保留「只改 digest」那条既有负例的输出，证明摘要失配的诊断未被新检查挤掉 | D15、第七轮 P1 |
| `a_definition_identity_mismatch_is_rejected_by_the_legacy_facade` | H1b：同一错配经 `legacy::materialize` 提交 → 与 `bind` 相同的诊断与 Pointer；二参入口不能绕过身份比对 | D15、第七轮 P1 |
| `plan_identity_covers_every_parsed_field` | 逐字段 mutation 表（section/instruction/operand/modifier/fixup/symbol/output/target），每项都必须改变身份 | 硬规则 2 的逐字段反例 |
| `plan_identity_ignores_provenance` | 只改 `provenance` → 身份不变（与 legacy `fingerprint` 的排除一致） | §12 |
| `a_definition_edit_reloads_to_a_new_digest` | 改定义文档字节后重载：`digest` 变；旧计划按旧摘要被 `bind` 拒绝。替代 H1a 之后无法编译的字段直改测试 | `HE-T03` |
| `plan_identity_ignores_the_legacy_document` | 只改 `source_trace` → `ParsedPlanIdentity` **不变**、旧 `fingerprint` **变**；两者是不同主张，不能互相替代 | D12 |
| `a_legacy_fingerprint_is_not_a_trusted_cache_key` | 改一个解析后操作数：旧 `fingerprint` 不变，但 `ParsedPlanIdentity` 与 `ExecutionReceipt` 变。验收要求「旧行为保持 + 新身份随执行事实变化」，**不**要求把旧指纹测试翻成拒绝 | D3/D12、第六轮 P1 |
| `a_bind_identity_does_not_identify_the_legacy_artifact` | 计划 A 与「A + `source_trace`」：两个 `BindIdentity` 字段都相同，`fingerprint` 与 `payload_digest` 都不同；完整收据能区分 | D3、D12 |
| `an_image_reservation_failure_is_a_host_failure` | 注入 `allocate_image` 失败 → `MaterializationFailure::HostFailure`，不是 `Internal`、不是诊断数组；同一计划在够内存的主机上仍成功 | D4、`§8.3` |
| `a_legacy_fingerprint_covers_document_fields_the_parser_drops` | H0 的约束测试，H1 之后仍然通过（改名 `legacy_document` 不改变行为） | `HE-AC-10`、D12 |
| `receipt_names_the_build_that_ran` | `receipt.implementation` 来自物化器的编译期常量；`FMP_BUILD_ID` 缺失时记 `build: None` 且不宣称满足 `HE-T20` | `HE-T20`、D9 |
| `bind_reports_only_plan_and_definition` | `ValidatedPlan` 的 `BindIdentity` 里没有 implementation 字段（编译期 + 依赖方向） | D11 |
| `payload_digest_follows_the_bytes` | 改一个操作数 → 字节变 → 载荷身份变；再改 `materializer_version` → 载荷身份**不变**、envelope 变 | `HE-T20`、`ADR-0126` |
| `legacy_facade_rejects_a_digest_mismatch` | 二参 facade 同样拒绝（H0 的对照测试迁到这里） | `HE-T04` |
| `bind_reports_the_definition_it_bound` | `identity.definition.digest` 等于实际执行定义的摘要 | `HE-AC-06` |
| `the_exit_code_separates_rejection_from_internal_fault` | `exit_code` 纯函数：`Rejected`/`PostEncodeAssertion` → 1，`Internal`/`HostFailure`/`Io`/`Usage` → 2；断言 `Internal` 不落到 `Rejected` 分支 | 第四轮 P2、§3.4 |

### 4.3 金样与既有门禁

先说清现有测试**实际**证明了什么，再说 H1 加了什么。

`fixtures.rs::negatives_produce_exactly_the_registered_diagnostics`（`:220-254`）
和 `planner_api.rs::negatives_reject_at_the_same_code_path_and_detail_keys`
（`:247`）比较的是 **排序后的三元组** `(error code, JSON Pointer, detail key 名字
集合)`。它们**不**比较 detail 的**值**、完整消息文本或原始诊断顺序。因此：

| 门禁 | 实际保证 |
|---|---|
| `python tools/he1_baseline.py --check research/he1/compatibility-results.json` | 128 个产物**载荷**（`payload/0.1`）、104 个定义摘要、计数、oracle 状态不变；记录快照的 `payload_root` **和** `definitions_root` 还必须等于 `research/he1/baseline-anchor.json`，且每个 fresh artifact 的必需 envelope 成员必须存在。`envelope` 只在实现收据相同时才比较；结构错误、内容与声明摘要不符、派生计数不一致都先于物化以 exit 2 拒绝 |
| `python tools/test_he1_baseline.py` | 比较器自检：payload 变化必失败、实现收据不同时仍比较 payload、结构或计数变化必失败、改 `payload.bytes_hex` 不改摘要 / 改 envelope 摘要 / `definitions.count` 与文档数不符 / `by_isa` 和与语料计数不符 / oracle 和与正例数不符都是故障、删除 `envelope` 是故障、锚点不符（含 `definitions_root`）是差异、缺 `definitions_root` 的锚点是故障、fresh artifact 缺 `materializer_version` 等必需成员是故障、裸调用不能重录、失败的工具链子进程记为 `unavailable` 而不是抛异常。不依赖真实二进制，因此 CI 里先于基线比较运行 |
| `cargo test --workspace` 的 `fixtures`/`planner_api` | 619 个负例的 **code + Pointer + detail-key 集合**相等。detail 值与顺序**不在**门禁内 |
| `determinism.rs` | 每 ISA 一条 **envelope** 摘要（`materializer_version` 在内），跨三主机 |
| `fixtures.rs` 的 Level-1 用例 | envelope 形状未被新身份污染 |
| `tools/oracle/rerun.py` | 122 条仍可复现 |

H1 只对「本次错误边界迁移实际触及」的负例增加值级快照，**集合由 H1a 的实测决定，
不预先写死条数**。源码推导出的阶段分布如下；实测与表不符时以实测为准修正表，而不是
让表反过来约束测量：

| 用例类别 | 现在在哪一步失败（源码推导） | H1 要验证的 |
|---|---|---|
| `expected_size` 与 form 不符（N05、N05b） | `validate` 的 `check_instructions` 已拒绝（`:655-668`），不会进入 `emit` | 属于 `bind` 的拒绝；断言诊断三元组不变，**不**算编码后失败 |
| `expected_digest` 不符（N13） | 只在 `emit`（`:597-609`）产生 `E-BYTE-001` | 值级快照（`declared`/`actual`） |
| fixup 变换前对齐（N20） | 只在 `apply`（`:707-716`）产生 `E-RANGE-003`；`validate` 只查操作数对齐（`:819-832`） | 值级快照（`required_align`/`value`） |
| fixup 变换后范围（N04b、N04f） | 只在 `apply`（`:752-771`）产生 `E-FIXUP-003` | 值级快照（`min`/`max`/`value`） |
| 可由输入触发的 `Internal` | `page` + `none` 已确认（§3.2）；其余 `internal(...)` 由 H1a 审计 | 先补静态前提；只有确实不可由计划触发的才保留 `Internal` |

值级快照的名单和条数写进 `ADR-0127`，与实测阶段一一对应。其余负例继续用三元组
门禁；不整体加，是因为 619 条全量值级快照会把每次合法的消息措辞调整都变成门禁失败，
收益与维护成本不成比例。

如果将来要宣称「完整诊断数组逐字节不变」，必须先把门禁扩大到全部 619 条；在那
之前，计划和报告都不得使用这个说法。

## 5. 兼容性影响

先按**兼容类**分开写，因为「不变」在这几层含义不同（`ADR-0126` 的教训）：

| 层 | 结论 |
|---|---|
| FMP 文档面（`fmp/0.1` 计划、`fmp-def/0.1|0.2` 定义） | **格式不变**。既有合法输入的机器载荷保持不变；此前错误接受、未明确拒绝或以内部故障结束的输入，允许按既有规范收紧处理。新增拒绝、诊断变化和失败阶段迁移必须记录在本节的兼容性差异行与 §4.3 的阶段表中 |
| 128 个正例的**载荷** | **不变**（`payload_root` 不变）。这是 `HE-AC-10` 的判据 |
| Artifact **envelope** | 形状不变、不加字段；`materializer_version` 仍是 envelope 收据，可变 |
| 旧 `fingerprint` | 算法与输出不变，输入仍是 `Plan.legacy_document`（只读、legacy-only）；文档标注 legacy，**不**作为新可信身份。它是 Artifact 字段，所以仍影响 `payload_digest` |
| `BindIdentity` 的语义 | 只是「计划事实 + 定义摘要」的绑定，**不是**完整 legacy Artifact 的重放键：多一个 `source_trace`，两个绑定字段都不变，`payload_digest` 却变。完整身份用 `ExecutionReceipt` |
| **Rust 库 API** | **允许迁移**。`fmp_materialize::materialize` 的路径与参数类型都变；`legacy::materialize` 只是「两参数形状且无法绕过检查」的过渡函数，**不是源码兼容入口**。仓库外的调用者需要改代码 |
| 「旧入口」指什么 | `fmp/0.1` 文档面、产物 envelope 与 `fmp` CLI 行为。**不是** Rust 库函数签名；`ADR-0125` 决策 6 的 adapter 只承诺前者 |
| 619 个负例诊断 | code + Pointer + detail-key **集合**不变；值级快照只加在 H1a 实测确认的编码后失败用例上（§4.3） |
| 定义身份 | `bind` 比较 `namespace`/`version`/`digest` 三项；`Registry::find` 的「namespace + version → 唯一 digest」规则由绑定入口承担，CLI 与公开库入口接受规则一致（D15） |
| 定义文件与形态 | 不改；`definitions/**` 一个字节不动（H0 锚点的 `definitions_root` 不变） |
| 错误码 | 不新增。`E-DEF-001`/`E-SIZE-001`/`E-BYTE-001`/`E-INTERNAL-001` 均已注册 |
| 宿主故障 | 分配失败由 `MaterializationFailure::HostFailure(HostFault)` 表达，CLI 映射为 exit 2 的宿主通道（与 `Failure::Io` 同级）。64 MiB 上限已在 `fmp-validate`，不新增限制；H4 若加新的主机相关限制，是新的 `HostFault` 变体 |
| 内部故障 | `MaterializationFailure::Internal`（`E-INTERNAL-001`）映射为 exit 2 的独立内部故障通道，stderr 先打 `internal fault:`；**不**与 `bind` 拒绝、`PostEncodeAssertion` 共用 exit 1，避免把实现缺陷说成用户计划错误 |
| 计数 | 不改 `STATUS.md` 的 v0 计数；测试数会变（7 个 characterization 里 1 个改为 `compile_fail` + 重载测试，其余保留；H1b 新增身份测试，**不**翻转旧指纹测试） |
| 依赖方向 | 不变：`validate → model`，`materialize → validate + model` |

「原型阶段允许 API 迁移」是本轮的明确选择（§9 D5）；如果评审要求旧库调用点源码
兼容，则必须重新设计新旧入口的命名、参数与绑定生命周期，而不是把 facade 描述成
「原入口不变」。

## 6. 提交拆分与门禁

| 提交 | 内容 | 每步必过 |
|---|---|---|
| H1a | `Definition` 封闭 + `Registry` 用 `Arc` + `identity` 模块 + `Plan.legacy_document` 改名 + 逐字段 mutation 测试 + 定义可变性测试改造（`compile_fail` + 改文档重载）+ `plan::check_structure`（`format_version`、`payload_hex`、五个数值边界）与八条**直接调用 `check_structure`/`check`** 的负例（两条 X86-P71、对齐/`transform_shift`/字段边界、`u32::MAX` 宽度和、两个极大 offset、`page` 前提）+ `check_fixup_kind` 的 `page ⇒ pcrel_page` 检查 + `internal(...)` 前提表与寄存器宽度风险复现 + validator 位位置算术与逐位循环硬化（`u128`/`u64`/`checked_*`、截断到 `form.bits()`）+ fixup 错误归属实测 | `fmt`、`test --workspace`、`baseline --check`、`check_ids` |
| H1b | `ValidatedPlan` + `bind`（第一步调用 `check_structure`，随后比对 `namespace`/`version`/`digest`）+ `BindIdentity` + 新 `materialize`/`Materialization`/`ExecutionReceipt` + `MaterializationFailure`/`HostFault`/`allocate_image` + CLI 失败分流/`exit_code` + facade + 调用点迁移 + **同一批八条结构/前提输入经 `bind` 的端到端拒绝**（结构非法者停在 `check_structure`，只有类型合法者到达 `check`）+ namespace/version 错配与 facade 测试 + 新身份测试（旧指纹测试保持，不翻转） | 同上 + `oracle` + `check_definition` |
| 同 PR | `docs/adr/0127-*.md` + 本文件改为「已采纳」+ `research/he1/H1-report.md` | `check_ids`、`git diff --cached --check` |

一个 PR 两个提交：`ADR-0125` 决策 1 要求 H1 是一个阶段，§13.1 要求阶段内可回归。
H1a 必须先全绿再开 H1b：八条结构/算术/前提反例在 H1a 就落地，直接测
`check_structure`/`check`，**不调用尚不存在的 `bind`**；H1b 的 `bind` 只负责接入，
再把同一批输入经 `bind` 测一次端到端拒绝，并按 §4.2 的表核对该入口的拒绝阶段
（结构非法者不会到达 `check`），最后补 `namespace`/`version` 的身份错配。
fixup 错误归属与 `internal(...)` 前提表也在 H1a 实测后，才冻结
`MaterializationFailure` 的成员（§10）。

## 7. 风险与回滚

| 风险 | 处置 |
|---|---|
| 身份算法写错，导致不同事实同身份 | 逐字段 mutation 表；`plan_facts` 是纯函数，可单测 |
| 给结构体加字段后忘记同步身份，漏洞复发 | **编译期**：穷尽解构、不用 `..`、枚举不写 `_ =>`（§3.1） |
| `plan_facts` 与 `bind` 漂移成两个权威来源 | 只从 `Plan` 读数，不读 `legacy_document`；`legacy_document` 只有一个读者（旧 `fingerprint`），并由 H0 约束测试钉住。注意旧 `fingerprint` 仍是 Artifact 字段，所以 `legacy_document` 会经它影响 `payload_digest`——这不是「新身份读了旧文档」 |
| 身份编码的字段顺序随重构变化，旧身份无法重算 | `ADR-0127` 把字段顺序与 tag 写成协议文本，附 3 个固定向量（其中一个用 Python 独立重算） |
| 诊断顺序变化，负例面扩大 | 619 个负例的 code/Pointer/detail-key 集合门禁；`bind` 内顺序照抄现实现；编码后失败的值级快照按 H1a 实测的阶段选择（§4.3） |
| `Arc` 改动扩散 | 编译器引导，约 8 处；`Registry` 仍保持确定性顺序 |
| 可变 DTO 绕过解析器规则，把非法 hex 或越界数值送进 validator/materializer | `bind` 先跑 `check_structure`：X86-P71 的奇数长度与非十六进制两条负例；`align_bits=128`、`transform_shift=128`、`lsb/width/bits` 越界与 `u32::MAX` 宽度求和四条负例；`fmp-validate` 的描述符算术改成 `u64`/`checked_add` 作第二道防线；`decode_hex` 保持现状，不改成「猜一个字节」 |
| 合法解析范围内的数值在 validator 内溢出或无界循环 | `offset` 是解析器允许的完整 `u64`：`check_fixup_overlap` 的 `offset * 8` 可溢出，`check_one_writer` 会按 `u32::MAX` 宽度逐位遍历。H1a 用 `u128`/`checked_*` 计算绝对位位置，并把逐位循环截断到 `form.bits()`；`two_huge_fixup_offsets_do_not_overflow` 从合法 JSON 进入 `check`，debug/release 各跑一次 |
| 计划声明的 namespace/version 与传入定义不一致 | `bind` 比较三项（D15）；H1b 的 namespace、version 错配与 facade 测试；`BindIdentity.definition` 取自实际绑定的定义，不取计划声明 |
| 合法计划触发 `Internal`（`page` + `none`） | `check_fixup_kind` 补 `page ⇒ pcrel_page`（D16）；H1a 直接测 `check`，H1b 测 `bind`，`ADR-0127` 记下诊断码与 Pointer；其余 `internal(...)` 由 H1a 的前提表覆盖 |
| 定义输入让寄存器宽度检查越界移位 | `reg_number` 槽位不允许 `range`（`definition.rs:487-499`），总宽只由 placements 之和决定（单个 ≤64，个数无上限）；`validate` 的 `:775` 用 `1u64 << field_bits`，64..127 在 debug 溢出。H1a 先复现，并选择「比较改用 `u128`」而不约束加载；H1a 评审又发现编码端 `write_field` 仍对整个字段做 `i128` 掩码与移位：127 位 debug panic，192 位 release 成功但把值也写进第一个 placement。现已改为逐 placement 从低 128 位提取、高位按符号扩展，`he1_wide_register.rs` 用非零寄存器覆盖 64/127/128/192 位并在 debug/release 断言实际字节；**不**把「字段已私有化」扩大解释为「加载器接受的定义都已被证明安全」 |
| `Internal` 被误分类成用户计划错误 | `Failure::Internal` 独立变体 + `exit_code` 单测；exit 1 只留给 `Rejected` 与 `PostEncodeAssertion` |
| 有人继续用二参入口绕过 | facade 内部就是 `bind`；两条测试：摘要不符仍被拒、namespace/version 错配同样被拒（D15） |
| envelope 意外新增字段 | Level-1 夹具 + `payload_root` |
| `BindIdentity` 被当成完整产物的缓存/重放键 | §2.2 写明它不含 payload；`a_bind_identity_does_not_identify_the_legacy_artifact` 用 `source_trace` 实测 |
| 分配失败被写成 `E-INTERNAL-001` 或计划拒绝 | `MaterializationFailure::HostFailure` + 注入式 `allocate_image` 测试（§3.3）；`E-INTERNAL-001` 只留给不变量破坏 |
| 载荷身份混入构建信息（重复 `ADR-0126` 的 bug） | `payload_digest` 只能读 `payload/0.1` 投影；单测证明改 `materializer_version` 不改变它 |

回滚：整个 PR 可整体撤回。H1 不动定义文件、不动协议版本，没有需要迁移的持久
状态。

## 8. 明确不在 H1 内

- bundle/package 格式、`fmp-definition` crate（H2）。
- `fmp/0.2`、命名空间化的 ISA 身份、零操作数 form（H3）。
- `load_dir` 全目录扫描、`check_form_id` 白名单（H3）。
- 解析深度上限、包格式与新增包资源的限制（H4）。64 MiB 映像上限**已经存在**
  （`MAX_IMAGE_BYTES`，`fmp-validate/src/lib.rs:18`，检查在 `:285`）；H4 只验证并
  补齐既有资源限制，不重复引入。
- fixup profile 与新原语（H4）。
- 任何指令覆盖扩张。

## 9. 待审决策

`D3`/`D4`/`D5`/`D7` 按第一轮评审修订，`D8`–`D10` 同轮新增；`D11`–`D12` 是
第二轮评审（`ebddbdb`）后新增；`D4` 在第三轮评审（`ccdc7a3`）后再次修订，加回
`HostFailure`；`D13` 是第四轮评审（`66d5e14`）后新增，封闭「公开可变 DTO 被当成
已解析合法输入」的缺口；第五轮评审（`cb1e4ad`）把其范围从两个字符串规则扩到
全部五个解析器数值边界；第六轮评审（`fe369ef`）新增 `D14`，封闭 `offset * 8`
溢出与无界逐位循环，并把 H1a/H1b 的测试边界按被测 API 拆开；第七轮评审
（`d5c0ca7`）新增 `D15`（`bind` 比对完整定义身份）与 `D16`（`page` 的 PC
reference 前提，以及 `internal(...)` 分支的静态前提审计）。

| # | 问题 | 决定（推荐） | 状态 | 备选与代价 |
|---|---|---|---|---|
| D1 | `Definition` 就地封闭还是改名 `VerifiedDefinition` | **就地封闭**；H2 由 `fmp-definition` 的 `VerifiedBundle` 包装 | 接受 | 现在改名会让 ~40 处调用点动一次，H2 再动一次 |
| D2 | `Registry::find` 返回 `Arc<Definition>` | **是**；`Arc` 只给共享所有权，不给内部可变性 | 接受 | 返回 `&Definition` 则需要另一条「取所有权」的路径，等于两个入口 |
| D3 | 身份覆盖「除 `provenance` 外全部解析字段」 | **是（含 `path`），但改名并限定**：类型为 `ParsedPlanIdentity`，文档称「解析快照身份」，算法名 `plan-identity/0.1`。不称「机器语义身份」，也**不是完整 legacy Artifact 的重放键**（见 D12） | 有条件接受 → 已修订 | 只覆盖影响字节的字段：身份更窄，逐字段反例更难写清；且会让「解析事实变了、字节没变」变成不可检测 |
| D4 | 物化失败分类 | **三个变体**：`PostEncodeAssertion`、`Internal`、`HostFailure(HostFault)`。**删掉 `Rejected`**（`bind` 之后不应可达）；**保留 `HostFailure`**，因为 `emit` 的 `try_reserve_exact`（`:400`）是主机资源失败，设计 §8.3 要求单独分类。哪些错误码落进 `PostEncodeAssertion` 由 H1a **实测**决定 | 第二轮修订 → **第三轮再修订** | 把分配失败并进 `Internal`：`E-INTERNAL-001` 会变成「主机内存不够」，而计划的不变量并没有被破坏；并进 `Rejected` 会让同一份计划在不同主机上得到不同的「计划错误」 |
| D5 | 旧入口的兼容承诺 | **保留一个阶段的过渡函数**，`#[deprecated]`，内部走 `bind`；同时**明确声明**不承诺 Rust 源码兼容，只承诺 FMP 文档面与产物兼容 | 需要修订 → 已修订 | 真要源码兼容就得重新设计命名/参数/生命周期，成本高于本阶段收益 |
| D6 | 旧 `fingerprint` 是否改算法 | **不改**，标注 legacy，新身份不复用它 | 接受 | 改算法会移动 128 个产物 → 违反 `HE-AC-10` |
| D7 | `plan_facts` 手写还是复用 `fmp-plan` 序列化 | **手写**在 `fmp-model`，并加**编译期穷尽性约束**（不用 `..`、枚举无 `_ =>`）与算法版本名 | 有条件接受 → 已修订 | 复用 `fmp-plan` 的第二套 DTO（`fmp-plan/src/lib.rs:155-280`）会把第二个权威来源带进执行路径 |
| D8 | 身份是否分层 | **三层**：`payload`（比较）、`envelope`（同收据才比较）、`implementation`（只记录），各自带版本名。`payload_digest` 必须去掉 `materializer_version` | 新增（设计 §7.2 本就如此分层） | 单一摘要：构建版本一改就误报载荷漂移，`ADR-0126` 已实测 |
| D9 | `ImplementationIdentity` 从哪来 | 由**物化器构建层**提供 `{name, version, build}`，`build` 取 `option_env!("FMP_BUILD_ID")`；取不到记 `None`，且不宣称满足 `HE-T20` | 新增 | 用 `fmp-model` 的 `CARGO_PKG_*`：名字与版本都不指向物化器 |
| D10 | 负例门禁的声明范围 | 619 条只保证 **code + Pointer + detail-key 集合**；额外对 H1a 实测确认的编码后失败用例加**值级**快照（§4.3） | 新增 | 619 条全量值级快照：把合法的措辞调整变成门禁失败，维护成本不成比例 |
| D11 | 身份归属与依赖方向 | **`bind` 只产 `BindIdentity { plan, definition }`**；`ImplementationIdentity`、载荷身份与 `ExecutionReceipt` 只在 `fmp-materialize`；`fmp-validate` 的依赖只允许 `fmp-model`，并加 `cargo tree` 检查 | 新增（第二轮 P1） | 把 implementation 放进 `BindIdentity`：要么 `fmp-validate → fmp-materialize` 成环，要么让验证结论依赖宿主 |
| D12 | `Plan.document` 如何处置 | **保留并改名 `legacy_document`**，只供旧 `fingerprint()` 只读；`ParsedPlanIdentity` 与编码/布局/fixup 决策都不读。**但它经 `fingerprint` 仍影响 `payload_digest`**：`BindIdentity` 相同的两个计划（A 与 A+`source_trace`）`fingerprint` 与 `payload_digest` 都不同，所以它**不是完整 legacy Artifact 的重放键**；完整身份必须用含 `PayloadIdentity` 的 `ExecutionReceipt`。删除它需要新指纹算法 + 新 ADR | 新增（第二轮 P1）→ **第三轮补充反例** | 直接删除：解析器丢弃 `source_trace`/`symbol.type`/`symbol.size`，旧指纹无法保持逐字节不变（已实测） |
| D13 | 公开可变的 `Plan` DTO 如何进入 `bind` | **不信任类型，重新验证结构**：`plan::check_structure(&Plan)` 重放解析器中未被类型强制的全部规则——`format_version`、`payload_hex` 的偶数长度小写十六进制，以及 `FieldRange.lsb` 0–127、`FieldRange.width` 1–64、`RangeConstraint.bits` 1–64、`RangeConstraint.align_bits` 0–12、`Fixup.transform_shift` 0–63 五个数值边界。`bind` 在摘要比对、`check` 与任何移位/求和之前调用。`fmp-validate` 的描述符算术同时改为 `u64`/`checked_add`，但那是第二道防线，不是替代。`Plan` 继续公开可变，`planner_api.rs` 的负例写法不变；`ValidatedPlan` 仍是唯一凭证 | 新增（第四轮 P1）→ **第五轮扩围** | 改成只有私有字段的构造器/包装类型：`planner_api.rs` 约 1500 行「解析后改字段」的负例要重写，且会把「测试便利」误当成「执行信任」；只复用 `check()`：`check_fragments` 只比 `len()/2 == size`（奇数长度仍会进 `decode_hex`），且 `check` 本身在 `align_bits >= 128`、`bits == 0`、`width = u32::MAX` 时会 panic |
| D14 | validator 的位位置算术与逐位循环如何有界 | **先有界，再比较**：fixup 绝对位位置（`offset * 8 + lsb`）用 `u128` 计算（`u64::MAX * 8 + u32` 在 `u128` 内必然可表示），描述符局部算术用 `u64`/`checked_*`；`check_fixup_overlap` 不再执行 unchecked `offset * 8`。`check_one_writer`/`check_fixup_ownership` 的逐位循环只遍历与 `0..form.bits()` 的交集，超出模板的宽度由 `check_fixup_descriptor` 的 `E-FIXUP-005` 报告，循环不按 `u32::MAX` 走。H1a 用**合法解析的 JSON** 计划（两个极大 offset，同一 section）和 `u32::MAX` 宽度测试，debug 与 release 都必须在有限步返回 | 新增（第六轮 P1） | 只把求和改成 `u64`：`offset * 8` 仍溢出、逐位循环仍无界；前序检查出错就跳过后续检查：会少报重叠/ownership 诊断，改变 619 负例集合 |
| D15 | `bind` 如何确认计划声明的定义身份就是传入的定义 | **比较三元组**：`namespace`、`version`、`digest` 逐字段与传入的不可变 `Definition` 比对，全部一致才继续；`BindIdentity.definition` 从传入对象取，不从计划里的声明取。今天 `materialize` 只比 `digest`（`:349-359`），`namespace`/`version` 只由 `Registry::find`（`definition.rs:805-826`）在**选定义**时约束；`bind(plan, Arc<Definition>)` 的调用者不必经过 `Registry`，所以缺的这个检查必须由 `bind` 自己承担（`01_contract.md` §5：`namespace + version` 映射到唯一 digest）。诊断沿用 `E-DEF-001`，Pointer 分别为 `/definition_identity/namespace`、`/definition_identity/version`、`/definition_identity/digest`；digest 那条的 Pointer 与 detail key 保持现状，所以 619 负例的输出逐字节不变 | 新增（第七轮 P1） | 继续依赖 `Registry::find`：只对 CLI 成立，公开库入口仍可错配；只比 `(namespace, version)`：现成的 digest 失配拒绝会退化 |
| D16 | 可由合法计划触发的 `internal(...)` 如何处理 | **先补静态前提，再分类**：`Transform::Page` 必须配 `PcRule::PcrelPage`（`03_fixup_model.md` §4/§6，`adrp`），缺失时 `check` 返回 `E-FIXUP-001`（Pointer `/fixups/i/pc_reference_rule`，`kind: "value_transform:page"`），不再让 `emit` 的 `:725-733` 用 `internal(...)` 兜底。H1a 为 `emit` 的 15 处 `internal(...)` 逐项记录「由哪项验证保证」，填不出的补检查；确实不可由计划触发的分支写进 `ADR-0127` 并附原因。由计划可触发的内部故障必须消失，`Internal` 只留给真正的实现不变量破坏 | 新增（第七轮 P2） | 把它归入 `PostEncodeAssertion`/`Internal`：等于把可静态拒绝的输入说成实现缺陷，「`bind` 之后不再拒绝」仍不成立；只修 `page` 不审计其余分支：同类缺口换个变换就复发 |

## 10. 证据状态

| 结论 | 依据 | 状态 |
|---|---|---|
| 六个缺口中的三个由 H1 关闭 | 前两条有运行测试；第三条是可读签名事实（§1.1）。另有三条归 H3/H4 | 高 |
| `Definition.digest` 在加载时由文档算出 | 读 `definition.rs:217` | 高 |
| `Definition.document` 从未被读取 | 全仓库 grep `.document`：只有写入处 | 高 |
| 旧 `fingerprint` 依赖原始文档中解析器丢弃的字段 | `a_legacy_fingerprint_covers_document_fields_the_parser_drops` 通过：加 `source_trace` 后解析 DTO 不变、指纹改变 | 高（已实测） |
| `fmp-validate` 不依赖 `fmp-materialize` | 读 `prototype/crates/fmp-validate/Cargo.toml`：`[dependencies]` 只有 `fmp-model` | 高 |
| `materialize` 的产品路径没有 I/O | `std::fs` 只出现在 `fmp-materialize/src/lib.rs` 的测试里（`:947`、`:1075`） | 高（I/O 事实） |
| 无 I/O ≠ 无宿主故障 | `emit` 在 `:400` 调用 `try_reserve_exact(size)`，失败时 `:401` 记 `internal("image reservation failed")`；分配失败只取决于主机资源 | 高（源码事实）— 所以 D4 保留 `HostFailure` |
| 64 MiB 映像上限已在 `fmp-validate` | `MAX_IMAGE_BYTES` 定义在 `fmp-validate/src/lib.rs:18`，检查在 `:285` | 高 — 不是 H4 新增 |
| 公开可变 DTO 能绕过解析器的结构检查 | `plan.rs:515-523` 只在 `read` 路径检查 `payload_hex`；`:858-860`/`:922-943` 的五个数值边界也只在那条路径；`fmp-validate/src/lib.rs:452` 只比 `hex.len() / 2`，`:821` 直接移位 `align_bits`，`:1284` 以 `u32` 求宽度和；`fmp-materialize/src/lib.rs:887-890` 直接访问 `pair[1]`。这些相加构成源码级反例 | 高（源码事实）— 尚未跑修改后的 Rust 程序；H1a 用 X86-P71、`A64-P4` 与 `page`+`none` 落八条运行负例（D13/D14/D16） |
| 合法解析的极大 `offset` 会让重叠检查溢出 | `check_fixup_overlap` 无条件在 `check_fixups` 之后运行（`:1010`），用 `fixup.offset * 8 + lsb`（`:1309-1312`）；`offset` 是解析器允许的完整 `u64`，两个同节 fixup 即可触发 unchecked 乘法 | 高（源码事实）— debug 可能 panic；H1a 的 `two_huge_fixup_offsets_do_not_overflow` 从合法 JSON 实测 |
| 异常宽度会让逐位检查无界 | `check_one_writer` `:1426` 遍历 `lsb..lsb+width`，宽度越界只是 `continue`；`check_fixup_ownership` `:1475` 用 `u32` 加法构造同一范围 | 高（源码事实）— `u32::MAX` 宽度可遍历约 40 亿位；H1a 的宽度测试要求有限步返回 |
| CLI 现有出口是 `0/1/2` 三分 | `fmp-cli/src/main.rs:16` 与 `:30-56`；`04_errors.md:78` 把 `E-INTERNAL-001` 定义为实现缺陷 | 高 — 所以 `Internal` 必须走 exit 2，而不是与计划拒绝共用 1 |
| 宿主分配失败应独立分类 | HE-1 设计 `docs/architecture/he1-horizontal-extension.md` §8.3 明确写入 `HostFailure` | 高 |
| 编码后**至少**有两种失败 | 读 `lib.rs:583`、`:597`；负例计数 2 与 1 | 高 |
| 编码后失败**不止**两种（旧的「三条编码后」分类已撤回） | `E-BYTE-001` 只在 `emit`（`:597-609`）；fixup 的 `E-RANGE-003`（`:707-716`）与 `E-FIXUP-003`（`:752-771`）只在 `apply`；`E-FIXUP-002` 在 `:689`、`:833`。而 `E-SIZE-001` 的两个负例先被 `validate` 的 `:655-668` 拒绝，不进入 `emit` | 高（源码事实）— 值级快照集合由 H1a 实测确定（§4.3） |
| 拟议的 `bind` 只搬 digest 会漏掉 namespace/version | 读 `materialize :349-359`（只比 digest）与 `Registry::find :807-826`（namespace + version → 唯一 digest）；`bind(plan, Arc<Definition>)` 的输入不保证经过 `Registry`，`01_contract.md` §5 要求三者对应 | 高（源码事实）— H1b 的 `a_declared_namespace_must_match_the_bound_definition` 落测 |
| `page` 可以没有 PC reference 就通过静态检查 | `check_fixup_kind`（`:1153-1246`）没有 `page` 规则；`emit` 在 `:725-733` 以 `internal(...)` 失败。A64-P6 把 `fixups[0].pc_reference_rule` 改成 `none` 即构造；该字段值已在夹具中核对 | 高（源码事实）— 未运行修改后的 Rust 程序；H1a 的 `a_page_transform_without_a_page_pc_rule_is_rejected` 落测 |
| 定义输入可让寄存器宽度检查移位到 64 位以上 | `reg_number` 槽位不允许 `range`（`definition.rs:487-499`），总宽只由 placements 之和决定（`bind_placement` 单个 ≤64，个数无上限）；`validate` 的 `:775` 用 `1u64 << field_bits`，64..127 在 debug 溢出 | 中（源码事实）— 未运行；H1a 先复现再定修复 |
| envelope 不能加字段 | `fixtures.rs:143-153` 固定整份 artifact | 高 |
| 现有负例门禁只比三元组 | 读 `fixtures.rs:220-254`、`planner_api.rs:247`：排序后的 `(code, path, detail-key 集合)` | 高 |
| `determinism.rs` 钉的是 envelope 摘要 | 读 `:63` 的 `canonical_bytes(&artifact.to_json())` 与 `:158`/`:163`/`:168` 三个常量 | 高 |
| 调用点数量 | 在 `d42125d` 与当前树上 grep 计数（§1.2） | 高（会随实现变动） |
| `compile_fail` doctest 能覆盖 API 约束 | 未在本仓库跑过 | **未验证** — 第一个提交时先证明它能触发 |
| 两个提交都全绿 | 尚未实施 | 未验证 |

# H1 实施计划（草案）：封闭执行对象与身份

- 状态：**草案，non-normative**。评审通过后，规范决策写入 `ADR-0127`；本文件
  保留为实施计划、验收映射和待审问题清单。
- 基线：`d42125d`（H0 已提交，工作树干净）。文中行号均取自该提交。
- 上游：`ADR-0125`；`ADR-0126`（身份分层与构建收据）；
  `docs/architecture/he1-horizontal-extension.md` §8（不可变执行边界）、
  §13「H1」、§14（`HE-T02`/`HE-T03`/`HE-T04`/`HE-T20`）、§15.1。
- 完成定义：`HE-AC-06` 连同 `HE-T02`、`HE-T03`、`HE-T04` 由运行期测试或编译期
  测试证明；旧 128 个产物载荷（`payload/0.1` 投影）逐字节不变
  （`research/he1/compatibility-results.json` 的 `payload_root`）。

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
| 深层 JSON 无界 | `tools/he1_baseline.py --probes` 的 `deep-json` 探针：退出 `3221225725`（**不是** Rust 测试之一） | 否 — H4 |
| 旧指纹依赖解析器丢弃的原始文档字段 | `a_legacy_fingerprint_covers_document_fields_the_parser_drops`：加 `source_trace` 后解析结果不变、指纹改变 | **必须保留**（约束，不是缺口；`D12`） |

H0 报告最初写「五个测试以记录漏洞的方式通过」，这是**错误分类**：那批测试实际是
**4 个缺口 + 1 个约束 + 2 个对照**（摘要失配拒绝、非对象顶层拒绝），深层 JSON 的
证据来自 Python 探针。缺口本身不变，错的是归类；`ADR-0126` 已在 `H0-report.md` §6
更正，第二轮评审后又补了那条约束测试（`H0-report.md` §7）。
H1 只翻转前两条（定义重编码、稳定指纹），保留约束测试，这一点写进 `ADR-0127`，
避免验收时把 H3/H4 的条目算进 H1。

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
| `src/plan.rs` | `Plan.document` 改名 `legacy_document`，字段注释限定为「旧 `fingerprint()` 的唯一输入」；不加任何新访问器 |
| `src/lib.rs` | 导出 `identity` 模块与 `ParsedPlanIdentity`；**不**导出 `ImplementationIdentity` |
| `src/definition.rs` 测试 | 现有 22 个模型测试按访问器改；新增「同一字节两次加载摘要相同」 |

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
| `ValidatedPlan`（新增） | `{ plan: Plan, definition: Arc<Definition>, identity: BindIdentity }`；唯一构造 `bind(plan: Plan, definition: Arc<Definition>) -> Result<Self, Vec<Diagnostic>>` |
| `bind` | 复用现有顺序：先摘要比对（现 `materialize` 的 `:349-359`），再 `check`，最后 `diagnostic::sort`。顺序不变是负例门禁的前提 |
| `check` | 签名不变，内部改走访问器 |
| `BindIdentity`（新增） | `{ plan: ParsedPlanIdentity, definition: DefinitionIdentity }`。**没有** implementation 字段，也没有 `PayloadIdentity`：两者都要在产物存在后才知道 |
| `Model` | 不变（只读视图） |

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
| `MaterializationFailure`（新增） | 三个变体：`PostEncodeAssertion(Vec<Diagnostic>)`（只在产物字节生成后才能发现）、`Internal(Diagnostic)`（`E-INTERNAL-001`）、`HostFailure(HostFault)`。**不设 `Rejected`**：`bind` 之后不应再有静态拒绝，给一个不可达变体只会造出语义模糊的分支 |
| `HostFault`（新增） | 初始只有一个变体 `ImageReservation { requested: usize }`。它描述「这台机器没能满足一次请求」，不描述计划；诊断文本由 CLI 组装，不带可变字节。H4 若加入新的主机相关限制，是新变体，不是新 crate |
| 宿主故障的归属 | **没有 I/O 不等于没有宿主故障。** `emit` 在 `:400` 的 `try_reserve_exact(size)` 就是一次分配，源码注释 `:397-399` 已经写明「a failed reservation here is a host limit, not a plan property」；64 MiB 上限**已经存在**于 `fmp-validate/src/lib.rs:18`（检查在 `:285`），不是 H4 才引入。分配失败取决于主机资源状态，既不是计划属性，也不是 `E-INTERNAL-001`——该码的意思是「不变量被破坏」，而这里不变量成立、只是主机给不出内存。设计 §8.3 明确要求把主机分配失败独立归类为 `HostFailure`。CLI 把 `HostFailure` 映射到 exit 2 的宿主通道（与 `Failure::Io` 同级），而不是 exit 1 |
| 分配失败的测试 | 把 `try_reserve_exact` 抽成 `fn allocate_image(size: usize) -> Result<Vec<u8>, HostFault>`，`emit` 只调用它。测试传入一个在指定 size 上返回 `Err(ImageReservation { .. })` 的同签名函数参数。**不用**全局开关、环境变量或真的耗尽内存：前者是隐藏输入（`INV-05`），后者不稳定且会拖垮 CI。断言 `MaterializationFailure::HostFailure`，并断言它不是 `Internal`、不是诊断数组 |
| `post-encode` 的成员必须先实测 | `emit` 今天还能返回 `E-FIXUP-002`（`:689`）、`E-RANGE-003`（`:710`）、`E-FIXUP-003`（`:766`）、`E-FIXUP-002`（`:833`）。它们是「`check` 没拦住」还是「只能在此刻发现」，H1a 必须先跑一遍负例确认，再决定归入哪一个变体；**不猜**。若某条在 `check` 已拒绝，它属于 `bind` 的 `Vec<Diagnostic>`。`emit` 里另外两处 `internal(...)`（`:384` 未验证 section、`:393` size 不适合主机）保持 `Internal`；`:401` 的分配失败改判 `HostFailure` |
| `fingerprint` | **算法与输出逐字节不变**，唯一输入是 `Plan.legacy_document`；文档注释改为「legacy envelope 身份，按 `ADR-0123` 解释；不覆盖解析后的操作数；不可用于新身份」。`a_legacy_fingerprint_covers_document_fields_the_parser_drops` 钉住它对 `source_trace` 的敏感性 |
| `payload_digest`（新增） | `payload/0.1` 投影的 canonical sha256：`to_json()` 去掉 `materializer_version`。**不是** `canonical_digest(to_json())`——那会把构建身份算进载荷（`ADR-0126`） |
| `lookup`（`:881`） | 走 `definition.forms()` |
| `legacy::materialize`（新增，`#[deprecated]`） | `(&Plan, Arc<Definition>)`：内部 `bind` 后调用新 `materialize`，只返回 `artifact`、丢掉 receipt。它**不是源码兼容入口**：路径和参数类型都变了；它的作用是保留一个「两参数形状且无法绕过检查」的过渡函数（§5） |

### 3.4 `fmp-cli`

`main.rs:100-110` 改为 `Registry::load_dir` → `plan::read` → `Registry::find`
（得 `Arc<Definition>`）→ `bind` → `materialize`。返回的 `Materialization` 里
CLI 只打印 `artifact`；`receipt` H1 不落盘（H3 建 run receipt 时才决定协议）。
`PostEncodeAssertion` 与 `Internal` 仍把完整诊断数组写到 stderr、exit 1，负例输出
不变。`HostFailure` 不同：它不是计划错误，走宿主通道 exit 2（与 `Failure::Io`
并列），stderr 说明是哪一次分配失败。宿主故障由此有了一个明确的、不依赖具体操作
系统的分类点。

### 3.5 测试改造

| 文件 | 改动 |
|---|---|
| `he1_identity_characterization.rs` | H1a 改定义可变性那条（见 §4.1）：字段私有化后它无法编译，改成 `compile_fail` + 「改文档后重载得到新摘要」；H1b 只翻转指纹那条（`a_parsed_operand_can_change_under_a_stable_fingerprint` → 拒绝）。其余 5 条保留（H3 关 2 条缺口、1 条 legacy 约束、2 条对照），文件头加「所属阶段」表；深层 JSON 属 H4，证据是 Python 探针，不是该文件的测试 |
| `fixtures.rs`、`determinism.rs`、`planner_api.rs` | `materialize` 改走 `bind`；`find` 返回 `Arc` 后约 8 处加 `&` |
| `fmp-materialize` 单测 | 5 处 `materialize` + 4 处 `fingerprint` 按新签名改 |

## 4. 测试计划

### 4.1 编译期（`HE-T02`/`HE-T04`，「API 不可表达」）

用 `compile_fail` doctest，零新依赖：

| 位置 | 断言 |
|---|---|
| `fmp-model` crate 文档（H1a） | 外部 crate 不能写 `definition.forms`，不能 `Definition { .. }` |
| `fmp-validate` crate 文档（H1b） | 不能 `ValidatedPlan { .. }`，不能 `Clone`；`materialize` 只接受一个参数，无法「用 A 验证、传 B 执行」 |

限制：`compile_fail` 只证明「编译失败」，不证明失败**原因**。计划在 doc 注释里
写明这一点，并在评审时人工核对一次失败信息。

H1a 的定义可变性改造具体是：把现在直接写 `definition.digest` / `forms` /
`template` 的那条测试拆成两半——编译期 `compile_fail` 证明字段不可写；运行期
`a_definition_edit_reloads_to_a_new_digest` 改定义**文档字节**后重新 `read`，
断言摘要变了、且旧计划按摘要被拒。这样既保留了「摘要覆盖内容」的实测，又不依赖
被封闭的字段。

### 4.2 运行期

| 测试（拟名） | 断言 | 对应 |
|---|---|---|
| `a_definition_reloads_to_the_same_digest` | 同一字节两次加载摘要相同；换行/键序不同但 canonical 相同则摘要相同 | `HE-T03` |
| `a_tampered_definition_document_is_rejected_by_bind` | 改模板保留计划中的旧摘要 → `E-DEF-001` `/definition_identity/digest` | `HE-T03` |
| `a_mutated_operand_changes_the_plan_identity` | 改 `payload.reg` → `ParsedPlanIdentity` 变 | `HE-T02`/`HE-T04` |
| `plan_identity_covers_every_parsed_field` | 逐字段 mutation 表（section/instruction/operand/modifier/fixup/symbol/output/target），每项都必须改变身份 | 硬规则 2 的逐字段反例 |
| `plan_identity_ignores_provenance` | 只改 `provenance` → 身份不变（与 legacy `fingerprint` 的排除一致） | §12 |
| `a_definition_edit_reloads_to_a_new_digest` | 改定义文档字节后重载：`digest` 变；旧计划按旧摘要被 `bind` 拒绝。替代 H1a 之后无法编译的字段直改测试 | `HE-T03` |
| `plan_identity_ignores_the_legacy_document` | 只改 `source_trace` → `ParsedPlanIdentity` **不变**、旧 `fingerprint` **变**；两者是不同主张，不能互相替代 | D12 |
| `a_bind_identity_does_not_identify_the_legacy_artifact` | 计划 A 与「A + `source_trace`」：两个 `BindIdentity` 字段都相同，`fingerprint` 与 `payload_digest` 都不同；完整收据能区分 | D3、D12 |
| `an_image_reservation_failure_is_a_host_failure` | 注入 `allocate_image` 失败 → `MaterializationFailure::HostFailure`，不是 `Internal`、不是诊断数组；同一计划在够内存的主机上仍成功 | D4、`§8.3` |
| `a_legacy_fingerprint_covers_document_fields_the_parser_drops` | H0 的约束测试，H1 之后仍然通过（改名 `legacy_document` 不改变行为） | `HE-AC-10`、D12 |
| `receipt_names_the_build_that_ran` | `receipt.implementation` 来自物化器的编译期常量；`FMP_BUILD_ID` 缺失时记 `build: None` 且不宣称满足 `HE-T20` | `HE-T20`、D9 |
| `bind_reports_only_plan_and_definition` | `ValidatedPlan` 的 `BindIdentity` 里没有 implementation 字段（编译期 + 依赖方向） | D11 |
| `payload_digest_follows_the_bytes` | 改一个操作数 → 字节变 → 载荷身份变；再改 `materializer_version` → 载荷身份**不变**、envelope 变 | `HE-T20`、`ADR-0126` |
| `legacy_facade_rejects_a_digest_mismatch` | 二参 facade 同样拒绝（H0 的对照测试迁到这里） | `HE-T04` |
| `bind_reports_the_definition_it_bound` | `identity.definition.digest` 等于实际执行定义的摘要 | `HE-AC-06` |

### 4.3 金样与既有门禁

先说清现有测试**实际**证明了什么，再说 H1 加了什么。

`fixtures.rs::negatives_produce_exactly_the_registered_diagnostics`（`:220-254`）
和 `planner_api.rs::negatives_reject_at_the_same_code_path_and_detail_keys`
（`:247`）比较的是 **排序后的三元组** `(error code, JSON Pointer, detail key 名字
集合)`。它们**不**比较 detail 的**值**、完整消息文本或原始诊断顺序。因此：

| 门禁 | 实际保证 |
|---|---|
| `python tools/he1_baseline.py --check research/he1/compatibility-results.json` | 128 个产物**载荷**（`payload/0.1`）、104 个定义摘要、计数、oracle 状态不变。`envelope` 只在实现收据相同时才比较 |
| `python tools/test_he1_baseline.py` | 比较器自检：payload 变化必失败、实现收据不同时仍比较 payload、结构或计数变化必失败。不依赖真实二进制，因此 CI 里先于基线比较运行 |
| `cargo test --workspace` 的 `fixtures`/`planner_api` | 619 个负例的 **code + Pointer + detail-key 集合**相等。detail 值与顺序**不在**门禁内 |
| `determinism.rs` | 每 ISA 一条 **envelope** 摘要（`materializer_version` 在内），跨三主机 |
| `fixtures.rs` 的 Level-1 用例 | envelope 形状未被新身份污染 |
| `tools/oracle/rerun.py` | 122 条仍可复现 |

H1 只把「值级」保证加到 3 条**编码后失败**的负例上（`E-SIZE-001` ×2、
`E-BYTE-001` ×1）：它们的 detail 带数值（`expected`/`actual`），而 H1 会动这条
路径。做法是给这 3 条加规范化快照（含 detail 值），其余 616 条继续用三元组门禁。
不整体加，是因为 619 条全量值级快照会把每次合法的消息措辞调整都变成门禁失败，
收益与维护成本不成比例。

如果将来要宣称「完整诊断数组逐字节不变」，必须先把门禁扩大到全部 619 条；在那
之前，计划和报告都不得使用这个说法。

## 5. 兼容性影响

先按**兼容类**分开写，因为「不变」在这几层含义不同（`ADR-0126` 的教训）：

| 层 | 结论 |
|---|---|
| FMP 文档面（`fmp/0.1` 计划、`fmp-def/0.1|0.2` 定义） | **不变**。字段、语义、拒绝规则不动 |
| 128 个正例的**载荷** | **不变**（`payload_root` 不变）。这是 `HE-AC-10` 的判据 |
| Artifact **envelope** | 形状不变、不加字段；`materializer_version` 仍是 envelope 收据，可变 |
| 旧 `fingerprint` | 算法与输出不变，输入仍是 `Plan.legacy_document`（只读、legacy-only）；文档标注 legacy，**不**作为新可信身份。它是 Artifact 字段，所以仍影响 `payload_digest` |
| `BindIdentity` 的语义 | 只是「计划事实 + 定义摘要」的绑定，**不是**完整 legacy Artifact 的重放键：多一个 `source_trace`，两个绑定字段都不变，`payload_digest` 却变。完整身份用 `ExecutionReceipt` |
| **Rust 库 API** | **允许迁移**。`fmp_materialize::materialize` 的路径与参数类型都变；`legacy::materialize` 只是「两参数形状且无法绕过检查」的过渡函数，**不是源码兼容入口**。仓库外的调用者需要改代码 |
| 「旧入口」指什么 | `fmp/0.1` 文档面、产物 envelope 与 `fmp` CLI 行为。**不是** Rust 库函数签名；`ADR-0125` 决策 6 的 adapter 只承诺前者 |
| 619 个负例诊断 | code + Pointer + detail-key **集合**不变；3 条编码后失败的值级快照（§4.3） |
| 定义文件与形态 | 不改；`definitions/**` 一个字节不动 |
| 错误码 | 不新增。`E-DEF-001`/`E-SIZE-001`/`E-BYTE-001`/`E-INTERNAL-001` 均已注册 |
| 宿主故障 | 分配失败由 `MaterializationFailure::HostFailure(HostFault)` 表达，CLI 映射为 exit 2 的宿主通道（与 `Failure::Io` 同级）；`E-INTERNAL-001` 只留给真正的不变量破坏。64 MiB 上限已在 `fmp-validate`，不新增限制；H4 若加新的主机相关限制，是新的 `HostFault` 变体 |
| 计数 | 不改 `STATUS.md` 的 v0 计数；测试数会变（7 个 characterization 里 1 个翻转、1 个改为 `compile_fail` + 重载测试，其余保留） |
| 依赖方向 | 不变：`validate → model`，`materialize → validate + model` |

「原型阶段允许 API 迁移」是本轮的明确选择（§9 D5）；如果评审要求旧库调用点源码
兼容，则必须重新设计新旧入口的命名、参数与绑定生命周期，而不是把 facade 描述成
「原入口不变」。

## 6. 提交拆分与门禁

| 提交 | 内容 | 每步必过 |
|---|---|---|
| H1a | `Definition` 封闭 + `Registry` 用 `Arc` + `identity` 模块 + `Plan.legacy_document` 改名 + 逐字段 mutation 测试 + 定义可变性测试改造（`compile_fail` + 改文档重载） | `fmt`、`test --workspace`、`baseline --check`、`check_ids` |
| H1b | `ValidatedPlan` + `bind` + `BindIdentity` + 新 `materialize`/`Materialization`/`ExecutionReceipt` + `MaterializationFailure`/`HostFault`/`allocate_image` + facade + 调用点迁移 + **1 条**测试翻转（指纹） | 同上 + `oracle` + `check_definition` |
| 同 PR | `docs/adr/0127-*.md` + 本文件改为「已采纳」+ `research/he1/H1-report.md` | `check_ids`、`git diff --cached --check` |

一个 PR 两个提交：`ADR-0125` 决策 1 要求 H1 是一个阶段，§13.1 要求阶段内可回归。

## 7. 风险与回滚

| 风险 | 处置 |
|---|---|
| 身份算法写错，导致不同事实同身份 | 逐字段 mutation 表；`plan_facts` 是纯函数，可单测 |
| 给结构体加字段后忘记同步身份，漏洞复发 | **编译期**：穷尽解构、不用 `..`、枚举不写 `_ =>`（§3.1） |
| `plan_facts` 与 `bind` 漂移成两个权威来源 | 只从 `Plan` 读数，不读 `legacy_document`；`legacy_document` 只有一个读者（旧 `fingerprint`），并由 H0 约束测试钉住。注意旧 `fingerprint` 仍是 Artifact 字段，所以 `legacy_document` 会经它影响 `payload_digest`——这不是「新身份读了旧文档」 |
| 身份编码的字段顺序随重构变化，旧身份无法重算 | `ADR-0127` 把字段顺序与 tag 写成协议文本，附 3 个固定向量（其中一个用 Python 独立重算） |
| 诊断顺序变化，负例面扩大 | 619 个负例的 code/Pointer/detail-key 集合门禁；`bind` 内顺序照抄现实现；3 条编码后失败另有值级快照 |
| `Arc` 改动扩散 | 编译器引导，约 8 处；`Registry` 仍保持确定性顺序 |
| 有人继续用二参入口绕过 | facade 内部就是 `bind`；另加一条测试证明摘要不符仍被拒 |
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
- 解析深度上限、64 MiB 映像上限（H4）。
- fixup profile 与新原语（H4）。
- 任何指令覆盖扩张。

## 9. 待审决策

`D3`/`D4`/`D5`/`D7` 按第一轮评审修订，`D8`–`D10` 同轮新增；`D11`–`D12` 是
第二轮评审（`ebddbdb`）后新增；`D4` 在第三轮评审（`ccdc7a3`）后再次修订，加回
`HostFailure`。

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
| D10 | 负例门禁的声明范围 | 619 条只保证 **code + Pointer + detail-key 集合**；额外对 3 条编码后失败加**值级**快照 | 新增 | 619 条全量值级快照：把合法的措辞调整变成门禁失败，维护成本不成比例 |
| D11 | 身份归属与依赖方向 | **`bind` 只产 `BindIdentity { plan, definition }`**；`ImplementationIdentity`、载荷身份与 `ExecutionReceipt` 只在 `fmp-materialize`；`fmp-validate` 的依赖只允许 `fmp-model`，并加 `cargo tree` 检查 | 新增（第二轮 P1） | 把 implementation 放进 `BindIdentity`：要么 `fmp-validate → fmp-materialize` 成环，要么让验证结论依赖宿主 |
| D12 | `Plan.document` 如何处置 | **保留并改名 `legacy_document`**，只供旧 `fingerprint()` 只读；`ParsedPlanIdentity` 与编码/布局/fixup 决策都不读。**但它经 `fingerprint` 仍影响 `payload_digest`**：`BindIdentity` 相同的两个计划（A 与 A+`source_trace`）`fingerprint` 与 `payload_digest` 都不同，所以它**不是完整 legacy Artifact 的重放键**；完整身份必须用含 `PayloadIdentity` 的 `ExecutionReceipt`。删除它需要新指纹算法 + 新 ADR | 新增（第二轮 P1）→ **第三轮补充反例** | 直接删除：解析器丢弃 `source_trace`/`symbol.type`/`symbol.size`，旧指纹无法保持逐字节不变（已实测） |

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
| 宿主分配失败应独立分类 | HE-1 设计 `docs/architecture/he1-horizontal-extension.md` §8.3 明确写入 `HostFailure` | 高 |
| 编码后**至少**有两种失败 | 读 `lib.rs:583`、`:597`；负例计数 2 与 1 | 高 |
| 编码后失败**只有**两种 | `emit` 另有 `E-FIXUP-002`/`E-FIXUP-003`/`E-RANGE-003`（`:689`、`:766`、`:833`、`:710`）；是否都被 `check` 提前拦住 **未测** | **未验证** — H1a 先跑负例确认 |
| envelope 不能加字段 | `fixtures.rs:143-153` 固定整份 artifact | 高 |
| 现有负例门禁只比三元组 | 读 `fixtures.rs:220-254`、`planner_api.rs:247`：排序后的 `(code, path, detail-key 集合)` | 高 |
| `determinism.rs` 钉的是 envelope 摘要 | 读 `:63` 的 `canonical_bytes(&artifact.to_json())` 与 `:158`/`:163`/`:168` 三个常量 | 高 |
| 调用点数量 | 在 `d42125d` 与当前树上 grep 计数（§1.2） | 高（会随实现变动） |
| `compile_fail` doctest 能覆盖 API 约束 | 未在本仓库跑过 | **未验证** — 第一个提交时先证明它能触发 |
| 两个提交都全绿 | 尚未实施 | 未验证 |

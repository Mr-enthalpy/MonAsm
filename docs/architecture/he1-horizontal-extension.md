# MonAsm HE-1：横向指令集扩展底座重构设计

文档状态：已采纳为 HE-1 的设计依据（`ADR-0125`）。文中新增 API、包格式、目录和阶段仍是目标状态，不是已经实现的能力
设计版本：0.1
检查日期：2026-11-10
源码基线：`d0082f9f2d3da2786d8d1c0467d2793369ec9090`（H0 已复核，见 `research/he1/H0-report.md`）
落库位置：`docs/architecture/he1-horizontal-extension.md`（本文件）
目标里程碑：**HE-1 — Horizontal Extension Ready（横向扩展就绪）**

本文件 §3 的 `HE-AC` 表和 §14 的 `HE-T` 表是这两个 ID 族的注册表：每个 ID 只在这里声明一次，其他文档只引用。`tools/check_ids.py` 校验这一条。

---

## 0. 决策摘要

下一阶段不再以“又增加多少条指令、多少个 form、多少轮覆盖”为主要目标，而以如下能力为交付目标：

> 在同一份稳定的公共物化契约下，不同贡献者能够独立新增不同 ISA 或同一 ISA 的不同指令族；扩展主要发生在目标数据包、包内测试与证据中，合并时不必修改公共编码流程、全局指令清单和中心文档。

**HE-1 不是最终架构。** 它不要求完整 ISA 覆盖、完整高级语义 IR、通用约束求解器、完整 ELF/COFF/Mach-O 输出或动态插件平台。它要求先形成一个能够持续接纳这些工作的底座。

保留 Rust 物化内核、显式 form、版本化定义、冻结布局、严格拒绝以及既有正反例。Python 继续承担开发期工具；LLVM/XirAsm 继续作为外部知识或验证来源，不作为产品运行依赖。本轮不重开语言选型和汇编器横向比较。

采用的结构是：

**目标数据包 + 离线定义构建器 + 不可变定义快照 + 通用验证/编码内核 + 包级一致性测试。**

这里的“横向扩展”是工程扩展和并行协作能力，不是分布式部署，也不是要求物化过程本身并行执行。

---

## 1. 现状证据与重构起点

本设计重新核对了指定提交的若干关键路径，但没有在本轮执行仓库测试。下表区分实际源码事实和据此提出的设计判断。历史审计中的风险必须先补回归测试，不得把源码推断当成已经运行复现。

| 当前源码事实 | 定位 | 对 HE-1 的含义 |
|---|---|---|
| 编码主要由指定 form 的模板和位域 placement 驱动 | `fmp-materialize/src/lib.rs:557–648` | 保留此执行机制，不重新写一套智能编码器 |
| `Definition` 同时公开原文档、forms 和摘要 | `fmp-model/src/definition.rs:20–51` | 横向贡献前先收紧已验证对象的构造与可变性 |
| form ID 校验硬编码 x86、AArch64、RISC-V，以及 x86 编码族 | `fmp-model/src/definition.rs:714–755` | 新 ISA 目前仍会碰到公共代码；新协议应改为命名空间和包声明驱动 |
| Registry 递归读取目录中的全部 JSON | `fmp-model/src/definition.rs:788–850` | 新运行路径需要按明确依赖闭包加载，不能由仓库全貌决定可用性 |
| 定义检查脚本绑定 ISA 名称、全量版本定义和中心文档表格 | `tools/check_definition.py:1–40, 118–135` | 工程协作热点不只是 Rust 代码，还包括数据和文档 |
| 当前 FMP Schema 的 ISA family 是三项枚举 | `schema/fmp-v0.schema.json:29–65` | 不能以修改旧 Schema 的方式无声扩大冻结协议 |
| fingerprint 基于原始计划文档和缓存的定义身份 | `fmp-materialize/src/lib.rs:919–936` | 执行对象与身份必须共享不可变事实源 |

**本轮不是推翻现有内核，而是拆开目前围绕它形成的集中式扩展路径。**

现有 `definitions/<isa>/<version>.json` 是值得保留的冻结资产，不应为了目录整洁而重新生成、批量改摘要或删除历史版本。

---

## 2. 必须保持的设计约束

### 2.1 物化器没有规划权

物化器只校验和执行显式机器事实，不得搜索更好的 form、扩展伪指令、插入填充、放宽约束、生成 veneer、进行 relaxation 或回退到外部汇编器。

机械计算允许存在，包括位域填入、固定变换、范围检查、关联 fixup 求值和规范化输出。每项计算必须具有版本化、唯一的含义。

### 2.2 不统一硬件语义，统一承载与执行机制

不同 ISA 的寄存器、地址形式、条件、隐含操作数、修饰语义保留目标身份。公共层统一生命周期、引用、约束执行、错误、身份和输出，不强制所有目标使用同一种“通用内存操作数”。

FMP 是机器事实层。原子动词 `Transfer/Compute/Branch/...` 仍是上游可能采用的骨架，不在本轮植入物化内核。`fmp-plan` 的计划构造器也不因本轮重构而获得选指令或布局求解权限。

### 2.3 扩展是受验证的数据，不是任意运行时代码

HE-1 不加载目标提供的 Rust/C 动态库，不执行目标包中的 Python、Lua、WASM 或宏脚本。

开发期可以使用受审查的生成器，但物化器只消费已生成、已验证、已固定摘要的声明式产物。新增元编程能力不是 HE-1 验收条件。

### 2.4 不把可重放误当成正确性证明

同样输入输出同样错误机器码仍然是缺陷。包级验证必须同时覆盖精确字节、操作数语义约束、fixup 数值关系和失败行为。

固定摘要证明“使用的是哪份规则”，不证明规则符合 ISA。ISA 正确性仍依赖来源、独立 oracle 和测试。

---

## 3. HE-1 的精确定义与停止条件

达到下列全部条件后，本轮应结束，不继续自动进入指令覆盖扩张。

| ID | 必须达到的能力 |
|---|---|
| HE-AC-01 | x86-64、AArch64、RV64 各有至少一个包通过新路径；未迁移定义通过 legacy 路径保留 |
| HE-AC-02 | 两个同 ISA、不同指令族的包可以在同一基线上独立开发和任意次序合并 |
| HE-AC-03 | 在公共能力集已冻结后，普通扩展 PR 只修改自己的包目录和包内证据，不修改核心、Schema、全局清单或中心计数 |
| HE-AC-04 | 包及依赖按明确 ID、版本和摘要绑定；不存在 latest、隐式升级或后加载覆盖前加载 |
| HE-AC-05 | 添加未选中的包、改变目录遍历顺序，不影响旧 lock 所确定的输出或拒绝结果 |
| HE-AC-06 | 经过验证的定义和计划不能被公开字段修改；输出身份对应实际执行对象 |
| HE-AC-07 | 新增一个合成目标命名空间不需要修改公共 ISA allowlist、核心 match 或 Schema 枚举 |
| HE-AC-08 | 每个包能独立运行验证；公共改动触发全部包和 legacy 回归 |
| HE-AC-09 | 两个以上包不能静默争夺同一 form、类型或 profile 身份；冲突必须失败 |
| HE-AC-10 | 所有现有有效夹具保持机器码、节、符号与 fixup 载荷语义；元数据和错误收紧单独记录 |
| HE-AC-11 | 包的来源、许可、生成版本与 oracle 状态能够追踪 |
| HE-AC-12 | 完成一次真实的多工作流并行扩展演练，而非仅提交目录结构与 trait |

HE-AC-07 的合成目标仅证明“没有硬编码 ISA 名称障碍”，不能计入真实 ISA 覆盖率。

**普通扩展的定义：** 使用当前已经存在的公共位域、约束和 fixup 原语。确实需要新公共机制的扩展走能力提案，不属于“零核心变更”的承诺范围。

---

## 4. 目标结构：开发期和物化期分离

```text
开发期
ISA 资料 / LLVM 与其他 oracle / 人工审查
                   |
                   v
          独立 Target Packages
        forms / types / profiles
          tests / evidence / NOTICE
                   |
         显式 BundleSpec + 依赖闭包
                   |
                   v
        Definition Builder / Verifier
                   |
            lock + sealed bundle

物化期
Frozen Plan + 明确选定的 sealed bundle
                   |
                   v
            bind + validate
                   |
              ValidatedPlan
                   |
                   v
         Deterministic Materializer
                   |
        Bytes / Sections / Fixup Records
                   |
            Identity / Run Receipt
```

开发期构建器可以验证包完整性、解决已经明确指定的依赖、对集合做规范化排序并生成派生产物。它不能替程序选择 form 或完成布局。

物化期不扫描完整仓库，不查网络，不读取作者目录，不执行包钩子。

“数据包排序”与“程序布局排序”必须分开：规范化无序包集合是编码定义构建规则；重排指令、节、符号或 fixup 的显式顺序仍然禁止。

---

## 5. 模块边界与现有代码迁移

不要为了模块化立即建立十几个 crate。先保留当前 workspace 路径和五个 crate，新增一个职责明确的 `fmp-definition`；一致性测试先作为共享测试 harness，而不是产品依赖。

| 模块 | HE-1 职责 | 不允许承担的职责 |
|---|---|---|
| `fmp-model` | Wire DTO、公共值类型、规范化、诊断结构、版本入口 | ISA family 白名单、运行时指令选择 |
| `fmp-definition`（新增） | 包读取、依赖闭包检查、离线 bundle 构建、产物校验、不可变定义身份、只读索引 | 程序布局、fallback、任意包脚本执行 |
| `fmp-validate` | 计划与定义一致性、操作数约束、布局、符号、fixup/profile 绑定；产生 `ValidatedPlan` | 自动修复、默认补齐机器决策 |
| `fmp-materialize` | 消费验证结果，机械写位、应用修补、输出 | 重解析作者包、遍历可变注册表、重新选择 form |
| `fmp-plan` | 上游显式事实的构造与序列化 | 自动 form 搜索、常量物化、ABI lowering |
| `fmp-cli` | 显式输入装配、I/O、错误出口；开发工具可使用独立子命令或 binary | 隐式寻找最近的定义目录 |
| `tools/` | 文档报告、oracle 适配、受控生成工具、兼容包装 | 作为产品编码时的依赖 |

依赖方向：

```text
fmp-plan --------> fmp-model
fmp-definition --> fmp-model
fmp-validate ----> fmp-model + fmp-definition
fmp-materialize -> fmp-validate + 必要公共只读类型
fmp-cli ---------> 上述运行组件；不依赖 fmp-plan 执行规划
```

类型归属可在避免循环依赖的前提下调整，但以下两点不能变化：已验证定义不依赖具体目标 crate；物化器不依赖任一 ISA 包的可执行实现。

### 5.1 文件级重构指令

| 现有位置 | 本轮处理 |
|---|---|
| `fmp-model/src/definition.rs` | 抽取定义加载、编译、Registry 到 `fmp-definition`；保留 legacy reader；去掉新协议入口中的 ISA 专用名称分支 |
| `fmp-model/src/plan.rs` | 区分可构造 Wire DTO 与不可变 Bound/Validated 对象；禁止原文档和执行字段分别可变 |
| `fmp-validate/src/lib.rs` | 按 target、layout、operand、fixup 等拆文件；建立引用索引；新增 profile 绑定；不以拆文件代替职责重构 |
| `fmp-materialize/src/lib.rs` | 保留位域执行器；入口改为验证结果；禁止接收不相干的 plan/definition 二元组 |
| `tools/check_definition.py` | 先保留 legacy 检查；新包检查委托权威 Rust 实现；Python 只组织报告和 oracle |
| `tools/check_ids.py` | 支持包命名空间和局部 ID；中心 ID 只管理公共协议和公共错误 |
| `schema/fmp-v0.schema.json` | 冻结；新协议放新文件，不就地扩大旧枚举 |
| `definitions/` | 保留历史原件及摘要，不作为每次新增指令的人工编辑入口 |
| `docs/STATUS.md` 和中心 form 表 | 不再要求普通扩展手工同步；当前事实生成报告，架构决定仍人工记录 |

迁移中可以保留薄兼容导出或旧 API facade。必须明确其弃用状态和验证路径，不能形成第二套可绕过验证的执行入口。

---

## 6. 包模型：把指令族变成独立工作单元

### 6.1 建议目录

```text
packages/
  x86_64/
    shared-types/
    mov-register/
    mov-memory/
    scalar-alu/
  aarch64/
    integer/
    branch/
  rv64/
    integer/
    branch/

每个叶包：
  package.json
  types.json                  # 可选
  forms/*.json
  fixup-profiles.json          # 可选
  constraints.json            # 可选，受限声明式约束
  tests/cases/*.json
  tests/oracles/*
  evidence/sources.json
  evidence/decisions/*.md
  NOTICE
  README.md

bundles/
  profiles/<bundle-name>.json
  locks/<bundle-name>.lock.json

tests/
  conformance/
  compatibility/
  extension-probes/

definitions/                  # 既有冻结资产，继续可用
```

不要求本轮把全部已有 forms 移入包。每个 ISA 选择一个有代表性的纵向切片，新旧路径可并存。

### 6.2 包清单

以下是逻辑字段草案，不代表仓库已经存在此格式：

```json
{
  "package_format": "monasm-package/0.1",
  "package_id": "monasm.x86.scalar-alu",
  "version": "0.1.0",
  "target_profile": "monasm.target.x86_64",
  "requires_capabilities": [
    "field-placement/v1",
    "integer-domain/v1"
  ],
  "dependencies": [],
  "exports": {
    "forms": ["forms/add.json", "forms/sub.json"]
  }
}
```

依赖项一旦存在，必须明确 package ID、精确版本和内容摘要。这里的版本是目标资产版本，不是 kernel 版本或 FMP wire 版本。

清单中的文件列表是显式输入。路径必须为包内规范化相对路径；禁止 `..` 越界、符号链接逃逸、网络 URL 拉取和通过文件系统顺序形成语义。

### 6.3 身份与归属

公共层只理解命名空间、字符串身份、唯一性和引用关系，不根据 mnemonic 字符串判断怎么编码。

现有 form ID 在 legacy 中保持不变。新包可以导出现有 ID；bundle 构建时建立唯一归属表：

```text
form_id -> package_id + exact revision + verified form
type_id -> owner package + verified type
profile_id -> owner package + verified profile
```

不同包导出同一 ID，即使内容碰巧一样，也必须报告归属冲突。公共依赖包在依赖闭包中重复出现且精确身份一致时只加载一次；这与两个包各自重新定义同一 form 不同。

共享寄存器类型和 profile 由独立小包维护，避免每个指令族复制类型语义。普通扩展不需要递增全局数字或申请下一个 ADR 号。

### 6.4 依赖不使用隐式版本求解

HE-1 不实现包管理生态。不查询“最新版本”，不使用 semver 范围自动选择，不联网下载依赖。缺失、冲突、循环或摘要不符均失败。

包作者选择依赖；发布者选择 bundle。构建器只是验证选择，不替任何一方优化依赖。

---

## 7. Bundle 与冻结协议版本

### 7.1 Bundle 是显式的目标快照

BundleSpec 明确列出 target profile 和所选包的精确身份。构建器计算闭包、检查冲突并生成：

1. lock：具体依赖及摘要；
2. 执行 bundle：扁平化、可验证的数据；
3. 派生目录和覆盖报告。

一个 FMP 绑定一个精确 bundle 身份。新增包不会自动加入既有 bundle。

目录扫描只可用于开发期展示“有哪些包”，不能用于决定“这份计划采用哪些包”。

### 7.2 摘要分层

| 身份 | 覆盖内容 |
|---|---|
| `source_package_digest` | 包内规范化清单及显式声明的可执行定义输入，记录包修订 |
| `definition_digest` | 实际执行的类型、forms、约束、profile、原语语义版本及所需目标事实 |
| `plan_digest` | 实际执行的冻结计划事实，包括显式输出和布局约定 |
| `artifact_digest` | 规范化结果载荷：字节/节/符号/fixup |
| `implementation_id` | 本次物化器构建身份，如 release、commit、构建描述摘要 |

定义内容摘要不能包含自身字段，否则产生自引用。实现可以采用外部 envelope 或明确排除 digest 字段的规范化规则。

证据说明、审计备注和作者个人路径不得偶然改变执行摘要；但必须能够从发布清单追踪它们。定义变动、错误约束变动和原语语义变动不能躲在“非执行元数据”里。

旧 lock 选择的输入未变时结果必须不变；创建一个包含更多包的新 bundle 后，bundle digest 改变是正确行为，不应为了“稳定”复用旧摘要。

### 7.3 新旧协议策略

冻结并继续接受 `fmp/0.1` 及既有 `fmp-def/0.1`、`fmp-def/0.2` 资产。

建议为新路径建立最小新版本：

- `fmp/0.2`：允许目标定义提供命名空间化 ISA 身份；允许以 profile ID 绑定 fixup；不引入高级语义操作。
- `monasm-package/0.1`：开发期包格式。
- `monasm-bundle/0.1`：运行期定义快照格式。

具体字符串可以由首份 ADR 固定，但三种版本语义必须分开。

新 FMP 的 layout、instruction、operand 基本骨架沿用现有结构。`definition_identity` 可以继续承担 bundle 身份，不必仅为改名新增一套冗余字段。

新版本的对象结构仍然封闭。开放的是目标命名空间和受验证的数据定义，不是任意未知字段、任意脚本或无约束扩展对象。

旧计划不得隐式升级到新版本。转换工具如存在，必须显式运行，产生新的计划身份和可审查差异。

---

## 8. 不可变执行边界

### 8.1 类型生命周期

```text
输入字节
  -> Raw/Parsed DTO
  -> VerifiedDefinitionBundle（私有构造、不可变）
  -> BoundPlan（绑定精确 bundle）
  -> ValidatedPlan（所有静态约束通过）
  -> MaterializationResult
```

逻辑接口示意：

```rust
fn load_bundle(bytes: &[u8]) -> Result<VerifiedBundle, DefinitionErrors>;

fn bind_and_validate(
    plan_bytes: &[u8],
    bundle: Arc<VerifiedBundle>,
) -> Result<ValidatedPlan, PlanErrors>;

fn materialize(plan: &ValidatedPlan)
    -> Result<MaterializationResult, MaterializationFailure>;
```

接口是设计约束示意，不是现成可编译代码。实施可保留便捷 facade，但底层最终必须通过这一生命周期。

`ValidatedPlan` 表示结构和静态约束通过，不应虚称已经证明所有字节级断言。`MaterializationFailure` 至少区分生成字节后才能发现的确定性断言失败（例如 expected digest 不符）、主机故障和内部不变量错误。能够提前计算的 fixup 值和范围应尽量在验证阶段固定；无论在哪一阶段失败，都不得返回部分成功产物或尝试替代形式。

### 8.2 强制要求

已验证类型的 fields 私有；不提供 `&mut`、`DerefMut`、可变内部共享状态或跳过验证的 public constructor。公开 DTO 可以可变，但它不是执行凭证。

`ValidatedPlan` 持有它绑定的定义快照，或者等价的不可替换身份与只读引用。不能先用 A 验证，再把 B 传给 encoder。

计划 canonical bytes、解析结果和摘要从同一不可变事实源构造。缓存只可派生，不能成为第二个可单独修改的权威来源。

加载器必须从已经读取到内存的同一份快照计算摘要并执行验证，不得先哈希文件、再另开文件读取执行内容而留下 TOCTOU 窗口。

定义产物即使带摘要也必须重新进行结构、安全和能力检查。摘要不是免检通行证。

### 8.3 错误边界

`PlanRejected` 是由显式计划、定义、协议和验证规则决定的错误。主机分配失败、I/O 失败等应独立归类为 `HostFailure`，不能声称不同资源状态的机器一定产生相同主机故障。

解析深度、包数量、模板长度、位域宽度和映像大小必须有确定上限。保留旧版本的已声明限制；新执行 profile 的限制必须显式并可记录，不能读取主机内存自动决定接受范围。

---

## 9. 公共内核与目标数据的权限边界

### 9.1 HE-1 只要求足够的有限能力集

建议初始能力集来自现有代码，不为了未来 ISA 一次性设计完整规则语言：

- 固定字节模板；零操作数形式；
- 常量位、连续/分散位域、固定位反转；
- 有符号/无符号域、对齐、有限排除集合；
- 类型与 feature requirement 检查；
- 显式的字段引用与单写者检查；
- 当前已有的绝对、PC-relative、page、Hi/Lo 类固定变换；
- 必要的有限关系检查，如寄存器相等/不等、配对身份一致。

这些是能力类别，不要求用此列表作为最终 API。若关系约束没有本轮真实样本，不必先实现完整谓词组合系统。

零操作数形式应通过新定义格式支持，例如固定编码的指令；不能为满足“至少一个 slot”人为伪造操作数。旧格式是否继续拒绝空 slots，按旧契约保留。

### 9.2 不在核心中解释 ISA 名称

新路径不得出现决定编码和合法性的以下模式：

```text
if isa == "new-isa" ...
match mnemonic ...
if form_id starts_with("x86:...") ...
```

ISA 特定事实应进入目标数据、目标资产编译检查或 legacy 兼容模块。legacy 中可暂留旧分支，但普通新包不得依赖继续往 legacy 分支加逻辑。

物化器只执行例如“位宽 5 的寄存器域”“来自这个 profile 的 PC 基点”“字段必须不等于该常量”这样的明确规则。

新协议中的操作数 role 是槽位绑定身份，不是核心语义开关。是否允许 symbol payload、使用哪种寄存器类别、是否存在隐含操作数，应来自包中的类型和槽位规则，不能再由 `role == "target"` 或某个 ISA 字符串猜出。HE-1 可以继续使用 reg/value/symbol 等有限字段载体，但必须保留目标类型身份；复杂操作数的字段投影不得自行选择寻址模式，也不能宣称已经实现完整上游 Operand Space。

### 9.3 约束必须能在运行入口验证

不能仅把硬编码检查从 Rust 移到某个作者脚本，然后让运行期无条件信任结果。

开发期可把目标检查编译为有限约束；运行期 bundle verifier 必须验证其结构、边界和能力，计划验证器必须执行影响合法性的约束。来源审查则负责这些约束是否真实符合 ISA。

### 9.4 Form 不应为所有数据值穷举

保留真正会改变编码形状的 form 区别，例如不同长度、opcode 路径、前缀族、地址形状。

由显式字段唯一决定的寄存器编码位、合法位移值和固定变换，不应一律拆成独立 form。这不是允许自动选择，而是避免把确定性计算误当成策略。

本轮不批量重命名或合并既有 form。先在新包作者层建立可复用生成方式，并证明生成后的规则和既有样本等价。

### 9.5 能力缺口处理

新包需要不存在的原语时，返回明确的 `unsupported-capability`。提交短能力提案，给出真实 ISA 需求、最小反例、输入上下文、确定性定义和负向测试。

禁止用原始字节 escape hatch 假装该指令族已被平台支持；禁止回退到 LLVM。计划中的普通数据片段仍可以存在，但不能计入受验证指令覆盖。

---

## 10. Fixup Profile：横向扩展最重要的第二边界

仅有模板包还不够。新目标的修补规则如果继续要求修改公共 `Transform` 和验证器大函数，扩展仍会集中到核心。

### 10.1 Profile 的职责

新路径中的 form/slot 应引用允许的 fixup profile。profile 固定：

- 它可以修补的字段和字段顺序；
- 引用目标类别；
- PC 基点、地址单位和缩放；
- 符号/addend 的取值来源；
- 允许的固定变换；
- 范围、有符号性和对齐；
- 配对关系、成员角色和跨成员约束；
- 是否支持原地解析、延迟记录或两者。

计划提供 profile ID、目标、addend、明确的解析模式和配对身份等实例事实。字段布局等已由版本化 profile 唯一决定的信息不必再重复手填。

如果同一 form 可以采用多种 profile，计划必须明确指定，不能由 materializer 猜测。

### 10.2 限定表达能力

HE-1 可以用少量固定、参数化的变换结构覆盖现有规则；不要求实现通用表达式解释器。

参数必须是已冻结常量或规定的上下文引用。禁止循环、递归、用户回调、搜索候选 form、追加指令或修改布局。

规则即使依赖配对成员，也必须声明观察哪些字段。不得通过访问任意全局计划状态形成隐藏决策。

### 10.3 必测配对语义

不能只测试“有一个 hi 和一个 lo”。至少覆盖同一符号、非零 addend、符号位进位、1:N low 使用者、不同起始 offset、不合法跨节引用、混合解析模式以及 profile 不兼容。

对 RISC-V 类 Hi/Lo，必须明确低半引用的是高半所用的目标表达式、PC 基点和 addend，不能让两个成员各自默默计算不同的值。

具体兼容组合应由 profile 约束；此处是待验证要求，不是对现有实现的已复现缺陷声明。

### 10.4 Legacy 处理

旧 FMP 的裸 `field_descriptor/transform` 路径通过版本固定的 adapter 保留。不能用一个“接受任意旧参数”的 profile 将旧路径变成安全绕过。

先迁移现有正例使用的 profile；新格式普通扩展必须使用 profile。对于此前错误接受的计划可以收紧拒绝，但要记录行为变化和回归用例。

ELF relocation 编号、REL/RELA 写法和链接器 relaxation 不在 HE-1 中完整实现。当前产物仍需明确标为规范化 fixup，而非已经可链接的目标文件。

---

## 11. 包级测试、证据和公共验证工具

### 11.1 一个语义权威实现

定义结构与约束检查以 Rust 库为权威。Python 检查脚本可以调用工具、核对文档和运行 oracle，不应长期维护另一份 ISA 白名单、位域合法性和变换语义。

现有脚本作为兼容 wrapper 保留到迁移完成。不要为了“统一”一次删除历史证据检查。

### 11.2 包应具备的独立验证

每个包的测试清单声明 form、case、oracle 和已知未验证项。至少包含：

- 每个导出 form 的正例；
- 合法边界与非法邻域，包括寄存器窗口、立即数、位移和 feature；
- 每种新规则的针对性反例；
- 有歧义编码的逐形式字节验证；
- 使用 fixup 的完整元数据和求值验证；
- 固定计划重复物化与错误重放；
- 可重跑的独立 oracle，或逐个样本登记的手工证据。

“每个 form 被出现一次”是下限，不是覆盖充分的证明。不要求一开始穷举全部操作数组合，但新包必须声明边界采样和遗漏。

独立反汇编可辅助检查，不足以独立证明选中了指定的精确编码形式。

### 11.3 Oracle 与跳过

保留已有明确登记的手工案例。新的跳过必须按 package/case ID 单独登记原因、证据和补证条件，不允许只有一个全局 skip reason 就无限增加跳过数量。

对重定位必须比较字段、目标、addend、PC 规则、配对和变换，不只比较记录数量。没有对象格式适配时，不能把规范化记录测试夸大为 ELF relocation 正确性。

### 11.4 资源与输入鲁棒性

补充有界性质测试和模糊测试入口，优先针对 JSON 深度、重复键、非法整数、模板/placement 边界、fixup 重叠和配对。

防止资源失控并不要求禁止 HashMap。可使用只参与查找而不决定输出遍历顺序的索引；输出顺序仍由冻结数组或明确规范化规则控制。使用 BTreeMap 是简化验证的可选实现，不是确定性的唯一实现。

---

## 12. 并行协作与 CI

### 12.1 普通扩展的变更预算

普通扩展 PR 的允许路径原则上为：

```text
packages/<target>/<owned-package>/**
```

必要时可提交独立发布清单 PR，但扩展包的测试和合并不应被全局发布清单阻塞。

普通扩展不得要求修改：

```text
prototype/crates/fmp-materialize/**
prototype/crates/fmp-validate/**        # 已存在能力下
schema/fmp-0.2.schema.json
tools/ 中的 ISA allowlist
docs/STATUS.md 的手写覆盖计数
其他包的 fixtures 和版本
```

共享类型和公共能力变更是另一类 PR，需明确标记影响面，不伪装成普通扩展。

### 12.2 消除中央文档锁

保留中心架构规范，但把常规扩展的说明放在包内。不再要求每新增一行编码就更新同一张大表、同一个状态文件、同一组连续编号。

中心目录、覆盖率和当前状态由包元数据生成。生成报告可作为 CI 产物或发布工序输出；普通 PR 不必提交全量再生成的大文件。

公共协议改变仍需 ADR。包内 form 增加使用包内决策 slug，不占用公共连续编号。

### 12.3 CI 层次

| 变更类型 | 必跑 |
|---|---|
| 单包数据/测试修改 | 包验证、该包及依赖它的受影响包测试、包 oracle、公共边界 smoke |
| 共享类型/profile 包修改 | 反向依赖闭包测试、bundle 冲突和兼容测试 |
| 核心、协议、构建器或规范化修改 | 全部新包、全部 legacy 夹具、跨主机一致性、oracle 基线 |
| 发布 bundle 修改 | 精确闭包重建、lock 校验、目标快照输出与旧 lock 重放 |
| 不确定的影响分析 | 退回全量测试，不能静默少跑 |

公共测试 harness 不应按 ISA 名称加入执行分支。oracle 的 target 参数和用例输入可以属于包测试数据，不同外部工具可以由受审查的适配器封装；这不等于要求所有 oracle 使用同一种命令行。

包发现和 job matrix 可由工具生成，不为每个新包手工添加一项 CI YAML。完整回归仍是合并/发布兜底，不能以“包独立”为由取消。

### 12.4 合并顺序不改变结果

对独立扩展 A、B，测试以下性质：

```text
Compose(Base, A, B) == Compose(Base, B, A)
```

这里的相等是同一显式包集合经过规范化构建得到的 bundle 执行摘要和目录相等，不是 Git commit hash 相等。

若 A、B 有真实命名/依赖冲突，两个次序都必须以确定性冲突失败，不能靠加载顺序选胜者。

### 12.5 许可和来源

每个包保留来源版本、引用范围、生成工具版本与 NOTICE。复用资产的许可判断不由文件扩展名或摘要自动完成；来源不清楚的包不能作为已审查发布包合并。

---

## 13. 分阶段重构任务

### H0：建立兼容与边界基线

**目标：** 先锁定本轮必须保持什么，再改结构。

读取仓库实际 HEAD；若与本文不同，提交差异清单。运行现有测试与检查，记录实际工具链、命令、正反例和跳过，不照抄历史统计。

建立 legacy 有效载荷快照、定义摘要清单和版本行为表。针对已验证对象可变性、摘要失配、错误定义配对和深层输入提出最小测试；未复现的结论标明状态。

**退出门槛：** 基线可一键重跑，已知风险有明确测试或未复现记录。不得以“先多加些 forms”替代。

### H1：封闭执行对象和身份

**目标：** 消除横向扩展前的身份与生命周期缺口。

私有化验证对象；绑定执行所用定义；建立唯一事实源；分开 plan、definition、artifact 和 implementation 身份；为旧入口保留受验证 facade。

静态能阻止的错误使用 compile-fail/API 测试，不能声称不可编译的篡改案例已经运行。通过序列化边界实施的篡改必须运行拒绝测试。

**退出门槛：** 在受支持 API 下，不能让不同执行事实冒用同一已验证身份；旧有效载荷不变。

### H2：包作者层和确定性构建

**目标：** 扩展不再人工编辑全量定义。

固定 package/lock 的最小契约，新增 `fmp-definition`。拆出三 ISA 各一个包，构建输出与对应旧 form 子集对比；此阶段允许暂输出 legacy 兼容快照。

实现唯一归属、精确依赖、路径边界和确定性规范化。共享检查以 Rust 为权威。

**退出门槛：** 两个不同包可独立测试；新包不会要求改中心表格；对照字节和定义语义无漂移。

### H3：新协议与通用加载边界

**目标：** 解除 ISA 闭集和全仓库加载耦合。

增加最小 `fmp/0.2` 与 bundle reader；目标身份由快照声明，能力由内核检查；旧协议通过 legacy adapter 保留。

加载明确 lock 的闭包，不读取未选中包。新增合成目标仅需添加数据和测试。支持零操作数形式，避免用假操作数绕过结构限制。

**退出门槛：** 新目标命名空间不修改公共白名单；未知能力严格拒绝；未选中包损坏不影响既有 bundle 的物化。

### H4：Fixup/profile 与包级一致性工具

**目标：** 普通修补规则扩展不再修改核心分支。

将现有代表性 PC-relative、AArch64 page、RISC-V Hi/Lo 规则表达为目标 profile，底层复用固定原语。绑定 form/slot 与 profile，补充非零 addend、配对、范围、字段所有权测试。

落地包级 oracle、错误、身份和回放 harness，以及资源上限测试。

**退出门槛：** 新增使用已有原语的 profile 只改包；完整元数据被校验；核心中不新增以目标名称分派的执行逻辑。

### H5：并行扩展演练与 HE-1 验收

**目标：** 用实际工作流证明平台可扩展。

冻结共享核心提交和能力集，然后至少建立三个独立工作流：

- 工作流 A：同一 ISA 中的包 A；
- 工作流 B：同一 ISA 中与 A 不重叠的包 B；
- 工作流 C：另一 ISA 的包 C。

三个真实 ISA 都必须在新路径有代表性包；合成新目标另作边界测试。每个工作流只增加少量样本，用于证明局部变化，不追求覆盖数量。

分别测试 A→B→C、C→B→A 的组合；测试旧 lock 在加入这些包后仍重放；核查各 PR diff 是否越过允许路径。

**退出门槛：** HE-AC-01 至 HE-AC-12 全部有证据。完成后停止，提交 HE-1 验收报告；后续覆盖工作由独立包任务推进。

### 13.1 阶段依赖与并行范围

H0 是共同前提。H1 的执行安全与 H2 的包契约设计可在接口明确后分工；H3 需要二者提供稳定边界。H4 与包测试迁移可并行。H5 必须在公共能力集冻结之后进行，否则“每条工作流都改核心”不构成通过。

一次性基础设施重构有顺序依赖是正常的。目标是让重构后的日常 ISA 扩展不再重复依赖这条纵向链。

每阶段以可回归的小 PR 交付，禁止单个 PR 同时重写内核、改全部历史定义、升级协议并新增大量指令。

---

## 14. 最小验收测试表

| Test ID | 操作 | 必须结果 |
|---|---|---|
| HE-T01 | 读取所有旧定义与旧正例 | 旧机器码/节/符号/fixup 载荷保持；身份兼容按版本规则检查 |
| HE-T02 | 修改原始 DTO 后尝试复用已有验证凭证 | 凭证不受影响，或必须重新验证并生成新身份 |
| HE-T03 | 篡改定义内容但保留声明摘要 | 加载/绑定拒绝 |
| HE-T04 | 验证时使用 A，执行时试图替换成 B | API 不可表达或拒绝，不得成功 |
| HE-T05 | 随机化目录和清单发现顺序 | 同一显式闭包产生相同 bundle 摘要 |
| HE-T06 | 新增或损坏未选中包 | 已冻结 bundle 的物化不变；不扫描该包 |
| HE-T07 | 两包导出相同 form ID | 确定性冲突，不 last-wins |
| HE-T08 | 依赖缺失、摘要错、环、两个不兼容精确版本 | 明确拒绝，不隐式选择 |
| HE-T09 | 包要求不存在的能力 | unsupported-capability，不回退 |
| HE-T10 | form 使用错误 profile 或手动弱化范围 | 拒绝 |
| HE-T11 | Hi/Lo 非零 addend、边界进位和多 low | 与独立 oracle/数学推导一致 |
| HE-T12 | profile 覆盖 opcode、寄存器位或重叠字段 | 拒绝 |
| HE-T13 | 深层 JSON、超大清单、越界 placement | 有界拒绝，不进程崩溃或无界消耗 |
| HE-T14 | 三 ISA 同一 conformance harness | 无 ISA 专用测试执行器分支才能通过 |
| HE-T15 | 新合成目标命名空间 | 包级变更完成；不改核心 family 列表 |
| HE-T16 | A+B 与 B+A 合并/构建 | 同一闭包同一执行产物 |
| HE-T17 | 新包只使用已有能力 | PR diff 不触碰禁止路径 |
| HE-T18 | 精确字节、fixup 完整元数据、错误值边界 | 不是仅比较长度、记录数量或错误字段名 |
| HE-T19 | 生成器/工具版本不同但产物相同 | 执行定义摘要相同，构建来源记录可区分 |
| HE-T20 | 构建版本变化 | implementation ID 可追踪；不借元数据变化掩盖载荷差异 |

HE-T19 只适用于规范中明确排除构建来源元数据的执行摘要。包源码摘要和构建收据可以不同。

主机故障不纳入“同一非法计划规范化错误必须相同”的测试；应验证其单独分类，不把环境不足误报成机器计划不合法。

---

## 15. 兼容性、回滚和风险控制

### 15.1 兼容性分类

| 变化 | 规则 |
|---|---|
| 历史定义文件及摘要 | 不原地改变 |
| 旧合法计划的机器输出与修补载荷 | 必须保持 |
| 旧 fingerprint | 继续按原版本算法解释；不无声改义 |
| 新协议 plan/bundle 身份 | 使用新版本定义，不与旧 fingerprint 混用 |
| materializer_version / 构建收据 | 允许真实版本变化，专门记录并更新元数据断言 |
| 旧实现错误接受的输入 | 可收紧拒绝；必须有反例和变更记录 |
| 旧诊断代码、路径及细节 | 尽量保持；新增严格检查的差异显式登记 |

不能要求“新的实现版本元数据”和“旧整个输出 envelope 字节”同时不变，再通过伪报旧版本解决矛盾。

### 15.2 回滚

旧输入读取与 legacy 执行语义在新路径完全验收前必须可用。新包构建、包目录和协议 reader 可逐阶段启用，默认行为切换单独提交。

新路径失败时必须报告错误。所谓回滚是部署/版本层面的显式切换，不是一次物化失败后自动换成旧 encoder。

### 15.3 主要风险

**规则语言膨胀：** 优先复用已有定长位域和固定变换；只为真实缺口新增原语。

**形式数量膨胀：** 作者层复用和受控生成，不用上游隐式选择换取表大小；不在本轮大改既有 ID。

**包很独立但发布仍锁死：** 包测试与合并不依赖中心 release manifest；bundle 发布由后续集成步骤完成。

**双重语义实现漂移：** Rust 为结构与语义权威，Python 不再平行实现新核心规则。

**只移动代码不移动权限：** 验收检查依赖方向、变更范围和实际并行合并，而不是统计 crate 数量。

**过早追求完整通用性：** HE-1 只保证已有能力集内的扩展；新的真实机制需求以能力提案处理。

---

## 16. 明确不做

本轮不做完整原子语义语言、不做自动指令选择、不做 ABI 参数/栈帧降低、不做布局求解器、不做完整对象文件后端、不做全 ISA 导入、不做远程包注册中心、不做运行时动态插件、不做通用表达式/宏系统，也不要求重写为 Zig、C++ 或其他语言。

不要求一次迁移全部历史定义；不要求一次消除所有 legacy 分支。允许暂存兼容复杂性，但必须有清楚边界，不让新扩展继续依附它增长。

不将“全部 invariants 已证明”作为文档修辞。验收报告应写明已测试范围、仅源码判断项和仍未覆盖的属性。

---

## 17. 交付物

建议提交以下少量权威文档，避免重新制造中心文档负担：

```text
docs/architecture/he1-horizontal-extension.md
docs/architecture/package-contract.md
docs/architecture/bundle-identity.md
docs/architecture/extension-conformance.md
docs/architecture/he1-acceptance.md

research/he1/
  baseline.md
  compatibility-results.json
  parallel-extension-results.json
  unresolved-capabilities.md
```

对应代码产物包括：不可变验证边界、`fmp-definition`、legacy adapters、最小包/lock/bundle 工具、三个真实 ISA 代表包、共享 conformance harness、合成目标探针和并行演练包。

工具命令名称由实现固定。文档中可以先描述 `package check/build/test`、`bundle build/verify` 的职责，但不得把尚未实现的命令当成可运行接口写入验收记录。

### 17.1 验收报告必须回答

1. 普通扩展是否确实不改核心？给出实际 PR diff/path 报告。
2. 两个同 ISA 工作流是否能独立合并？给出两种合并顺序的构建摘要。
3. 未选中包是否完全不能影响旧计划？给出缺失、损坏、增加包的测试。
4. 身份是否对应实际执行对象？给出 API 和篡改测试。
5. 哪些新目标需求仍需要新增原语？列出明确 capability gap。
6. 哪些旧输入收紧了拒绝？列出兼容差异，不隐藏在基线更新中。
7. 下一批工作是否可以直接按包分发，而不继续共同编辑一个大文件？

---

## 18. 可直接交给本地 Agent 的执行指令

你要将 MonAsm 推进到 HE-1，而不是完成最终汇编器。

先读取当前仓库约束和本文，固定实际 HEAD。若现有 AGENTS/ADR 与本轮目标冲突，提出一份范围明确的替代 ADR，由本轮明确授权的方向解决冲突；不要静默忽略旧规则，也不要因旧规则要求每次修改中心表格而拒绝开展重构。

首先复跑基线并核实历史审计风险。随后以小 PR 封闭执行对象身份，建立包作者层、精确依赖、不可变 bundle、新协议边界、profile 和包级 conformance。保留历史资产与有效载荷。

先证明一个真实切片，再扩展到三个 ISA。公共能力集固定后，安排至少三个独立扩展工作流，其中两个属于同一 ISA。普通扩展仅修改自己的包与证据，不能通过公共代码变更偷偷完成验收。

不新增优化、自动编码选择、自动布局、运行时宏或目标可执行插件。不得以支持更多 forms 掩盖扩展底座尚未成立。

每阶段报告修改范围、运行命令、实际结果、兼容差异和未验证项。不能把构建计划、源码推断或 CI 配置视为已运行结果。

所有 HE-AC 通过后停止，交付 HE-1 验收报告和后续独立包任务模板；不要自行开始新一轮纵向覆盖扩张。

---

## 19. 固定提交源码索引

以下是本设计的现状依据；上文新增 API、包格式、目录和阶段均为设计提案，不是当前仓库已有能力。

- [S1] 提交基线：<https://github.com/Mr-enthalpy/MonAsm/commit/d0082f9f2d3da2786d8d1c0467d2793369ec9090>
- [S2] 公开定义对象和位域模型：<https://github.com/Mr-enthalpy/MonAsm/blob/d0082f9f2d3da2786d8d1c0467d2793369ec9090/prototype/crates/fmp-model/src/definition.rs#L20-L166>
- [S3] ISA form ID 分支和全目录 Registry：<https://github.com/Mr-enthalpy/MonAsm/blob/d0082f9f2d3da2786d8d1c0467d2793369ec9090/prototype/crates/fmp-model/src/definition.rs#L714-L850>
- [S4] 当前定义检查脚本：<https://github.com/Mr-enthalpy/MonAsm/blob/d0082f9f2d3da2786d8d1c0467d2793369ec9090/tools/check_definition.py#L1-L165>
- [S5] 模板/位域执行器：<https://github.com/Mr-enthalpy/MonAsm/blob/d0082f9f2d3da2786d8d1c0467d2793369ec9090/prototype/crates/fmp-materialize/src/lib.rs#L557-L648>
- [S6] 旧 Schema 的目标闭集：<https://github.com/Mr-enthalpy/MonAsm/blob/d0082f9f2d3da2786d8d1c0467d2793369ec9090/schema/fmp-v0.schema.json#L29-L65>
- [S7] 当前 fingerprint：<https://github.com/Mr-enthalpy/MonAsm/blob/d0082f9f2d3da2786d8d1c0467d2793369ec9090/prototype/crates/fmp-materialize/src/lib.rs#L919-L936>

**最终验收原则：不是证明一个人可以继续往下实现，而是证明多个实现者可以在不争夺公共核心的前提下同时往旁边扩展。**

# Frozen Machine Plan v0
## 跨架构确定性物化器：本地 Agent 研究任务书与契约草案

**文档状态：** Research Directive / Contract Draft v0  
**目标架构：** x86-64、AArch64、RV64  
**核心技术参考：** XirAsm / XirAsm-lib、LLVM MC / TableGen  
**任务性质：** 源码研究、契约设计、最小原型、实验验证  
**非目标：** 再次开展大规模汇编器横向比较

---

# 0. 任务定义

本任务的目标是提出并验证一个最小但完整的 **Frozen Machine Plan v0（以下简称 FMP v0）**。

FMP v0 是上游规划器与下游确定性物化器之间的冻结契约。

其职责不是描述“程序希望做什么”，而是描述：

> 在一个确定的目标机器定义下，已经完成指令选择、操作数约束、编码形式选择、布局决策与修补决策的一组机器事实。

物化器只允许：

1. 校验计划是否完整、合法且适用于目标定义。
2. 按冻结计划执行编码。
3. 生成字节与明确规定的 fixup/relocation 记录。
4. 对非法、不完整或不一致的计划给出确定性错误。

物化器不允许：

1. 推断上游意图。
2. 自主选择机器指令。
3. 自主选择等价编码形式。
4. 自主扩展指令序列。
5. 自主进行分支松弛、跳板生成或重新布局。
6. 自主执行宏、脚本、表达式求值或元编程。
7. 根据未冻结的环境状态改变输出。

研究必须回答三个核心问题：

- **表达完备性：** FMP v0 至少需要冻结哪些信息，才能消除编码阶段的隐式决策？
- **跨架构边界：** 哪些结构可以跨 ISA 统一，哪些必须保留为目标特定的类型与规则？
- **可验证性：** 如何证明物化器只是执行计划，而没有偷偷成为另一个规划器？

---

# 1. 已确定的技术方向

以下决定视为本任务的前提，不应在研究中反复重新争论。

## 1.1 总体分层

系统划分为三个逻辑层：

```text
Atomic Semantic IR
        |
        | instruction selection
        | operand legalization
        | encoding-form selection
        | layout / relaxation
        | fixup planning
        v
Frozen Machine Plan
        |
        | validation
        | deterministic encoding
        | deterministic fixup recording
        v
Bytes + Fixup Records
```

### Layer A：Atomic Semantic IR

这一层采用有限、原子的代数式操作描述语义意图。

示意操作包括：

- `Transfer(Dst, Src)`
- `Compute(Op, Dst, SrcA, SrcB)`
- `Branch(Cond, Target)`
- `Jump(Target)`
- `Invoke(Target, ParamPlan)`
- `Fence(Scope)`

这些只是语义层示例，不构成 FMP v0 的最终 API。

尤其需要注意：

`Transfer` 不能直接等价于一条机器 `mov`。

`Compute` 不能自动确定机器指令、立即数宽度、标志寄存器副作用或编码形式。

`Invoke` 不能要求物化器承担 ABI 参数分配、栈帧生成或调用约定降低。

**所有这些选择都必须在进入 FMP 前完成。**

### Layer B：Frozen Machine Plan

FMP 描述已经决定的机器事实。

它不是通用语义 IR，不是传统汇编文本，也不是可继续优化的 Machine IR。

其核心组成预计包括：

- 目标定义标识
- 机器指令形式
- 类型化机器操作数
- 编码选择
- 逻辑布局
- 符号与引用
- fixup / relocation 计划
- 输出工件契约

### Layer C：Deterministic Materializer

物化器必须尽可能保持“愚笨”。

它可以包含复杂的编码规则和合法性校验，但不能包含未经契约授权的选择策略。

**复杂的编码知识是允许的；隐式编码决策权是不允许的。**

---

# 2. 技术栈与复用原则

## 2.1 XirAsm / XirAsm-lib

XirAsm 是本研究优先考察的结构参考，XirAsm-lib 是优先验证的复用候选。

本地 Agent 必须实际检查源码，不能仅依据 README、API 名称或二手描述判断其能力。

重点研究：

1. 核心数据结构与对象生命周期。
2. 指令、操作数、目标架构的表达方式。
3. 编码入口是否可以直接接受已经选定的机器形式。
4. 编码过程中是否存在自动选择、自动缩短、自动扩展或状态相关行为。
5. 是否能够绕过高层策略，直接复用低层编码能力。
6. 是否能够稳定导出字节、偏移、fixup 信息。
7. 是否存在宏系统、布局策略或隐式全局状态耦合。
8. API、许可证、构建方式及版本兼容约束。

研究结论必须把复用能力分为：

- **A：可直接复用**，不引入隐式决策。
- **B：可通过薄适配层复用**，决策权仍由 FMP 掌握。
- **C：需要局部改造或拆分**，才能符合确定性契约。
- **D：不宜复用**，会引入不可接受的策略耦合。

不得预设 XirAsm-lib 一定具备满足 FMP 的直接编码 API。

## 2.2 LLVM MC / TableGen

LLVM 的定位是成熟的跨架构机器编码知识来源与校验参考。

重点研究：

- Machine instruction definition 与编码描述。
- 指令形式标识及其稳定性。
- Operand class、register class 与约束。
- 固定位、可变位、立即数字段及重排。
- MCCodeEmitter 的编码行为。
- MCFixup、relocation、目标相关 fixup 语义。
- 分支位移、PC-relative 基准及缩放规则。
- MCAssembler、relaxation 与布局职责的边界。

必须区分：

**可以借鉴的内容：**

- 指令编码规则
- 类型约束
- 字段映射
- fixup 规则
- 目标特定知识
- 测试向量

**不能未经审查直接继承的内容：**

- 自动指令选择
- 自动分支松弛
- 自动编码形式优化
- 隐式 layout policy
- 依赖可变上下文的编码行为

LLVM 内部枚举值、opcode 编号或 TableGen 生成顺序不得未经证明就成为 FMP 的持久化稳定标识。

## 2.3 其他工具

允许使用 GNU binutils、LLVM 工具、objdump、readelf、目标架构反汇编器或其他独立编码器作为验证工具。

但不得重新展开广泛的汇编器产品比较。

使用这些工具的唯一主要目的，是构建测试 oracle、验证字节、检查重定位语义，以及定位分歧。

---

# 3. FMP v0 的核心不变量

以下不变量必须转化为机器可执行的测试。

## INV-01：无隐式指令选择

每条计划中的机器指令必须具有明确的目标 ISA 指令形式。

物化器不得根据语义操作自行选择机器指令。

## INV-02：无隐式编码形式选择

当同一语义指令存在多种可观测编码形式时，FMP 必须明确区分它们。

例如：

- x86-64 的立即数宽度、位移宽度与前缀形式。
- x86-64 的 VEX / EVEX 等编码族。
- AArch64 的目标指令变体与相关字段。
- RISC-V 的标准宽度与压缩形式。

物化器不得依据“更短”“更快”“更常见”等偏好自行决定。

## INV-03：无隐式指令扩展

一条计划指令不得在物化阶段自动变成多条指令。

伪指令、常量物化序列、长距离跳转序列必须在上游展开。

## INV-04：无隐式布局修改

物化器不得自行：

- 插入未计划的对齐填充。
- 改变指令顺序。
- 扩展分支。
- 插入跳板。
- 移动符号位置。
- 改变节的布局。

如果计划不合法，必须拒绝。

## INV-05：无隐藏环境依赖

相同的冻结计划、相同的目标定义、相同的物化器实现版本和相同的显式输出配置，必须得到相同的规范化结果或相同的规范化错误。

不能依赖：

- 主机 CPU 类型。
- 非显式环境变量。
- 系统时间。
- 随机数。
- 进程地址。
- 哈希表非稳定遍历顺序。
- 外部汇编器的默认配置。

## INV-06：无元编程执行

FMP 不得包含会在物化阶段执行的宏、循环、条件编译、脚本、插件回调或任意表达式语言。

允许静态、受约束的数据结构；不允许运行时生成计划内容。

## INV-07：严格拒绝

非法编码形式、操作数类型不匹配、立即数越界、位移越界、目标不匹配、fixup 语义不支持等情况必须明确报错。

不得静默修复。

## INV-08：可重放与可追溯

每次输出都必须能够追溯到：

- 冻结计划内容。
- 目标定义。
- 物化器版本。
- 规范化编码选项。
- 产生的字节与 fixup。

研究需要设计规范化摘要或内容哈希机制。

---

# 4. FMP v0 的概念数据模型

以下为候选模型，不是最终定稿。

本地 Agent 应基于源码证据与实验，对每个字段提出保留、修改、删除或拆分建议。

```text
FrozenMachinePlan
  format_version
  target_identity
  definition_identity
  output_contract
  sections[]
  symbols[]
  instructions[]
  fixups[]
  provenance?
```

## 4.1 Target Identity

至少研究以下字段：

```text
TargetIdentity
  isa_family
  isa_variant
  execution_mode
  enabled_extensions[]
  feature_constraints[]
  byte_order
  address_width
```

注意区分：

- 影响指令编码合法性的目标属性。
- 影响运行语义但不改变编码的目标属性。
- 影响对象文件格式的输出属性。

不得把 ISA、ABI、对象格式、主机平台混为一谈。

## 4.2 Definition Identity

必须设计一种能够标识编码规则集合的机制。

候选字段：

```text
DefinitionIdentity
  definition_namespace
  definition_version
  definition_digest
```

目标是避免同一个形式名称在不同定义版本中产生不同字节而无法检测。

研究需要回答：

- 是否需要规范化规则摘要？
- 哪些规则必须参与摘要？
- LLVM TableGen 生成结果是否能成为规则输入？
- XirAsm-lib 的编码实现版本如何绑定？
- 编码规则变更后，旧 FMP 如何拒绝或兼容？

## 4.3 Instruction Form

候选模型：

```text
FrozenInstruction
  instruction_id
  section_id
  offset
  form_id
  operands[]
  encoding_choices
  expected_size
  source_trace?
```

`form_id` 必须指向一个确定的机器编码形式，而不是仅指向一个模糊的助记符。

研究需要区分：

1. ISA 指令的语义身份。
2. ISA 编码形式身份。
3. 编码实例中的可变字段。
4. 编码实现内部的临时编号。

优先研究**语义稳定、定义版本绑定的形式标识**，而非直接持久化某个库内部的 opcode 整数。

## 4.4 Typed Operand

不得设计一个强迫所有 ISA 共享语义的“万能操作数类”。

允许统一结构载体，但操作数具体类型与合法性由目标定义控制。

候选：

```text
TypedOperand
  role
  kind
  target_type
  payload
  modifiers
```

需要研究的类别：

- Register reference
- Immediate value
- Encoded field value
- Memory addressing form
- Symbol reference
- Relative displacement
- Register list / tuple
- Predicate / condition
- Target-specific modifier

必须明确：

**操作数的抽象统一，不等于硬件语义的统一。**

例如 x86 memory operand、AArch64 addressing form、RISC-V base-plus-offset 不应被强行压缩成一个语义含混的通用 `Memory(base, index, scale, displacement)`。

可以共享结构协议，但应保留目标专属的类型系统。

## 4.5 Encoding Choices

这是 FMP v0 的重点。

本地 Agent 需要建立一个清单：

> 哪些选择会改变输出字节，但不能仅由 `form_id + operands + target` 唯一推导？

对每项选择判断：

- 是否应体现在 `form_id`？
- 是否应体现在操作数类型？
- 是否应成为显式 encoding choice？
- 是否属于布局或 fixup？
- 是否属于规则定义本身的确定性编码算法？

避免两个极端：

1. **冻结不足：** 编码器仍然需要选择。
2. **冻结过度：** 每一位机器码都由上游手工指定，使编码规则库失去意义。

建议的判定标准：

如果某项字段的取值在冻结输入与版本化规则确定后已经唯一，则允许编码器计算它。

如果存在多个合法且可观测不同的输出，则必须由 FMP 或其引用的规则明确消除歧义。

## 4.6 Layout

候选模型：

```text
SectionPlan
  section_id
  section_kind
  base_address?
  declared_size
  fragments[]
```

```text
Fragment
  offset
  size
  kind
  payload
```

研究应覆盖：

- 指令片段。
- 原始数据片段。
- 显式填充片段。
- 符号位置。
- 已知地址与未绑定地址。
- 节内偏移。
- 跨节引用。

**v0 原则：所有影响布局的字节数必须在进入物化器之前确定。**

对齐可以由上游计算并冻结为明确的填充片段；物化器不得自行决定填充数量。

## 4.7 Symbol 与 Fixup

建议将以下概念明确分离：

- Symbol identity
- Symbol definition / declaration
- Symbol reference
- Fixup site
- Fixup kind
- Relocation representation
- Resolution policy

候选：

```text
FixupPlan
  fixup_id
  section_id
  offset
  field_descriptor
  target_reference
  addend
  pc_reference_rule
  value_transform
  range_constraint
  resolution_mode
```

这些字段仅为研究起点。

特别需要检验：

- PC-relative 基准点。
- 有符号位移。
- 缩放位移。
- 分散位字段。
- 指令字节序与字段位序。
- addend 的语义。
- REL / RELA 等重定位表示差异。
- AArch64 成对或关联 relocation。
- RISC-V HI/LO 及其他关联修补。
- x86-64 不同宽度的相对引用。

不得假设所有 fixup 都是简单的连续字节补丁。

---

# 5. 必须明确的边界问题

## 5.1 FMP 是否保存最终字节？

研究至少比较三种方案：

**方案 A：仅保存形式、操作数和编码选择。**

字节由物化器完全生成。

**方案 B：保存形式、操作数、编码选择及可选 expected bytes/hash。**

物化器生成字节并进行一致性校验。

**方案 C：保存完整字节模板及显式修补字段。**

物化器主要执行校验和补丁操作。

要求给出比较：

- 可验证性
- 可移植性
- 与 XirAsm-lib 的复用程度
- 与 LLVM 编码知识的结合程度
- 计划体积
- 版本稳定性
- 隐式决策风险

可以考虑 B 作为候选基线，但必须由实验验证，不能直接宣布其最优。

## 5.2 Fixup 应在何时应用？

至少研究：

1. 完全已知的节内引用。
2. 已知绝对地址的引用。
3. 未解析外部符号。
4. 跨节但对象格式支持的引用。
5. 超出当前编码范围的引用。

需要确定 v0 的 resolution mode。

不得把“生成 relocation record”和“完成符号解析”混为一谈。

## 5.3 物化器输出到什么层次？

区分三个输出级别：

- **Level 0：** 裸字节及规范化 fixup records。
- **Level 1：** 已布局的 section images、symbol table 和 relocation records。
- **Level 2：** ELF、COFF、Mach-O 等完整对象文件。

优先验证 Level 0 或 Level 1。

Level 2 不应成为 v0 成功的必要条件，除非实验表明缺少对象格式语义会使关键 fixup 契约无法定义。

如果支持完整对象文件，还必须冻结节顺序、符号顺序、重定位顺序、填充、元数据等影响最终字节的因素。

## 5.4 规范化与哈希

需要明确：

- FMP 的逻辑等价性与序列化字节等价性是否相同。
- 字段排序规则。
- 未知字段处理策略。
- 扩展字段的版本兼容。
- 哈希包含哪些目标定义与输出配置。
- 错误是否有稳定的结构化表示。

不要使用依赖进程内对象地址或非稳定枚举顺序的哈希方法。

---

# 6. 三架构最小实验矩阵

研究不追求完整 ISA 覆盖。

每种 ISA 只需选择足以暴露关键设计问题的样本。

## 6.1 x86-64

必须覆盖：

1. 寄存器到寄存器的数据传送。
2. 立即数参与的算术运算。
3. 同一操作的不同合法编码形式。
4. 位移宽度差异。
5. REX 等前缀相关规则。
6. RIP-relative 地址引用。
7. 短分支与近分支。
8. 外部调用的 fixup / relocation。
9. 一个需要显式选择编码族的扩展指令案例（如适用）。

重点验证：

- 编码长度是否被完整冻结。
- 相同语义下的多个编码是否被清晰区分。
- 分支超界是否严格拒绝。
- 是否存在库内部自动选择较短形式的行为。

## 6.2 AArch64

必须覆盖：

1. 寄存器算术。
2. 带立即数的算术。
3. Load/store 地址形式。
4. 条件分支。
5. 无条件分支或调用。
6. ADR/ADRP 或等价的 PC-relative 案例。
7. 至少一个分散位字段或缩放立即数案例。
8. 一个目标特定修饰符案例。

重点验证：

- 固定指令宽度并不意味着编码选择已经消失。
- 立即数合法范围、缩放和字段映射必须显式校验。
- PC-relative 的基准与修补规则必须明确。
- 关联 relocation 不得被简化为无关的独立补丁。

## 6.3 RV64

必须覆盖：

1. 标准整数算术。
2. I-type 立即数。
3. Load/store。
4. 条件分支。
5. JAL 或相关控制转移。
6. 分散位字段。
7. RVC 压缩形式与非压缩形式的显式区别。
8. AUIPC + LO12 等关联引用案例。

重点验证：

- 压缩形式选择不得发生在物化阶段。
- 分支范围不足不得触发隐式扩展。
- 分散位编码必须可由规则确定性生成。
- 关联 fixup 的身份与关系必须被表达。

---

# 7. 关键负向测试

正向编码正确并不足以证明 FMP 成立。

必须主动构造非法计划，验证物化器是否拒绝。

至少包含：

| 测试 | 输入情况 | 预期 |
|---|---|---|
| N01 | 缺少必要 encoding choice | 拒绝 |
| N02 | 操作数寄存器类别不匹配 | 拒绝 |
| N03 | 立即数超出编码范围 | 拒绝 |
| N04 | 分支位移超界 | 拒绝，不扩展 |
| N05 | 声明大小与实际编码长度不一致 | 拒绝 |
| N06 | 目标扩展未启用 | 拒绝 |
| N07 | fixup 类型与字段不匹配 | 拒绝 |
| N08 | 引用不存在的符号 | 按明确 resolution policy 拒绝 |
| N09 | 布局片段重叠 | 拒绝 |
| N10 | 目标定义摘要不匹配 | 拒绝 |
| N11 | 尝试隐式插入对齐填充 | 拒绝 |
| N12 | 使用未支持的关联 relocation 组合 | 拒绝 |

错误应包含稳定的类别、相关计划节点标识和必要诊断信息。

不能仅用“assembler failed”作为合格的错误结果。

---

# 8. 确定性重放实验

至少开展以下实验。

## EXP-R1：重复执行

同一计划重复物化多次。

验证输出字节、fixup records 和规范化错误完全一致。

## EXP-R2：跨进程

在多个独立进程中运行相同计划。

验证结果一致。

## EXP-R3：不同主机环境

在条件允许时，使用不同操作系统、编译器构建或主机 CPU 运行。

验证逻辑输出一致。

如果无法实际测试，必须标记为未验证，不能宣称已证明跨平台确定性。

## EXP-R4：输入序列化重放

将 FMP 序列化、反序列化，再执行。

验证结果一致。

## EXP-R5：定义版本扰动

修改或替换编码规则定义版本。

验证系统能明确识别不兼容定义，而不是悄悄生成不同字节。

## EXP-R6：负向确定性

同一非法计划重复执行。

验证错误类别与结构化定位一致。

允许错误文本包含额外诊断信息，但不得影响规范化错误身份。

---

# 9. 本地 Agent 的源码研究方法

## 9.1 先盘点本地环境

首先识别：

- 仓库路径。
- XirAsm / XirAsm-lib 的实际版本、提交号。
- LLVM 的实际版本、提交号。
- 构建工具链。
- 已有测试工具。
- 可用目标架构。
- 可运行的编码器与反汇编器。

如果相关仓库不存在，应先记录缺失情况，再按允许的网络和依赖策略获取。

不得编造源码路径、API 或版本。

## 9.2 建立证据索引

每条重要技术结论应提供：

```text
Evidence
  repository
  revision
  file_path
  symbol_or_function
  line_range
  observed_behavior
  interpretation
  confidence
```

尽可能附最小可复现实验。

必须区分：

- 源码直接证明。
- 运行实验观察。
- 文档描述。
- 研究者推断。
- 尚未验证的假设。

## 9.3 先追踪真实编码路径

对 XirAsm-lib 与 LLVM，分别追踪：

```text
Input instruction representation
    -> validation
    -> encoding-form determination
    -> field encoding
    -> byte emission
    -> fixup creation
    -> output
```

逐节点标注：

- 读取哪些状态。
- 是否存在选择策略。
- 是否可能改变编码长度。
- 是否可能增加指令。
- 是否依赖布局。
- 是否可以在 FMP 边界外预先完成。

重点是找到**最小的策略隔离边界**。

## 9.4 不得仅通过 API 名称推断行为

例如：

`encode()` 不一定代表无策略编码。

`emit()` 不一定代表不会自动扩展。

`fixup()` 不一定具有跨 ISA 统一语义。

所有关键判断都应追踪到实际调用链或测试行为。

---

# 10. 最小原型要求

原型不要求覆盖完整架构，但必须真正执行编码。

建议实现以下接口概念：

```text
validate(plan, definition) -> ValidationResult

materialize(plan, definition) ->
    MaterializationResult {
        section_images,
        fixup_records,
        diagnostics
    }
```

可增加：

```text
canonicalize(plan) -> CanonicalPlan

fingerprint(plan, definition) -> Digest

verify_replay(plan, expected_result) -> VerificationResult
```

这些接口名称仅供参考。

具体语言、序列化格式和内部模块划分由研究结果决定。

## 10.1 必须有两种独立验证手段

每个正向样本至少需要：

1. 被研究物化路径生成的结果。
2. 一个可信的独立参考结果。

独立参考可以是 LLVM 工具链、GNU 工具链、ISA 手册推导或另一独立实现。

不得仅让同一编码函数生成 expected bytes，再用自身结果证明自身正确。

## 10.2 必须能观测隐藏决策

原型应记录必要的决策审计信息。

例如：

- 进入物化器时的 form ID。
- 实际使用的编码形式。
- 编码长度。
- 编码规则版本。
- fixup 类型与位置。
- 是否尝试调用 relaxation / fallback / instruction selection 路径。

如果底层库会自动做出选择，不能仅因为最终字节正确就判定符合契约。

必须证明这些选择已经被固定，或能够被禁用、约束、审计。

## 10.3 优先选择纵向切片

先打通每个架构一条最小路径：

```text
FMP input
  -> parse
  -> validate
  -> encode
  -> collect fixups
  -> compare oracle
  -> replay
```

不要先建设大而全的 IR 框架、完整对象文件写入器或宏系统。

---

# 11. 建议的研究阶段

## Phase 0：环境与证据基线

任务：

- 固定源码版本。
- 确认构建和测试工具可用。
- 建立证据目录。
- 列出关键技术风险。

产物：

`00_environment_and_evidence.md`

## Phase 1：策略边界审计

任务：

- 追踪 XirAsm-lib 的实际编码调用链。
- 追踪 LLVM MC/TableGen 的关键编码与 fixup 路径。
- 标出所有隐式决策点。
- 评估哪些组件可以复用。

产物：

`01_encoder_boundary_audit.md`

`01_reuse_matrix.md`

## Phase 2：FMP 契约设计

任务：

- 定义最小数据模型。
- 定义形式标识规则。
- 定义 operand 类型协议。
- 定义 encoding choices。
- 定义 layout、symbol、fixup。
- 定义版本绑定和错误模型。

产物：

`02_fmp_v0_contract.md`

`02_fmp_v0_schema.*`

`02_open_decisions.md`

## Phase 3：三架构纵向原型

任务：

- x86-64 最小编码与 fixup。
- AArch64 最小编码与 fixup。
- RV64 最小编码与 fixup。
- 建立独立 oracle 对照。

产物：

`prototype/`

`03_cross_isa_test_matrix.md`

## Phase 4：不变量与重放验证

任务：

- 执行全部适用负向测试。
- 执行重复、跨进程、序列化重放。
- 验证版本不匹配行为。
- 审计物化路径是否调用隐式策略。

产物：

`04_invariant_results.md`

`04_replay_results.md`

## Phase 5：收敛与决策

任务：

- 修订 FMP v0。
- 划定 v0 支持范围。
- 列出暂不支持的 ISA 特性。
- 明确下一阶段实现路线。

产物：

`05_final_recommendation.md`

---

# 12. 必须回答的研究问题

最终报告不得回避以下问题。

### Q1. 什么是最小充分冻结信息？

给出明确字段集，并用实际反例解释每个关键字段为什么必要。

### Q2. `form_id` 的稳定身份如何定义？

不能直接假设内部 opcode 编号具有跨版本稳定性。

### Q3. 什么情况下物化器仍然需要选择？

逐项列出残留选择，并说明如何消除、显式化或判定为不影响可观测结果。

### Q4. 编码规则与计划数据的分界在哪里？

哪些知识由版本化 target definition 提供，哪些事实必须存在于 FMP 实例中？

### Q5. XirAsm-lib 能否作为物化执行核心？

明确回答：

- 能否直接复用？
- 需要什么适配层？
- 哪些路径必须绕开？
- 是否存在难以隔离的策略行为？
- 如果不能复用，替代方案是什么？

### Q6. LLVM 应以什么形式参与？

比较：

- 仅作为参考与 oracle。
- 提取生成的编码知识。
- 复用 MC 层部分组件。
- 建立自有 target definition。

不允许仅以“LLVM 功能完整”作为选择理由。

### Q7. Fixup 是否能够统一表达？

给出跨 ISA 的公共结构，以及必须目标特化的部分。

### Q8. 如何证明“不偷偷规划”？

给出可以自动执行的证据，而不仅是架构图或口头承诺。

### Q9. v0 的最小有效边界是什么？

明确哪些功能必须进入 v0，哪些应延后。

### Q10. 未来扩展如何避免破坏旧计划？

说明版本、目标定义、未知字段、兼容性和重放策略。

---

# 13. 架构路线比较

最终必须评估以下三条路线。

## Route A：XirAsm-lib 中心

```text
FMP
  -> strict adapter
  -> XirAsm-lib low-level encoding
  -> normalized output
```

关注：

- 最小开发成本。
- 对已有库的依赖。
- 策略隔离程度。
- 多 ISA 扩展能力。
- 版本稳定性。

## Route B：LLVM MC / TableGen 中心

```text
FMP
  -> target-definition adapter
  -> LLVM-derived encoding machinery
  -> normalized output
```

关注：

- 编码知识覆盖度。
- LLVM 内部数据结构耦合。
- relaxation / assembler policy 的隔离成本。
- 构建和维护复杂度。
- 跨版本升级成本。

## Route C：自有最小物化核心 + 外部编码知识

```text
FMP
  -> strict validator
  -> minimal deterministic encoding kernel
  -> versioned target definitions
  -> normalized output
```

其中 XirAsm-lib 和 LLVM 可作为知识、工具或局部模块来源。

关注：

- 决策边界是否最清晰。
- 实现成本是否可控。
- 是否需要重复实现大量 ISA 编码知识。
- 长期可维护性。
- 正确性验证成本。

每条路线必须给出证据支持的优缺点和实际风险。

**不得因为既有技术偏好而预先宣布胜者。**

---

# 14. 验收标准

本任务只有在以下条件同时满足时，才视为完成。

## AC-01：契约完整

存在一份可以指导实现的 FMP v0 契约文档。

不是只有架构愿景或概念图。

## AC-02：字段有依据

关键字段能够对应实际编码需求、源码证据或失败测试。

## AC-03：三架构均有实证

x86-64、AArch64、RV64 都至少完成一个包含真实机器编码的纵向闭环。

## AC-04：编码歧义得到验证

至少在 x86-64 与 RV64 上证明不同合法编码形式不会由物化器隐式选择。

## AC-05：Fixup 得到验证

至少覆盖：

- 一个 x86-64 相对引用。
- 一个 AArch64 PC-relative 或关联引用。
- 一个 RV64 分散位或关联引用。

如果某案例被明确排除在 v0 范围外，必须记录原因，并提供不会被误接受的拒绝测试。

## AC-06：非法计划严格拒绝

至少完成 N01–N12 中所有适用的负向测试，并记录未适用项目的理由。

## AC-07：确定性可重放

至少完成重复执行、跨进程、序列化重放和定义版本不匹配测试。

## AC-08：复用边界有源码证据

XirAsm-lib 和 LLVM 的技术判断必须对应具体版本、文件、函数或测试。

## AC-09：明确未解决问题

不得用“后续完善”掩盖影响 v0 正确性的核心问题。

## AC-10：给出可执行下一步

最终应明确推荐路线、首批模块、实现顺序和关键阻塞项。

---

# 15. 输出目录约定

建议采用：

```text
research/fmp-v0/
  00_environment_and_evidence.md
  01_encoder_boundary_audit.md
  01_reuse_matrix.md
  02_fmp_v0_contract.md
  02_fmp_v0_schema.*
  02_open_decisions.md
  03_cross_isa_test_matrix.md
  04_invariant_results.md
  04_replay_results.md
  05_final_recommendation.md

  evidence/
    source_index.md
    xirasm/
    llvm/
    experiments/

  fixtures/
    x86_64/
    aarch64/
    rv64/

  prototype/
    README.md
    src/
    tests/
    tools/
```

Agent 可按实际仓库结构调整路径，但必须保持研究证据、契约、测试样本和实现代码可追踪。

---

# 16. Agent 执行约束

1. **先研究，后实现。** 不得在尚未识别底层编码路径前直接设计大规模框架。
2. **先契约，后扩展。** 不得用增加 ISA 覆盖率代替契约验证。
3. **先反例，后抽象。** 任何跨 ISA 通用字段都应通过至少两个架构的实际案例检验。
4. **优先最小闭环。** 不建设宏语言、优化器、ABI lowering、通用汇编前端。
5. **不隐藏失败。** 无法支持的编码形式应显式拒绝。
6. **不捏造证据。** 不存在的 API、源码位置和实验结果必须标记为未知。
7. **记录技术决定。** 重大设计取舍应形成简短 ADR（Architecture Decision Record）。
8. **允许推翻草案。** 本文的数据模型是研究假设，不是不可修改的规范。
9. **不得推翻核心边界。** 如果某方案要求物化器重新承担指令选择、松弛或布局规划，应视为与目标冲突。
10. **避免无关比较。** 除非发现直接阻塞问题，不再扩大汇编器横向调研范围。

---

# 17. 最终报告格式

最终报告必须按以下结构提交：

**A. Executive Decision**

- 推荐的 FMP v0 边界。
- 推荐技术路线。
- 主要证据。
- 尚未解决的阻塞项。

**B. Source Audit**

- XirAsm-lib 编码路径。
- LLVM 编码与 fixup 路径。
- 策略隔离判断。

**C. Frozen Contract**

- 数据模型。
- 形式标识。
- 操作数。
- 编码选择。
- 布局。
- 符号与 fixup。
- 版本和错误模型。

**D. Cross-ISA Validation**

- x86-64。
- AArch64。
- RV64。
- 关键反例与差异。

**E. Determinism Proof Obligations**

- 每项不变量的验证方法。
- 实际测试结果。
- 未验证部分。

**F. Route Evaluation**

- Route A / B / C。
- 复用成本。
- 风险。
- 推荐理由。

**G. FMP v0 Final Scope**

- v0 必须支持。
- v0 明确不支持。
- 后续扩展点。

**H. Implementation Roadmap**

- 第一阶段最小模块。
- 具体实现顺序。
- 测试门槛。
- 主要风险与应对。

---

# 18. 最终判定原则

研究完成后，应当能够用一句严格的话定义 FMP v0：

> Frozen Machine Plan 是一份绑定版本化目标编码定义的、已完成所有可观测编码与布局选择的机器计划；确定性物化器只负责验证并执行该计划，生成规范化字节和修补记录，不再拥有改变机器事实的规划权。

如果某项设计导致这句话不再成立，必须明确指出冲突，并重新划定职责边界。

**最终成功标准不是物化器支持多少指令，而是能够证明：所有会改变输出的选择，要么已冻结，要么由版本化规则唯一决定；除此之外，物化器没有自由裁量权。**

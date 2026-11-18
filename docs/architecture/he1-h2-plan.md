# H2 实施计划：目标包作者层与确定性定义构建

- 状态：**待审提案**（2026-11-16；同日按八轮审计 P1/P2 修订，2026-11-17 至
  2026-11-18 按第九轮至第二十轮审计修订）。规范决策见
  `docs/adr/0128-package-and-bundle-contract.md`，该 ADR 仍为 `proposed`；
  评审合并前本文和 ADR 都不是冻结依据。本文保留为实施计划与验收映射。
  **H2 尚未实现，本文不把任何 H2/H3/H4/H5 项目算作已完成。**
  第二十轮固定：H3 的子集目标必须逐指令证明 `E_owner(form(i)) ⊆ E_plan`，
  证据来自版本化的 bundle 归属/覆盖映射或另一个冻结来源；`monasm-bundle/0.1`
  没有该映射，只加 `fmp/0.2` 不放宽；无归属证明的 legacy form 默认拒绝，不按
  空集推定。发布门禁的键改为 `(B_checked, C_checked, mode)`：基线提交 SHA、
  被测候选**树** SHA 与合并模式；普通 up-to-date 检查不等于落地树相等，403 或
  空 ruleset 是未取到证据而不是没有保护。HE-1 总体设计 §6/§7/§10 的示例同步到
  本 ADR 的包与 bundle 结构。
  第十九轮固定：发布门禁只对它读到的提交对生效，禁止复用旧绿色结果；
  `monasm-package/0.1` 永久拒绝非空 `exports.types`/`exports.profiles`，语义留给
  显式的新包格式版本；输入顺序固定为词法校验→no-follow 打开→句柄类型检查→
  同句柄大小提示→有界读取→解析；canonical 定义超过 16 MiB 时构建省略 legacy
  快照，而不是写出自己无法通过 `--check` 的产物。
  第十八轮固定：打开的叶子只接受普通文件，类型取自已打开句柄，FIFO/socket/
  设备节点是 `not-a-regular-file`（退出 1），POSIX 输入打开带非阻塞语义；
  退役最后一个 spec 时同一 PR 删除 lock/sealed/legacy 派生产物，
  `--all --check` 拒绝孤儿产物。
  第十七轮固定：包目录段是**完整** `package_id`，路径映射是单射，
  `monasm.x86.crypto` 与 `vendor.x86.crypto` 可同版本共存；已发布集合的权威是
  **目标分支尖端 `B`**（不是 merge-base），要求
  `Published(B) ⊆ Published(H)` 且每个已发布路径的字节相等；依赖项是封闭对象
  并有一个非空依赖的固定摘要向量；`verify --package` 执行
  `fmp_model::definition::read`，但不执行用例的 `plan::read`/`bind`/`materialize`。
  第十六轮固定：`legacy_source` 的迁移目标等价是 `TargetEq`——`definition_format`
  相等，`target_identity` 除 `enabled_extensions` 外逐字段 canonical 相等、该字段
  按集合相等，因此规范升序的新包可以迁移扩展数组顺序不同的冻结 legacy 文档；
  边界正例取最终合法域 `D_form`（应用 `L`/`U`、`align_bits` 和 `excluded`）的
  端点与内部值，原始端点被排除或不对齐时不得作正例。
  第十五轮固定：`verify --package` 只验证用例的静态阶段契约，
  `package_conformance` 才执行并证明第一个真实拒绝阶段与完整诊断集，报告分别
  记录两种状态；寄存器边界按编码宽度 `w` 区分，`D_reg = ([0, 2^w−1] ∩
  [0, 2^64−1]) \ E`，`w ≥ 64` 时用 `0`/`u64::MAX` 加排除值或非法操作数类型，
  不要求不可表示的 `2^w`，并保留 127/192 位槽位的包级边界测试。
  第十四轮固定：已提交的 legacy 快照必须与 sealed 内 `definition` 的 canonical
  字节相等（`legacy-snapshot-mismatch`），但仍不进入任何摘要、缺失合法；定义
  身份错配不是 `monasm-cases/0.1` 的用例种类，由独立绑定测试承担；H3 解除
  `h2-exact-target` 需要版本化构建规则加新计划协议，`monasm-bundle-spec/0.1`
  的拒绝结论永久不变；变更路径先按 base registry 判定包含，嵌套
  `package.json` 不能遮蔽已发布祖先。
  第十三轮固定：`scope:"plan"` 负例可用 `stage:"read"` 记录 `plan::read` 自身
  的拒绝（`scope:"form"` 仍只能 `bind`），声明的阶段必须恰是第一个拒绝的
  阶段；中断写入只保证可检测、不是成功发布，不主张跨文件原子性；输出父目录
  受信任但 `--root` 下每段都走 §3 的不跟随规则，已提交 lock/sealed 用有界流式
  比较；`profile_id` 是包内名义标签，身份是完整 `target.identity`。
  第十二轮固定：首次发布只有一种顺序（build 成功 → 追加登记项 → 两项
  `--check` → 提交），发布是合并提交；legacy 快照是派生开发缓存，缺失合法，
  提交副本受等价门禁，写阶段先删除旧文件；扩展/能力数组只有一种严格排序、
  无重复的写法；
  64 MiB 闭包预算按实际读取的包根字节计费并在越界读取处拒绝；`fmp-def/0.1`
  的 `E_form = ∅` 限制写进验收报告。
- 基线：`fefb463`（H1 合并提交；工作树干净）。
- 上游：`ADR-0125` 决策 1–6；`docs/architecture/he1-horizontal-extension.md`
  §4–§8、§11–§13、§14、§15.1；`ADR-0127`；`research/he1/H1-report.md` §11。
- 完成定义：设计 §13 的 H2 退出门槛，加上 `HE-AC-03`、`HE-AC-04`、`HE-AC-05`、
  `HE-AC-08`、`HE-AC-09`、`HE-AC-11` 在 H2 可证明的部分，以及 `HE-T05`、
  `HE-T07`、`HE-T08`、`HE-T14`、`HE-T16`、`HE-T18`、`HE-T19` 在 H2 可证明的
  部分。其余验收项由 H3/H4/H5 承担，本文逐项标出边界。
- 硬约束：不改 `definitions/`、`fixtures/`、`schema/`、`docs/fmp-v0/`；不改
  H1 的 `bind`/`ValidatedPlan`/`Definition` 身份边界；不新增 `fmp/0.1` 错误码。

---

## 0. 一句话

把「新增一个指令族要手工改一份全量定义 JSON」变成「在自己的目标包里声明
指令族，用显式 spec 构建一个可重放、可对照的 bundle」，同时让执行仍然经过
H1 的 `Definition` → `bind` → `ValidatedPlan` → `materialize` 生命周期。

## 1. 基线事实（`fefb463`）

### 1.1 现在没有的东西

| 缺口 | 现状 | 由谁关闭 |
|---|---|---|
| 目标包目录 | 仓库没有 `packages/` | H2 |
| 显式 bundle/lock | 仓库没有 `bundles/`；`Registry::load_dir` 递归读取整个目录 | H2 定义格式与构建；运行期闭包加载是 H3 |
| `fmp-definition` crate | workspace 只有 `fmp-model`、`fmp-validate`、`fmp-materialize`、`fmp-plan`、`fmp-cli` | H2 |
| 包清单与归属表 | 没有 `monasm-package/0.1`；form 归属只存在于定义文件本身 | H2 |
| 目标配置 | `fmp-model/src/definition.rs` 的 `check_form_id` 仍白名单 `x86`/`aarch64`/`riscv`；`Registry::load_dir` 仍扫描整棵树 | H2 不修；H3 |
| 新 ISA 命名空间 | `fmp/0.1` 仍拒绝合成族名 | H2 不修；H3 |
| fixup profile | 现有 fixup 仍由 plan 的 `field_descriptor/transform` 表达 | H2 不修；H4 |

### 1.2 可以直接复用的边界

- `Definition` 已封闭：私有字段、无公开构造、无 `Clone`；唯一构造是
  `definition::read`/`Registry::load_dir`，只读访问器是 `namespace()`、
  `version()`、`target()`、`forms()`、`digest()`（`ADR-0127` §1）。
- `fmp_model::canonical::canonical_digest` 是既有 canonical JSON 摘要实现，
  与 `tools/check_definition.py` 的 `json.dumps(..., sort_keys=True,
  separators=(",", ":"), ensure_ascii=False)` 对齐；H2 的包摘要必须复用它，
  不能另写一套规范化。
- `fmp_model::definition::read` 已经是定义结构和语义的权威检查。H2 的构建器
  把包合并成一份 `fmp-def/0.1` 或 `fmp-def/0.2` 文档，再交给 `read`，不复制
  这套检查。
- `fmp_validate::bind(plan, Arc<Definition>)` 是唯一正式准入入口；H2 不改它。
- `fmp-plan` 的 `PlanBuilder` 可以在包级测试里构造计划事实，不需要手写
  `fmp/0.1` 文档。
- `fmp` CLI 用 `--definitions <dir>` 显式选择定义目录。H2 的 legacy 兼容快照
  只要落成目录，就能被现有 CLI 读取；H2 不新增 CLI 子命令。

### 1.3 语料测量

这些数字是 H0/H1 的证据，不是 H2 要改的手写计数：

| 项 | 值 |
|---|---|
| 定义文档 | 104 个（`definitions/**/*.json`） |
| 正例计划 | 128 个（x86_64 85、aarch64 26、rv64 17） |
| 负例 | 619 个（611 `materialize` 阶段 + 8 `read` 阶段） |
| oracle | `122/128` 重算，6 个 `manual-derivation` 跳过，0 失败 |
| 最新 x86_64 定义 | `0.78.0.json`，`fmp-def/0.2`，632 forms |
| 最新 aarch64 定义 | `0.20.0.json`，`fmp-def/0.1`，185 forms |
| 最新 rv64 定义 | `0.6.0.json`，`fmp-def/0.1`，24 forms |

H2 不新增正例/负例计数，也不把包的数量写进 `STATUS.md` 的手写覆盖表。
包级计数由工具生成。

## 2. 目标结构

### 2.1 开发期与执行期分开

```text
packages/<target>/<package_id>/<version>/
  package.json
  forms/*.json
  tests/cases.json
  evidence/manifest.json
  NOTICE
  README.md
          |
          |  fmp-definition build --spec <spec> --root <repo-root>
          v
bundles/specs/<bundle_id>.json         # 显式选择，不是扫描结果
bundles/locks/<bundle_id>.lock.json    # 精确闭包 + 摘要
bundles/sealed/<bundle_id>.bundle.json # 扁平化定义快照

执行期（H2 不改）
  plan + Arc<Definition> -> bind -> ValidatedPlan -> materialize
```

派生产物（lock、sealed、legacy 快照）与 spec 一一对应：最后一个 spec 退役的
同一 PR 删除它们，`verify --all --check` 拒绝孤儿产物（`ADR-0128` §8.4）。

H2 的 `VerifiedBundle` 只是在 `Arc<Definition>` 外面加包/闭包/归属元数据；
`bind` 仍接收 `Arc<Definition>`。H3 再把 `bind` 的输入收紧为 bundle，避免
在 H2 重写身份机制。

### 2.2 三个新类型（都在 `fmp-definition`）

| 类型 | 构造 | 作用 | 不是 |
|---|---|---|---|
| `PackageSpec` | `fmp-definition` 内部解析 `package.json` | 一个包的显式清单、导出、依赖 | 运行期可变的注册表 |
| `BundleSpec` | 解析 `bundles/specs/*.json` | 发布者显式选择目标、包、版本 | 目录扫描的“最新版本” |
| `VerifiedBundle` | `build`/`verify` 成功后产生，字段私有 | 已检查闭包、归属、规范和定义文档的不可变产物 | 完整的运行期能力验证（H3） |

`VerifiedBundle` 提供：

```rust
pub fn definition(&self) -> Arc<Definition>;
pub fn definition_digest(&self) -> &str;
pub fn bundle_digest(&self) -> &str;
pub fn lock_json(&self) -> Json;
pub fn bundle_json(&self) -> Json;
```

`definition()` 是 H2 到 H1 的桥：测试和 H2 的 legacy 兼容路径需要把
`Arc<Definition>` 交给 `bind`。H3 用 bundle-bound `bind` 替代它，H2 不把
这个桥描述成长期 API。

### 2.3 依赖方向

```text
fmp-definition --> fmp-model
fmp-validate ----> fmp-model
fmp-materialize -> fmp-validate + fmp-model
fmp-cli ---------> 上述运行组件
```

- `fmp-definition` 的**产品依赖**是 `fmp-model` 加上至多一个固定的路径安全层
  （只负责 H2-D3 的 no-follow 打开，不解析清单/定义/摘要）；它不依赖
  `fmp-validate` 或 `fmp-materialize`。
- 包级一致性测试放在 `fmp-definition/tests/`，用 dev-dependencies 引入
  `fmp-validate`、`fmp-materialize`、`fmp-plan`；这不改变产品依赖图。
- 不新增第六个产品 crate；测试 harness 先用 `fmp-definition` 的 test target，
  只有它长到需要独立发布时才拆 crate。

### 2.4 独立身份与包级用例（第一轮 P1-1；第二轮 P1-1/P1-2；第三轮 P1-3）

`verify --package` 不读 spec，因此不能借用 bundle 的 `namespace`/`version`。
实现必须调用同一个固定函数 `monasm-standalone/0.1`：

```text
namespace = "monasm.standalone." ++ package_id
version   = "standalone+" ++ lowercase_hex(source_package_digest 去掉 "sha256:")
domain    = "monasm-standalone/0.1"
```

输入只有包本身（清单 + 声明资产，即产生 `source_package_digest` 的那些字节）；
绝对路径、目录名、当前工作目录、时钟、spec 和枚举顺序都不参与。把包复制到
另一个目录、换一个工作目录运行，独立身份和独立 `definition_digest` 必须不变。

spec 的 `namespace` 不得以 `monasm.standalone.` 开头，`version` 不得以
`standalone+` 开头；否则 `reserved-identity`（退出码 1）。因此临时身份永远
不会写进 lock 或 sealed bundle。包级 conformance、`verify --package` 和未来的
作者工具都调用这个函数，不各自发明规则。

包级机器码测试是门禁的一部分，不是可选 harness：

- 含 forms 的包必须有 `tests/cases.json`（`monasm-cases/0.1`），位置固定为包根；
  没有中央用例清单、没有按 ISA 的注册表。
- 每个 case 带 `form_id`、`instruction_id`、`kind` 和**完整 `fmp/0.1` 计划文档**
  （不是抽象的 plan facts，也不是另一套 DTO）。计划里 `definition_identity`
  必须恰好是 `$standalone` 哨兵三字段，harness 在执行前替换成 §2.4 的独立
  身份，再调用 `fmp_model::plan::read`。
- 计划只能有一条 instruction；其 `instruction_id`/`form_id` 必须分别等于 case
  的 `instruction_id`/`form_id`，且 `form_id` 必须由包导出。否则
  `case-form-mismatch`。这阻止「case 声明 B，计划却执行 A」。
- 每个导出 form 至少一个 `positive` 和一个 `scope: "form"` 的 `negative`。
  普通拒绝用 `scope: "plan"`；它可以针对错误的 `expected_digest`、布局或目标，
  但不计入 form 覆盖。
- form 负例必须写 `baseline_case_id`（同文件中、同 form/instruction 的正例）
  和单个 `mutates` 指针，指针只能落在
  `/instructions/0/operands/<n>/(payload...|kind|target_type|modifiers...)`。
  harness 对基线和用例计划做 canonical JSON 差分，差异指针集合必须恰好等于
  `{mutates}`；多改、无改动或改 `form_id` 都是 `case-mutation-mismatch`。
- `expect_error` 是封闭对象：`stage`（`read`/`bind`/`materialize`）和非空的
  `diagnostics` 数组；每项恰好 `code`/`path`，按 `(path, code)` 排序且唯一。
  观察到的全部 `(code, path)` 对排序后必须与声明数组**完全相等**；多一条、
  少一条或只匹配其中一条都失败（`case-diagnostics-mismatch`）。`stage:"read"`
  的观察集是 `plan::read` 返回的单个 `Diagnostic`，且只允许 `scope:"plan"`；
  声明的阶段必须恰是第一个拒绝阶段，否则 `case-error-scope`；这一条由
  `package_conformance` 执行判定，静态文档检查只能看声明形状。`materialize`
  阶段只接受 `PostEncodeAssertion`，`Internal`/`HostFailure` 是
  `case-materialize-fault`，绝不算通过。
- form 负例声明的和观察到的 `path` 都必须是 `/instructions/0` 或以
  `/instructions/0/` 开头，否则 `case-error-scope`；plan 负例不限制路径。
  因此错误的 `expected_digest`、根级 `format_version` 或通配错误不能给 form
  充数。覆盖只由 `scope: "form"` 的负例计算；缺失是 `uncovered-form`。
- 每个用例带 `evidence`（`oracle` 或 `manual-derivation`）；有证据清单时其
  `path`/`sha256` 必须与清单一致，开发模式没有清单时直接核对 case 自带
  `sha256` 与原始文件字节。可发布包的证据清单还必须列出 `tests/cases.json`
  本身，因此改用例会改变 `evidence_digest` 和 `release_digest`，但不改
  `source_package_digest`/`definition_digest`。
- `verify --package` 校验用例 schema、覆盖、排序、单指令绑定、`scope`/基线/
  `mutates` 指针语法与计划差分、证据引用和哈希；阶段相关检查**只是静态契约**：
  `stage` 取值、form 只 `bind`、诊断数组形状和静态 scope 规则。它对包合成的
  `Definition` 执行 `fmp_model::definition::read`，但**不**执行用例的
  `fmp_model::plan::read`、`bind` 或 `materialize`（产品依赖仍只有 `fmp-model`），
  因此不证明第一个真实拒绝阶段。
- `package_conformance` 测试执行所有用例：替换独立身份 → `plan::read` →
  `bind` → `materialize`，比较 §4.2.1 的精确机器输出投影；负例断言完整的
  `(code, path)` 诊断集合，并证明声明的 stage 恰是第一个拒绝阶段，而不是只找
  一条符合预期的错误。报告的“静态用例有效”和“执行阶段与诊断集已验证”是两行
  独立状态，前者不能推出后者。
- harness 在测试期枚举 `packages/*/*/*/package.json`。这是测试发现，不是构建器
  选择；它不能改变任何 bundle 摘要，因此不重新打开 `HE-AC-05`。

一个结构合法但 opcode 被改错的 form 会被 `package_conformance` 的正例字节比较
拒绝；若作者连期望字节一起改，则必须提供独立证据，`--release` 检查证据存在、
被清单列出且哈希匹配。构建器不声称自己重跑了 oracle；`tools/oracle/rerun.py`
仍只覆盖冻结的 legacy fixtures。这一点必须写进 H2 报告，不能把「证据记录在案」
夸大成「本机重算」。

## 3. 契约决定（待 `ADR-0128` 固化）

以下决定编号 `H2-D1`–`H2-D12` 只在本计划内引用；规范文本已写进
`docs/adr/0128-package-and-bundle-contract.md`，本节保留实施细节。

### H2-D1 目录与显式输入

- 叶包路径：`packages/<target>/<package_id>/<version>/`，`target` 是目录名
  （`x86_64`、`aarch64`、`rv64`），不是 form ID 前缀；`<package_id>` 必须等于
  清单的**完整** `package_id`（`monasm.x86.mov-register` →
  `monasm.x86.mov-register`，不是 `mov-register`），
  `<version>` 必须等于清单 `version` 和 spec 的 `packages[].version`；不一致
  分别是 `path-lexical` 和 `path-version-mismatch`。映射
  `Path(target, package_id, version) = (target, package_id, version)` 是单射：
  `monasm.x86.crypto` 与 `vendor.x86.crypto` 落在
  `packages/x86_64/monasm.x86.crypto/0.1.0/` 与
  `packages/x86_64/vendor.x86.crypto/0.1.0/`，可独立存在；若只取最后一个点分段，
  两者会争用 `packages/x86_64/crypto/0.1.0/`，独立作者的命名空间隔离无法保留。
  `pseg` 已允许点号，不需要新增转义。`target` 只是目录标签：只
  校验词法，不与 `isa_family`、`target_profile` 或中心表比较，因为目标事实由
  包自述（H2-D2），H3 的第四种家族不能被迫增加目录映射。
- **身份、路径段和产物文件名是 ASCII 且跨平台可移植（第九轮 P2-1，
  `ADR-0128` §1.3）。** 以下规则在打开任何文件之前校验：
  - `package_id`、`bundle_id`、`namespace`、`target_profile`、`profile_id`
    匹配 `^[a-z][a-z0-9]*(\.[a-z][a-z0-9_-]*)+$`；非法是
    `identifier-lexical`（退出码 1）。`monasm.x86.`、`Monasm.X86.Mov`、
    `monasm..x86` 都拒绝。
  - 作者写的 `version` 匹配
    `^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){2,}(-[a-z0-9]+([.-][a-z0-9]+)*)?$`：
    至少三段数字、无前导零；`0.1.0`、`0.2.0`、`0.1.0-h2` 合法，`0.1`、`01.0`、
    `0.1.0-H2` 不是。派生的
    `standalone+<hex>` 只用于独立身份，不写进 manifest/spec/lock/路径；写进
    spec 时已由保留前缀判为 `reserved-identity`。
  - 声明路径（`exports.forms/types/profiles[].path`、spec 的
    `packages[].path`、证据清单中的路径、`legacy_source` 组件）的每一段匹配
    `^[a-z0-9_][a-z0-9_.-]*$`，整体产生式是 `pseg ("/" pseg)*`，因此**允许单段
    路径**：顶层的 `add.json` 是一个 `pseg`，包根文件 `NOTICE`/`README.md` 也是
    单段（它们是仅有的两个固定大写例外），不是至少两段（第十一轮 P2-2）。形状
    固定的字段另有规则：`packages[].path` 仍是
    `packages/<target>/<package_id>/<version>`，form/type/profile 路径相对包根，证据
    路径相对包根。每段不得是 `.`/`..`、不得含 `..`、不得以 `.`
    或空格结尾、不得是 Windows 设备名（`CON`、`NUL`、`PRN`、`AUX`、
    `COM1`–`COM9`、`LPT1`–`LPT9`，大小写不敏感，带扩展名也算）；非法是
    `path-lexical`（退出码 1），不是「某个平台打开失败」（退出码 2）。
  - 声明路径的冲突比较有**两个命名空间**（第十轮 P1-1）。包内资产与证据路径
    相对于各自的 `packages/<target>/<package_id>/<version>/`：同包内按**相对字符串**
    ASCII 大小写折叠比较；跨闭包只按 `packages[].path` 与该相对路径拼接后的
    **仓库根相对路径**比较。不同包根下的同名相对路径不冲突，是合法组合：
    `packages/x86_64/monasm.x86.alu/0.1.0/forms/add.json` 与
    `packages/x86_64/monasm.x86.vector/0.1.0/forms/add.json` 是两个文件，规范
    固定位置的 `tests/cases.json` 同理。只有两个被选中的包根折叠成同一仓库路径
    （如 `packages/x86_64/monasm.x86.alu/0.1.0` 与
    `packages/x86_64/MONASM.X86.ALU/0.1.0`）或同一 `path`
    被列两次才是 `path-lexical`。语法本身只允许小写，因此合法文档不会触发折叠；
    这条规则把拒绝理由固定为折叠，而不是「文件刚好能打开」。`README.md`/`NOTICE`
    作为证据路径出现时按固定大写拼写精确匹配，是唯一例外；它们不是资产路径。
  - 路径按字面匹配，不小写化、不去尾点/空格、不解析 8.3 别名；只有修补后才
    匹配的路径是 `path-lexical`。
  - **磁盘目录项必须与声明逐字节同名（第十轮 P1-2）。** 声明 `forms/add.json`
    只有在已打开的 `forms` 句柄中确实存在名为 `add.json` 的目录项时才成立。大小写
    不敏感的 APFS/NTFS 会用它打开 `Add.json`；那不是成功，而是 `path-lexical`
    （退出码 1），ext4 上结论相同。检查在**已打开的父句柄**上完成：枚举该句柄，
    找逐字节相等的名字，再相对同一句柄按 no-follow 规则打开该目录项；不得比较
    绝对路径字符串，也不得在打开前另做一次探测。中间目录与最终文件都适用。
  - **打开必须绑定到被核对的那个目录项（第十一轮 P2-3）。** 名字核对与实际打开
    之间，目录项可能被替换；「再按同名打开一次」不自动保证读到同一对象。实现必须
    打开刚匹配到的项（目录项句柄或打开后的对象身份核对），或在发现替换时以
    `path-escape`（退出码 1）拒绝。只证明拒绝符号链接不算证明这一点；N1 门禁在
    三平台都要包含该替换场景。平台无法对已打开句柄做精确名字查找，或无法把打开
    绑定到匹配项时，N1 失败；不得接受别名名字，也不得退回跟随打开。这与「声明
    `forms/Add.json`」的非法词法测试是两回事，不能互相替代。
  - `bundles/specs/<file>.json`、`bundles/locks/<file>.lock.json`、
    `bundles/sealed/<file>.bundle.json` 的 `<file>` 必须等于文档里的
    `bundle_id`，否则 `bundle-file-mismatch`（退出码 1）；legacy 快照固定为
    `bundles/legacy/<bundle_id>/definition.json`。`--all` 因此每个身份只有
    一个文件名，重命名 spec 不能把它挂到另一个发布上。
- 版本目录是**已发布快照的不可变边界**。发布事实记录在
  `bundles/published.json`（`monasm-published/0.1`，§8.3）：发布者在第一次把
  版本写进 spec 的同一 PR 里追加登记项；之后即使删除 spec，登记项也永久保留。
  只有 **目标分支尖端 `B`** 已登记的版本目录才在本 PR 内不可变（merge-base 不是
  权威：`Published(B) ⊆ Published(H)`，且每个已发布路径的字节在 `B` 与 `H` 中
  相等）；同一 PR 首次
  创建并登记是**首次发布**，允许创建和调整，合并前必须按 head spec、最终
  `path`、`version` 和重算的 `source_package_digest` 校验；合并后登记项进入
  base，快照才冻结。删除 base 登记项本身是 `published-registry-modified`，
  所以不能借同一 PR 取消发布。base 已登记目录内任何文件（含 `package.json`、
  `NOTICE`、`README`、`evidence/`、`tests/cases.json`）都不得新增、修改、
  重命名或删除；违反是 `published-package-modified`（退出码 1）。登记项只能
  追加；`path` 与 `(package_id, version)` 都全局唯一，同一逻辑版本永久绑定
  首次合并登记的 `path` 和摘要，多个 bundle 只能引用同一项，不能各自创造内容
  不同的同名版本。删除/改写/重排 base 条目是 `published-registry-modified`，spec
  选中但未登记是 `published-registry-incomplete`，登记与包摘要不符或重名版本
  换路径/摘要登记是 `published-registry-invalid`。新 form、修正或发布后证据
  变更必须创建同级新版本目录，旧目录原样保留；只要旧 spec 仍在 head，旧 lock
  仍能 `verify --all --check` 重建。发布者另行决定何时把 spec 指向新版本。
  删除最后一个 spec 只退役发布：同一 PR 删除该 bundle 的 lock、sealed 和 legacy
  快照，包快照与登记项保留，退役字节在发布它的提交上仍可重放；H2 不定义归档
  格式，也不留下没有 spec 的 sealed 文件。
- **门禁结论必须对应实际落地的基线与候选树（第十九、二十轮 P1-1）。** 变更路径
  门禁读取并记录一个三元组 `(B_checked, C_checked, mode)`：`B_checked` 是它读的
  目标分支提交 SHA，`C_checked` 是它在声明的合并模式下评估出的候选**树** SHA，
  `mode` 是 `merge`/`squash`/`rebase`/`fast-forward`。合并落在提交 `M` 上，令
  `B_landed` 为 `M` 所应用的提交（合并提交的第一父提交，其余模式为原目标尖端）、
  `C_landed = Tree(M)`；只有 `B_landed = B_checked`、`C_landed = C_checked` 且
  `mode(M) = mode`，绿色结果才授权合并。否则「A 改未发布包的 `README.md`、B 先
  发布该版本并合入、A 用旧结果合并」会改动刚发布的目录，而 A 跑过的每个检查都
  曾是对的（差异字节没变，只有基线移动了）。**不能用提交 SHA 对代替树**：每种
  合并模式都产生新提交，`refs/pull/N/merge` 的临时提交不是最终写入目标分支的
  提交，树才是可跨模式比较的单位。
  可建立等式的机制有两种：merge queue 在当前目标尖端上构建 merge-group 候选、
  在该候选上跑门禁并只合并该候选（目标前进时组重建）；或把记录的候选提交以
  目标移动即被 git 拒绝的操作落到记录的基线上（候选提交的 fast-forward，或
  写入该确切提交的受保护分支合并）。**普通 up-to-date required checks 不等价**：
  它只在基线前进时重跑检查，不承诺最终写入的提交带被测树，且合并提交 SHA 必然
  不同于临时测试合并 ref；因此「要求分支为最新」的设置不能证明
  `C_landed = C_checked`，若仓库走这条路，还必须额外合并记录的候选（或在最终
  候选上重跑并合并该确切候选），否则只有检测、不构成授权。门禁输出三元组，
  自动化检查在落地提交上重算并比较，不一致即失败（非零退出）；不得复用旧结果，
  手工绕过保护路径的合并不是合法发布。合并后审计只提供可检测性，不能替代等式。
  平台设置无法从树内读出：H2a 必须通过 API 读取生效的 branch protection/merge
  queue 并把证据（查询的端点、生效配置、仓库实际允许的合并操作）写进报告；
  **403、空 ruleset 列表或 API 不返回设置都不是「没有保护」的证据**，而是尚未
  取到证据，本轮仍失败（`ADR-0128` §8.1）。
- 登记还包括 `identities` 数组：每项恰好 `definition_digest`/`namespace`/
  `version`，按 `(namespace, version)` 严格排序。定义名是永久的，bundle ID
  是可移动的发布线：
  - `(namespace, version)` 首次合并发布后永久绑定该 `definition_digest`；之后
    任何 spec 复用同一名字但生成不同摘要（即使旧 spec 已全部退役）是
    `definition-identity-conflict`（退出码 1）。用相同摘要重新发布是合法的，
    不新增第二项。
  - `bundle_id` 不入登记。发布者把同一 `bundle_id` 推进到新包版本是正常流程；
    不可变的**bundle 内容标签**是 `(bundle_id, bundle_digest)`，由提交的
    lock/sealed 和 git 历史记录，`verify --all --check` 在写出它们的提交处重建。
    `release_digest` 是**证据完备的发布身份**：它把完整证据清单也纳入，bundle
    摘要不含证据。H3 客户端必须明确固定的是哪一个，不能混用。
  - 两个数组都只追加：base 行只能按排序插入新行，删除/改写/重排/替换是
    `published-registry-modified`；head-only 行在无 head spec 发布该身份时可撤销。
  - spec 发布 bundle 时其定义身份必须已按实际摘要登记：缺失是
    `published-registry-incomplete`，摘要不符是 `definition-identity-conflict`。
  - 登记不进入 `source_package_digest`/`definition_digest`/`bundle_digest`/
    `release_digest`；`identities` 的摘要只与构建结果比较，绝不作为它的输入。
- **冻结的 legacy 定义名是保留身份。** `definitions/` 早于 H2，不在 spec 集合或
  登记表里。构建器按路径排序读取 `<root>/definitions/*/*.json` 的
  `namespace`/`version`，得到只读的保留集合；它不进入任何摘要，也不用于选择。
  文件按路径排序读取；同一对出现在两个冻结文件里仍只贡献一个成员，成员资格不
  依赖迭代顺序。
  spec 的 `(namespace, version)` 若落在该集合里是 `reserved-identity`（退出码 1）；
  `identities` 也不得登记这样的名字。反例：spec 只导出两条 mov 行、却复用
  `monasm.isa.x86`/`0.1.0`，当前 spec 集合无冲突、登记表也无行，但生成的摘要与
  冻结的 `definitions/x86_64/0.1.0.json` 不同，同名定义出现两份执行快照。
  H2 自己的 bundle 用新版本（`0.1.0-h2`），因此这条规则不占用任何包的名字。
- `package.json` 是唯一入口；`exports.forms` 显式列出每个可执行输入文件。
- 包内可以有不进入执行摘要的 `README.md`、`NOTICE`、`evidence/`、`tests/`。
- 构建器只读取 spec 和闭包里显式声明的文件；不读取作者主目录，不联网，不
  执行包内脚本。

### H2-D2 包清单

`monasm-package/0.1` 的封闭键：

```json
{
  "package_format": "monasm-package/0.1",
  "package_id": "monasm.x86.mov-register",
  "version": "0.1.0",
  "target_profile": "monasm.target.x86_64",
  "definition_format": "fmp-def/0.1",
  "target_identity": {
    "isa_family": "x86",
    "isa_variant": "x86-64",
    "execution_mode": "64",
    "enabled_extensions": [],
    "byte_order": "little",
    "address_width": 64
  },
  "legacy_source": { "isa": "x86_64", "version": "0.1.0" },
  "requires_capabilities": ["field-placement/v1"],
  "dependencies": [],
  "exports": {
    "forms": [
      { "id": "x86:mov/r64-rm/legacy", "path": "forms/mov-r64-rm.json" },
      { "id": "x86:mov/rm-r64/legacy", "path": "forms/mov-rm-r64.json" }
    ],
    "types": [],
    "profiles": []
  }
}
```

- 必需键：`package_format`、`package_id`、`version`、`target_profile`、
  `definition_format`、`target_identity`、`requires_capabilities`、
  `dependencies`、`exports.forms`。可选键只有 `legacy_source`、
  `exports.types`、`exports.profiles`；未知键、重复键、非字符串 ID 仍拒绝
  （`INV-07`），必需键缺失拒绝，可选键缺失合法。
- `exports.forms` **必须非空**（`empty-package`，退出码 1）。`definition::read`
  的 `bind_forms` 拒绝空 `forms` 数组，而 H2 又拒绝非空
  `exports.types`/`exports.profiles`，所以零 form 的包没有任何可构建对象。
  纯类型/profile 包要等新的包格式和 reader，不能靠“空定义也能读”混过去；
  `oracle.status: "not-applicable"` 因此在 H2 可发布包中不合法。
- `definition_format` 与 `target_identity` 是包的**目标自述**：每个包都写，
  进入 `source_package_digest`，不来自中心表、spec 或 legacy 文件。新指令族
  即使 `definitions/` 里没有任何对应文件，也走这条路径。
- `legacy_source` 只表示**迁移来源**：可选；有它才检查钉住版本的行相等，没有
  它就没有 legacy 行可比，构建器不发明一行。它是清单键，存在时进入源摘要。
  把 `0.1.0` 静默改成 `0.78.0` 会改变源摘要；如果行没跟着改，行相等测试必定
  失败。H2 的三个包都是迁移包，必须写。
- `legacy_source` 按固定路径解析为 `<root>/definitions/<isa>/<version>.json`；
  `isa` 是目录名（`x86_64`、`aarch64`、`rv64`），不是 form 家族名。构建器不
  搜索、不取最新、不在多个候选中选择。
- 有 `legacy_source` 时，迁移等价性不止是行相等：包的 `definition_format` 必须
  与钉住文档相等，`target_identity` 必须满足 `TargetEq`——除
  `enabled_extensions` 外每个字段 canonical 相等，`enabled_extensions` 按集合
  相等。这条规则是必需的：§1 要求包内数组用唯一严格升序写法，而冻结的 legacy
  文档保留已发布字节（`definitions/rv64/0.6.0.json` 是
  `["rv64i","rv64c"]`，规范写法是 `["rv64c","rv64i"]`）；若要求原始数组相等，
  两种写法会分别被 `legacy-target-mismatch` 和 `extension-lexical` 拒绝，不存在
  合法清单。包仍自述目标并各自计算摘要，legacy 文件不重拼写。其他字段不一致或
  扩展成员集合不同是 `legacy-target-mismatch`（退出码 1），在合并文档交给
  `read` 之前拒绝。历史文件仍不是目标权威；包自述目标，legacy 只用于证明迁移
  保持语义。把 `execution_mode` 改成 `"32"` 或 `address_width` 改成 32、同时保留
  逐字节相同 form 行的反例，必须被这条检查拒绝。
- `exports.forms` 用 `{id, path}` 而不是裸字符串：文件内容里的 `form_id` 必须
  等于声明的 `id`；交换两个文件不会静默改变归属。
- `exports.forms` 必须按 `id` 严格升序，重复 `id` 拒绝；这样清单只有一种写法，
  重排不是「另一个合法清单」。
- `requires_capabilities` 与 `target_identity.enabled_extensions` 也必须严格
  升序、无重复（第十二轮 P2-2）；逆序是 `extension-lexical`、重复是
  `capability-lexical`（退出码 1）。与 `exports.forms` 同一原则：同一个集合
  只有一种清单写法，构建器不静默重排。
- `dependencies` 的每项是封闭对象 `{package_id, version, source_package_digest}`
  （`ADR-0128` §1）：三个键都必需，未知键/重复键拒绝，`package_id` 用点分标识符、
  `version` 用版本词法、`source_package_digest` 是 `sha256:<64 位小写十六进制>`
  文本；三项都必须精确匹配；数组按 `(package_id, version)` 严格升序。没有
  `latest`、没有 semver 范围、没有隐式升级。§7.0 有一个非空依赖数组的固定摘要
  向量，键名或可选性改变都会改变摘要。
- spec 里的 `source_package_digest` 是作者输入，不是构建器补全。新包先用
  `fmp-definition digest <package-path>` 得到该值，再写进 spec；`build` 发现
  不匹配即拒绝，不自动改写 spec。
- `requires_capabilities`：H2 只承认已经由 `fmp-def/0.1` 和 H1 执行的
  `field-placement/v1`、`integer-domain/v1`；任何其他字符串在 build/verify
  时以 `unsupported-capability` 拒绝（退出码 1）。**声明必须等于从行结构推导出
  的集合**，否则是 `capability-mismatch`（退出码 1）：
  - 任一导出 form 的某个 slot 具有非空 `placements` → `field-placement/v1`；
  - 某个 slot 的 `from` 是 `"operand_value"`（按 `range` 编码整数操作数）→
    `integer-domain/v1`。

  这里有一个必须写明的后果：`definition::read` 要求每个 form 的 `slots` 非空、
  每个 slot 的 `placements` 非空（`bind_forms`/`bind_slot`），所以**每个合法的
  `fmp-def/0.1` form 都推导出 `field-placement/v1`**。因此含 forms 的包声明
  `[]` 是 `capability-mismatch`，不是合法的退化简并；`integer-domain/v1` 才是
  可选的。合法端到端例子是 §1 的两条真实 x86 `0.1.0` mov 行：声明
  `["field-placement/v1"]` 时被合并、`read` 接受且推导集合相等；同一包声明
  `[]` 在 `read` 之前被拒绝。`{"form_id":"x86:example/form","template":"90"}`
  不是合法 Definition（无 slots、ID 缺 `/legacy` 段），只作为 §7.0 的摘要预映像
  fixture，永不进入 `read` 或本推导；不能为了让测试通过而放宽 `read`。

  漏报会让 H3 低估需求，多报会让字段变成愿望清单，所以两个方向都拒绝。推导只
  作用于 H2 已解析的 `fmp-def/0.1` 结构，是读入文档的全函数；H3 可以扩展能力表，
  但不能放宽等式，无法推导的新能力是新的格式版本。H2 不做运行时能力协商；拒绝
  未知声明是为了不让内核不理解的包进入已验证快照。
- `evidence/manifest.json` 对开发中的包可选，对可发布包必需。形状为
  `{"evidence_format":"monasm-evidence/0.1","sources":[{"path","note"}],
  "oracle":{"status","command","skips":[{"case_id","reason"}]},
  "files":[{"path","sha256"}]}`；封闭对象，`sources`/`files` 按 `path` 排序，
  `skips` 按 `case_id` 排序。`sources[].path` 必须也出现在 `files` 中。
  它只覆盖 README/NOTICE/来源记录/oracle 记录/用例证据/`tests/cases.json`；不进入源摘要或
  定义摘要，只进入 lock 的 `evidence_digest` 和 `release_digest`；列出的文件必须存在、
  位于包内且哈希匹配，否则 `evidence-mismatch`（退出码 1）。`files[].sha256`
  和 case 的 `evidence.sha256` 都是 `sha256(raw_file_bytes)`：CRLF/LF、缩进或尾随
  换行改变都算改变，不能先解析再规范化。
- **开发模式与发布模式的证据语义。** 没有清单时，`verify --package` 直接检查每个
  case 的 `evidence.path` 存在且等于 case 自带的 `evidence.sha256`，不计算
  `evidence_digest`，也不要求 `NOTICE`/`sources`/`oracle.status`。清单存在时，
  即使在开发模式也以它为准：case 证据未列出或哈希不符是
  `case-evidence-mismatch`。`--release-evidence`（以及包含它的 `--release`）缺清单
  是 `evidence-incomplete`，绝不降级为开发模式。结构、资产、`read` 和用例契约
  两种模式完全相同，只有这一组发布证据不同。
- 可发布包（被任一已提交 spec 选中，或以 `--release-evidence`/`--release` 校验）
  还要求：`files`
  列出 `tests/cases.json`、`NOTICE`、每个用例的证据文件；至少一条 `sources`
  记录编码事实的来源。`sources[].path` 仍必须是包内已提交的记录（例如
  `evidence/legacy-source.md` 或手册摘录）；迁移包把 `legacy_source` 写进
  `note`，新包指向 `evidence/` 下的手册摘录、厂商文档、反汇编或独立汇编器
  记录；`oracle.status` 和每个 skip 的理由齐全。缺项为 `evidence-incomplete`
  （退出码 1）。因为
  `tests/cases.json` 本身被哈希，改用例会改变 `evidence_digest` 和
  `release_digest`，但不会改变 `source_package_digest` 或 `definition_digest`；
  改了用例却不更新清单是 `evidence-mismatch`。
- 含 forms 的包必须有包根 `tests/cases.json`（`monasm-cases/0.1`，封闭对象，
  `cases` 按 `case_id` 排序）。正例键集恰好是 `case_id`/`form_id`/
  `instruction_id`/`kind`/`plan`/`expect`/`evidence`；负例基本键集恰好是
  `case_id`/`form_id`/`instruction_id`/`kind`/`scope`/`plan`/`expect_error`/
  `evidence`（**没有 `expect`**），`scope:"form"` 时再加 `baseline_case_id`/
  `mutates`。正例写 `scope` 或负例写 `expect` 都是 schema 错误。
  计划是完整 `fmp/0.1` 文档，`definition_identity` 是 `$standalone` 三字段
  哨兵，由 harness 在执行前替换成 §2.4 的独立身份。计划只能有一条
  instruction，其 `instruction_id`/`form_id` 必须等于 case 的对应字段，否则
  `case-form-mismatch`。
- 正例 `expect` 是 §4.2.1 的精确投影：Level 0 恰好
  `format_version`/`level`/`bytes_hex`/`size`/`fixups`；Level 1 恰好
  `format_version`/`level`/`sections`/`fixups`，且仅当
  `output_contract.include_symbol_table` 为真时出现 `symbols`。缺键与空数组
  不等价，harness 不做归一化；键集错误是 `case-expect-shape`。
- 负例必须写 `scope`。`scope:"plan"` 是普通拒绝，可针对错误的
  `expected_digest`、布局、目标，或 `fmp/0.1` 无法表示的值（如 `{"reg":-1}`，
  在 `plan::read` 就是以 `E-PLAN-002` 拒绝），但从不计入 form 覆盖。它用
  `stage:"read"` 记录 `plan::read` 自身的拒绝，用 `stage:"bind"`/
  `"materialize"` 记录文档可读之后的拒绝。`scope:"form"` 必须
  绑定同文件、同 form/instruction 的正例 `baseline_case_id`，并给出单个
  `mutates` 操作数指针；基线和用例计划的 canonical 差分必须恰好是
  `{mutates}`，否则 `case-baseline-invalid`/`case-mutation-mismatch`。
  差分定义在两份**最终值**上，不是作者编辑操作的记录；算法固定如下，
  避免不同 JSON 库报告不同层级：
  1. 相等 → 无指针；
  2. 两个不同类型的值（对象/数组/字符串/数/布尔/null）→ 该位置的指针，因为值本身
     被替换；
  3. 两个对象 → 只在一侧出现的每个键，指针是该键（其下整棵子树算差异）；两侧
     共有键递归；
  4. 两个数组长度不同 → 该数组自身的指针（形状变了）；长度相同 → 逐下标递归；
  5. 两个同类标量不同 → 该位置的指针。

  因此成员增删报告**成员**指针、数组长度变化报告**数组**指针，只有 kind 变化
  报告该位置本身。改写整个对象与只改一个成员在最终值上不可区分，格式不试图
  区分。固定向量：

  ```text
  {"payload":{"reg":10}} → {"payload":{"reg":11}}   ⇒ {/instructions/0/operands/2/payload/reg}
  {"payload":{"reg":10}} → {"payload":10}           ⇒ {/instructions/0/operands/2/payload}
  {"payload":{"reg":10}} → {"payload":{"value":10}} ⇒ 两个指针 ⇒ 不是单次变异
  ```

  结果只取决于两份文档，不取决于遍历顺序或库实现。
  form 负例必须由 `bind` 拒绝（`expect_error.stage` 必须是 `bind`），
  `stage:"read"` 或 `stage:"materialize"` 都是 `case-error-scope`：读取器拒绝
  的值到不了操作数槽位判定，编码后的断言也不是操作数合法性证据。
- form 负例的至少一条 `(code, path)` 必须指向 `mutates` 本身或其父对象：
  path 是 `mutates` 的、在 `/` 边界截断的前缀，且不短于
  `/instructions/0/operands/<n>`。只指向 `/expected_digest`、
  `/expected_size`、`/definition_identity` 或其他 instruction 字段的诊断是
  `case-error-scope`，不计覆盖。form 负例不得声明 `E-BYTE-001` 或
  `E-SIZE-001`；合法寄存器从 0 改成 1、保留旧 `expected_digest` 的反例会在
  `bind` 通过、编码后返回 `E-BYTE-001`，它不是操作数非法性证据。
- `expect_error` 恰好是 `stage` 和非空 `diagnostics`；`stage` 取 `read`、
  `bind` 或 `materialize`，`diagnostics` 每项恰好 `code`/`path`，按
  `(path, code)` 排序且唯一。harness 比较完整的 `(code, path)` 集合，
  多/少/重复都失败（`case-diagnostics-mismatch`）；`materialize` 只接受
  `PostEncodeAssertion`，`Internal`/`HostFailure` 是 `case-materialize-fault`。
  观察集是所声明阶段的完整结果：`read` 只接受 `plan::read` 返回的单个
  `Diagnostic`（读取器报一个故障，不是收集数组）组成的单元素集，读得通就是
  `case-error-scope`；`bind` 要求 `plan::read` 先通过；`materialize` 要求
  `bind` 零诊断。三个阶段的统一规则是：**声明的阶段必须恰是第一个拒绝的
  阶段**；更早阶段已拒绝、或声明阶段放行，都是 `case-error-scope`（退出码
  1），且不构成任何证据。只有 plan 负例可以用 `read` 或 `materialize`；form
  负例的所有 path 还必须在 `/instructions/0` 范围内且至少一条在变异操作数上，
  否则 `case-error-scope`；plan 负例不限。
- 每个用例的 `evidence`（`kind`、`path`、`sha256`）在有证据清单时必须与
  `evidence/manifest.json` 一致；开发模式没有清单时直接核对 case 自带的
  `sha256` 与原始文件字节。没有文件是 `missing-cases`，没有
  `scope:"form"` 负例是 `uncovered-form`，证据对不上是
  `case-evidence-mismatch`（均退出码 1）。这个文件是唯一发现点，不引入中央
  测试列表。
- `verify --package` 使用 §2.4 的独立身份；包级 conformance 用同一身份执行
  用例。`verify --package` 对包合成的 `Definition` 执行
  `fmp_model::definition::read`，并只校验用例的静态契约（`scope`、`stage` 三态
  取值、form 只 `bind`、基线链接、`mutates` 指针与基线/用例计划差分、诊断数组
  形状和错误范围）；它**不**执行用例的 `fmp_model::plan::read`、
  `fmp_model::validate::bind` 或 `fmp_model::materialize::materialize`，因此不
  判断第一个真实拒绝阶段；执行与阶段证明在 `fmp-definition/tests/` 的
  `package_conformance` 中完成，报告分别记录两种状态。
- `cases_format` 只接受 `monasm-cases/0.1`；其他值在解析用例前以
  `case-format-unsupported` 拒绝（退出码 1）。`0.1` 只承诺 H2 的模型：单个
  `fmp/0.1` 计划、恰好一条 instruction、按第一个拒绝阶段记录负例
  （`read`/`bind`/`materialize`）、有操作数的 form 和操作数表面变异。
  H3 的 `fmp/0.2` 和零操作数 form、H4 的多指令/配对 fixup 场景必须引入
  `monasm-cases/0.2`（或显式场景格式）及自己的覆盖规则，不能把 `0.1` 静默
  重解释。case 格式版本与 `package_format` 独立，新增版本不重命名包，也不改
  `source_package_digest`。
- `exports.types` / `exports.profiles`：可选的 `{id, path}` 列表，文件和
  `exports.forms` 一样按 `id` 严格排序，每个文件只放一个 type/profile 对象，
  其 `type_id`/`profile_id` 必须等于声明的 `id`。它们已进入封闭键集和源摘要，
  但 H2 不执行也不输出这些资产，非空列表以 `unsupported-asset` 拒绝。缺省与
  空列表都表示零资产，但它们是不同的清单、得到不同的源摘要；lock 钉住实际
  发布的那一种写法。**这是 `monasm-package/0.1` 的永久结论（第十九轮 P1-2）**：
  文档的含义由它声明的 `package_format` 决定，不由读取它的构建器版本决定；
  升级构建器不得把同一份未改动的 `0.1` 清单从拒绝变成接受，否则重放要依赖
  二进制版本。H4 必须引入显式的新包格式版本（如 `monasm-package/0.2`），在版本
  内定义 type/profile 语义、归属/冲突规则、摘要输入和非空列表所需的验证；
  沿用键名不等于放宽 `0.1`，与 `monasm-bundle-spec/0.1` 的 `h2-exact-target`
  拒绝永久保留同理。冻结的仍只是外层身份、排序、摘要输入和拒绝语义；文件内部
  的 type/profile 语义（共享类型、组合 profile）是 H4 的提案。
- 每个 `forms/*.json` 只放一个 form 对象；迁移包里它就是 legacy 定义里的
  对应行，新包里它由包自己的用例和 oracle 证明。这样归属、摘要和差异都可以
  逐行审查。

### H2-D3 路径边界

- 所有清单路径必须是包内规范化相对路径，使用 `/`；身份、路径段和文件名的
  词法规则见 H2-D1（`ADR-0128` §1.3），在打开前以 `identifier-lexical`/
  `path-lexical`/`bundle-file-mismatch` 拒绝。
- spec 的 `packages[].path` 相对于 `--root`；解析后仍必须位于 `--root` 之下。
- `legacy_source.isa` 和 `legacy_source.version` 在拼成
  `<root>/definitions/<isa>/<version>.json` 之前也按路径组件校验：`isa` 匹配
  `^[a-z0-9_]+$`，`version` 匹配
  `^(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*)){2,}$`；含 `/`、`\`、`..`、
  整段 `.`、盘符、URL scheme 或 NUL 的值直接拒绝，不做「规范化后合法」的修补。
- 拒绝绝对路径、`..`、空段、`.`、反斜杠、NUL、URL scheme、盘符。
- 路径边界是整个读取过程的不变量，不是打开前的一次检查：从 `--root` 到被打开
  文件的每个组件都不得是符号链接或 Windows reparse point，出现即
  `path-escape`（退出码 1）。**仅用 non-follow 元数据预检再按路径打开不算满足**：
  `symlink_metadata()` 之后目录可被替换为链接，随后的 `read()` 仍会跟随，这与
  `canonicalize()` 后再 `open()` 是同一类 check-then-use 缺口。实现必须让
  **打开动作本身**拒绝跟随（相对已打开的目录句柄逐级 no-follow 打开，或使用
  让内核拒绝链接的打开标志），并从该句柄读取；不能事后再按同一路径重开一次。
  平台无法表达 no-follow 打开时以 `path-escape` 失败，不降级为跟随打开。
  `--root` 可规范化一次以确定基准，但其下任何段都不跟随链接。spec 的
  `packages[].path` 和 `legacy_source` 的读取同样适用。H2 不声称抵御构建成功后
  重写工作树的攻击者，也不声称 `--root` 本身可信；它声称一次成功的构建打开的
  正是各项检查所描述的那些对象。
- **逐段精确同名是同一个打开不变量（第十轮 P1-2）。** 相对父句柄枚举目录项并
  要求名字与声明段逐字节相等，是在同一次 no-follow 打开里完成的，不是打开前的
  `stat`、不是绝对路径字符串比较，也不是「宿主能解析就算通过」。声明小写合法而
  磁盘目录项大小写不同（中间目录 `Forms/` 或最终文件 `Add.json`）在任何平台上
  都是 `path-lexical`，构建结论不随文件系统大小写敏感性变化（`INV-05`）。平台
  能力不足时 N1 失败并停止，不降级为跟随打开或按路径重开。
- **匹配与打开之间不得有可替换窗口（第十一轮 P2-3）。** 名字核对通过后再按同名
  打开一次，两步之间目录项可被替换，读到的对象就不是检查描述的对象。实现要么
  打开刚匹配的目录项（句柄或对象身份核对），要么检测到替换并以 `path-escape`
  失败；N1 必须在三平台证明这一点，只测符号链接/reparse point 不算覆盖。
- **叶子必须是普通文件，类型在已打开句柄上判定（第十八轮 P2-1）。** 合法路径的
  no-follow 打开仍可能落在非普通对象上：工作树里 `forms/add.json` 可以是 POSIX
  FIFO、Unix socket 或设备节点，它们不是链接，`path-escape` 不触发；对无写者的
  FIFO 直接 `read()` 会阻塞，长度预算也约束不了没有长度的对象。中间组件必须是
  目录、叶子必须是普通文件；类型取自**已打开的句柄**（POSIX `fstat`、Windows
  `GetFileInformationByHandle`），不取自打开前的路径 `stat`。POSIX 输入打开带
  非阻塞语义（`O_NONBLOCK`），使 FIFO 在类型已知前不会挂起；Windows 没有文件系统
  FIFO，用 `FILE_TYPE_DISK` 加普通文件属性判定。非普通叶子（或需要文件处出现
  目录、需要目录处出现非目录）是 `not-a-regular-file`（退出 1），不是退出 2。
  规则覆盖构建器打开的所有文件：清单、声明资产、用例、证据、spec、lock、
  sealed、legacy 快照和 `bundles/published.json`；写阶段用临时文件加 rename，
  不打开旧产物，因此不需要对应规则。N1 在 POSIX 上增加 FIFO 负例：打开不得
  阻塞，结论必须是 `not-a-regular-file`。
- **路径层是显式依赖，不是可携带的 `std::fs` 调用。** `File::open` 只会跟随
  链接；`OpenOptionsExt::custom_flags` 只影响最后一段。`fmp-definition` 的产品
  依赖因此是 `fmp-model` 加上至多一个固定的路径安全层，它只负责 no-follow 打开，
  不解析清单/定义/摘要；也可以用平台原生调用而不加 crate。候选是否真的在三平台
  成立不在本文假设，由 §6 的 N1 可行性门禁实测。
- 文件列表之外的文件不是输入；`README`/`NOTICE`/`evidence` 可以存在，但不能
  影响执行摘要。

### H2-D4 目标配置

- `BundleSpec` 显式带 `target`：

```json
{
  "bundle_format": "monasm-bundle-spec/0.1",
  "bundle_id": "monasm.bundle.x86_64-mov",
  "target": {
    "profile_id": "monasm.target.x86_64",
    "identity": {
      "isa_family": "x86",
      "isa_variant": "x86-64",
      "execution_mode": "64",
      "enabled_extensions": [],
      "byte_order": "little",
      "address_width": 64
    }
  },
  "definition_format": "fmp-def/0.1",
  "namespace": "monasm.isa.x86",
  "version": "0.1.0-h2",
  "packages": [
    {
      "package_id": "monasm.x86.mov-register",
      "version": "0.1.0",
      "path": "packages/x86_64/monasm.x86.mov-register/0.1.0",
      "source_package_digest": "sha256:..."
    }
  ]
}
```

- `packages` **就是完整闭包**，不是「根集合」，且按 `(package_id, version)`
  严格排序、无重复；逆序是拒绝，不是被重排。构建器只读取这里列出的 `path`，
  从不扫描 `packages/` 目录；依赖边只用于校验，不用来发现新包。
- 每个 `path` 的末段必须同时等于 spec 的 `version` 和包清单的 `version`；
  不一致是 `path-version-mismatch`（退出码 1）。base 已发布的版本目录不可变
  （以 `bundles/published.json` 判定，H2-D1）：普通包更新不会改写旧 path，
  旧 spec/lock 仍可重建；同一 PR 首次创建并登记的版本按最终快照校验。
- `target.identity` 的结构字段（`isa_family`、`isa_variant`、`execution_mode`、
  `byte_order`、`address_width`）和 `definition_format` 必须与**每个包自己声明
  的**对应字段相等；它们不再从包钉住的 legacy 定义推导。`fmp-def/0.1` 与
  `fmp-def/0.2` 的 form 行不是同一种对象：0.2 的 x86 行多出 REX 位放置和
  `requires_extensions`，而 0.1 的 reader 会因未知键拒绝 0.2 行；反之 0.1 行
  放进 0.2 文档会缺必需键。构建器必须让 spec、包自述和行三者互相一致；混合
  格式的闭包直接拒绝，不做隐式转换，显式版本化转换属于 H3。
- **`enabled_extensions` 是保守声明覆盖，不是最小集合（第一轮 P1-3，第九轮
  P2-4）。** 包的列表是作者声明的覆盖：它包含所有行的需求，并且是选择该包的
  bundle 必须至少提供的集合；它不是「恰好等于行并集」的最小集合。spec 的列表
  表示「这个 bundle 选中了哪些扩展」。构建器证明的是
  「并集 ⊆ 包声明 ⊆ bundle 选择」，不证明包声明等于行的并集：`fmp-def/0.1`
  的 form 没有 `requires_extensions`，`fmp-def/0.2` 的 form 列表也不是完整
  目标（不含基础 ISA/profile 事实），等式规则只能凭空补一个需求。因此高报
  合法且有实际效果：行的需求只有 `rv64i`、但包声明 `["rv64c","rv64i"]` 时，
  它不能被只选 `rv64i` 的 bundle 选中——这是作者的选择，不是不一致。构建器
  不把声明裁剪成并集，否则 `source_package_digest` 描述的需求与作者写下的
  不同，包也会在没有编辑的情况下变得可选；要更窄的需求就发布声明更窄的新
  版本。低报仍然是错误，由 form ⊆ 包检查拒绝。这样新增一个 `rv64c` 包时，
  `rv64i` 算术包的清单不需要改，源摘要不变，不会把无关包重新发布一次。
- **扩展与能力数组只有一种写法（第十二轮 P2-2）。** 包的
  `target_identity.enabled_extensions`、spec（以及 lock/sealed 复制的
  `target.identity.enabled_extensions`）和包的 `requires_capabilities` 都必须是
  严格递增、无重复的数组：集合关系按成员判定，但逆序或重复是**格式拒绝**，
  不是第二种等价写法。例：`["rv64c","rv64i"]` 合法，`["rv64i","rv64c"]` 是逆序
  拒绝。错误分别是 `extension-lexical` 与 `capability-lexical`
  （退出码 1），发生在任何子集判定之前。理由与 `requires_extensions`、
  `exports.forms` 的既有严格排序一致：同一集合若允许两种 JSON 写法，清单、
  合并文档和摘要就会有两个身份，`source_package_digest` 也无法区分「改了写法」
  与「改了语义」。派生能力集合仍是按成员比较的等值检查；数组写法先被词法规则
  固定，不做隐式重排。这条规则只约束包清单和 spec 输入，不重写 `definitions/`
  里冻结的 legacy 文档——`rv64/0.6.0.json` 保持已发布的 `["rv64i","rv64c"]`，
  消费者按集合比较（`check_target` 把两侧收进 `BTreeSet`）。
- **子集规则按 form、包、bundle 三层逐包检查（第八轮 P1-3）。** 只查
  「包 ⊆ bundle」不够：bundle 更宽的扩展集合会替一个欠声明的包放行。完整规则是

  ```text
  E_form(f) ⊆ E_package ⊆ E_bundle     对每个选中包 P 和每个 f ∈ P.forms
  ```

  `E_form(f)` 在 `fmp-def/0.2` 下是 `form.requires_extensions`，在
  `fmp-def/0.1` 下是空集（该格式的 form 对象没有这个键，`FORM_FIELDS` 会拒绝）。
  `E_package` 是包声明的**保守覆盖集** `target_identity.enabled_extensions`，
  `E_bundle` 是 spec 的 `target.identity.enabled_extensions`。这个式子只表示
  包含关系，不表示相等：并集 ⊆ 声明 ⊆ 选择。构建器先对每个包求所有导出 form
  的 `E_form` 并集，若该并集不被包自身声明覆盖，以 `form-extension-mismatch`
  （退出码 1）拒绝；随后才检查声明 ⊆ bundle。高报合法，只缩小该包可被哪些
  bundle 选中；构建器不把声明裁剪成并集。
- **`fmp-def/0.1` 下第一项包含检查是空真（第十二轮 P2-4）。** 因为
  `E_form(f) = ∅`，`⋃E_form ⊆ E_package` 对每个包都自动成立，无法发现 form
  真正需要、而清单漏报的 ISA 扩展。H2 对 `0.1` 包实际证明的是
  `E_package ⊆ E_bundle`：声明的覆盖落在所选目标内。`legacy_source` 只额外提供
  target 一致性（`definition_format` 相等，`target_identity` 满足 `TargetEq`：
  除 `enabled_extensions` 按集合外逐字段相等；不一致是
  `legacy-target-mismatch`），仍不从行体推导 ISA 需求；没有 `legacy_source` 的
  新包依赖作者声明和包自己的用例/证据。构建器不得为消除这个限制而发明 ISA 专用
  推导器——那会让它成为第二套 ISA 语义权威（`ADR-0125`）。H2 验收报告必须写明
  「包目标覆盖关系已验证」不等于「真实 ISA 扩展需求已被完整证明」；收窄覆盖只能
  由作者发新版本完成。
- **每个选中包先按自己的目标 `read`（第八轮 P1-3）。** `read` 把 form 的
  `requires_extensions` 与**生成文档**的目标集合比较，而生成文档带的是 bundle
  的目标。因此一个包可能只在合并后才合法，而 `verify --package` 按包自己的目标
  会拒绝它，同一份字节出现两个结论。构建器在合并之前，用该包自己的行和自己的
  `target_identity` 组成文档、按该包的 `definition_format` 调用 `read`；失败即该
  包自己的 `read` 拒绝。合并后的文档仍照常再 `read` 一次，归属/身份/摘要检查不变。
  反例：`fmp-def/0.2` 包声明 `["rv64i"]`、其中一条 form 需要 `["rv64c"]`，spec
  选中 `["rv64c","rv64i"]`。包 ⊆ bundle 通过，合并后的 `read` 也通过；但
  `verify --package` 用包自己的目标 `["rv64i"]` 会失败。正确修法是把 `rv64c`
  加进清单，而不是靠更大的 bundle 让行变合法。H2 的三个包都是 `0.1`，无法在
  form 层表达这个错误，所以 H2a 用 `0.2` fixture 测这条规则，不从三个 `0.1`
  包反推。
- **高报扩展是合法的，不可被裁剪（第九轮 P2-4）。** 反例：一个包的所有行只需
  `rv64i`，清单声明 `["rv64c","rv64i"]`，spec 选中 `["rv64c","rv64i"]`；所有
  检查通过，包合法，但它不能被只选 `rv64i` 的 bundle 选中。把声明当作「恰好
  等于行的并集」的实现会裁剪声明（改变作者的 `source_package_digest`，并让包
  在没有编辑的情况下变得可选），或错误拒绝作者故意覆盖的 bundle。H2 保留作者
  声明，高报只缩小可选范围；精确性需要后续版本化规则定义完整需求。
- H2 的过渡规则：`bind` 的集合关系取自**定义**格式，不是计划格式
  （`fmp-validate/src/lib.rs` `check_target`：`subset_rule =
  definition_format == fmp-def/0.2`）。`fmp-def/0.1` 定义按集合相等比较
  `enabled_extensions`，`fmp-def/0.2` 要求计划集合 ⊆ 定义集合，并在之后检查逐
  form 需求。因此 `definition_format == fmp-def/0.1` 时，H2 额外要求包的声明
  覆盖与 spec 选择**完全相等**（`h2-exact-target`）；这不是永久包契约。
- **解除按协议能力、不是删检查（第十、十一轮 P2-1；第十四轮 P2-2）。** 现有的
  两个（计划, 定义）格子必须保持不变（矩阵见本节末）：`fmp/0.1` +
  `fmp-def/0.1` 是集合相等，`fmp/0.1` + `fmp-def/0.2` 是计划集合 ⊆ 定义集合加
  逐 form 需求。增加格子并解除 `h2-exact-target` 需要**新的计划协议**且需要
  **版本化构建规则**，两者必须同时成立；把规则改成按计划格式判断会重新拒绝
  已经合法的 `fmp/0.1` + `fmp-def/0.2`。要改 `fmp-def/0.1` 的相等规则，必须
  引入新版本化契约而不是删除旧检查；构建选项不能改变任一格子。
- **构建期与执行期是两扇门，必须都打开（第十四轮 P2-2）。** Builder 处理的是
  spec 与包，在任何计划被绑定**之前**就按 `h2-exact-target` 拒绝不相等的
  `fmp-def/0.1` 选择，所以只增加 `fmp/0.2` 计划格式不能使该 spec 构建成功。
  解除必须同时包含：一条**版本化构建规则**（新的 `monasm-bundle-spec` 版本，
  或 Builder 读取的显式版本化兼容关系），以及上面的计划侧格子。已发布的
  `monasm-bundle-spec/0.1` 永久保留其拒绝结论：同一份 spec 字节不能因为
  Builder 软件升级而从确定性拒绝变成接受，那等于静默改变旧格式的接受语义。
  H3 验收必须对同一组合（例如 `rv64i`-only 包 + `rv64c`/`rv64i` bundle）证明
  三件事：旧 spec 版本仍拒绝不相等的选择、新构建规则版本能构建、得到的 bundle
  能绑定目标集合为子集的计划；第一条是 `0.1` 语义未漂移的证据，第二条才在
  Builder 端（而不只是计划校验器端）解开 H5。
  H3 必须用同一包、不同扩展集合跑矩阵：旧格子保持结果，新格子只在自身规则
  允许处接受子集；「删掉检查后能构建成功」不是新规则的证据。这些规则必须在 H5
  并行扩展演练之前生效，否则先修订 ADR，不得直接开始 H5。H2 不声称这个等号
  是最终组合规则。`h2-exact-target` 与上面的 form ⊆ 包检查互不替代：前者比较
  包与 bundle，后者比较行与包。
- **H3 的子集规则必须逐指令证明（第二十轮 P1-1）。** 只查
  `E_plan ⊆ E_bundle` 不够：bundle 选 `{rv64i, rv64c}`、包 A 覆盖 `{rv64i}`、
  包 B 覆盖 `{rv64c, rv64i}` 时，声明 `{rv64i}` 的计划仍可选中 `c.addi`，而它的
  归属包需要 `rv64c`。H3 必须对每条选中的指令检查

  ```text
  E_owner(form(i)) ⊆ E_plan     对 Plan.instructions 中的每条 i
  ```

  `E_owner` 优先取版本化定义里的逐 form 需求，否则取该 form 归属包的声明覆盖
  （保守但不会放行计划目标不支持的指令）；从 mnemonic 或 ISA 名推导需求是
  `INV-01`/`INV-06` 禁止的。`fmp-def/0.2` 的 `E-TARGET-003` 已按**计划**集合
  检查 form 需求，所以缺口是 `fmp-def/0.1`/legacy form（没有该键）与 0.2 行
  低报（需求列表不含基础 ISA/profile 事实）。
  **H2 冻结的 sealed bundle 不足以支撑该检查**：`monasm-bundle/0.1` 只有合并
  定义和 `sources`，没有 `form_id → owner` 或 `E_package`；lock 只有 path/摘要。
  H3 必须先取得版本化 bundle（如 `monasm-bundle/0.2`）中的逐 form 需求或可验证
  归属/覆盖映射，或另一个同样冻结、摘要绑定且有门禁的来源，然后才可接受子集
  计划。只增加 `fmp/0.2` 不放宽；重新解释 `0.1` bundle 等于改格式。
  **缺少归属证明的 legacy form 默认拒绝**（`target-subset-unproved`，H3 协议自己
  的诊断，不是 `fmp/0.1` 码），不能按空集推定其对任何扩展配置都合法；精确目标
  格子不受影响，因为那里所有集合相等。H3 验收至少证明：`c.addi`/`rv64i` 计划被
  拒、包含归属覆盖的计划通过、无证明的 0.1/legacy form 被拒而不是当作空集、
  两个旧格子保持 H2 结果。H2 不实现该规则，也不向 `monasm-bundle/0.1` 加映射；
  义务现在写入，避免冻结 H2 后让 H3 无法证明。
- `target.profile_id` 必须与每个包的 `target_profile` 一致，否则构建失败。
  这是一次**包内名义标签**检查，不是全局目标身份：两个 spec 可以用同一个
  `profile_id` 搭配不同的 `target.identity`，H2 视之为不同目标，兼容性、
  生成文档、lock 和 sealed bundle 一律以六键 `target.identity` 为准。H2 不加
  `(profile_id, identity)` 的跨 spec 唯一性，也不建中央 profile 表；否则
  「同名多义」会被误读成已发布的全局事实。若后续阶段要让 `profile_id` 唯一
  指向一份目标事实，必须走版本化格式变更，不能假设 H2 已经如此。
- **form 家族一致性（第二轮 P1-3）。** 每个导出 form 的 `form_id` 前缀（`:` 前）
  必须等于包声明的 `target_identity.isa_family`。这是一条字符串相等不变量，
  不是包格式里的 ISA 白名单：H2 的 `fmp_model::definition::read` 仍只认识
  `x86`/`aarch64`/`riscv`，那是定义读取器已有的检查；H3 增加第四种家族时，
  只要 `family(form_id) == isa_family`，包格式和构建器都不需要改。真正的别名
  （两个字符串不同）由版本化 target profile 声明。不一致是
  `form-family-mismatch`（退出码 1），在调用 `read` 之前拒绝。未来
  不能通过往构建器里追加 ISA 名单解决。
- H2 不引入 `target profile` 的中央 Rust 表。目标事实由包清单和 spec 数据共同
  提供，这正是 H3「新目标不改公共白名单」的前置条件。
- 没有 `legacy_source` 的新包不需要先写进任何 spec：`verify --package` 用包
  自述的目标、独立身份（§2.4）、`read` 合并文档和包自己的用例完成校验。这是
  普通扩展作者的独立测试路径，也是 H2 证明作者协议不永久依赖历史定义的方式。
- `fmp-def/0.1` 按集合相等比较 `enabled_extensions`，`fmp-def/0.2` 把表集合
  当上限。H2 只复用这两条既有规则，不改变任何一条；上面的过渡等号是构建器
  在 0.1 上的附加检查，不是修改 `bind`。

**目标兼容矩阵（H3 必须保持既有两个格子，只允许新增计划协议格子）：**

| 计划协议 | 定义协议 | 当前关系 |
|---|---|---|
| `fmp/0.1` | `fmp-def/0.1` | 集合相等 |
| `fmp/0.1` | `fmp-def/0.2` | 计划集合 ⊆ 定义集合，另加逐 form `requires_extensions` |
| 新的计划协议（H3） | 由该协议声明 | 只在新协议规则允许处接受子集 |

实现依据是 `check_target` 的 `subset_rule`，它只读定义格式；按计划格式选择
关系会把第二行从“合法”改成“拒绝”，这是必须在 H3 验收中单独覆盖的反例。
第三行不仅需要计划侧的新格子：Builder 在绑定计划前就按 `h2-exact-target`
拒绝不相等的 `fmp-def/0.1` 选择，所以 H3 还必须带一条版本化构建规则，并证明
`monasm-bundle-spec/0.1` 对同一选择仍拒绝（§H2-D4 上一段）。

### H2-D5 依赖闭包：spec 列全，构建器不扫描

- `BundleSpec.packages` 列出闭包内的每个包（ID、version、path、digest）。
  构建器只打开这些 path；`packages/` 目录里多一个或少一个文件都不影响构建。
- 每个包清单的 `dependencies` 是校验边：每个 `{package_id, version,
  source_package_digest}` 必须精确对应 spec 列表中的一项，且 digest 必须等于
  该包的实际 `source_package_digest`。依赖不能引入列表外的包。
- 闭包验证有两个入口，且都不信任文件里写的摘要：`verify --all` 从 spec
  重读每个包并重算 `source_package_digest`；`verify --package --closure <lock>`
  打开 lock 中的每个依赖 `path`，重算其 manifest+资产摘要，并要求该值同时等于
  lock 条目和依赖方的 `dependencies[].source_package_digest`。不一致是
  `dependency-mismatch`（退出码 1）。手写 lock 只能声明它读过哪些包，不能凭
  声明得到 `dependency_closure: verified`。
- **闭包检查是传递的。** 从被验证包出发，对每个 `dependencies` 项解析精确
  `(package_id, version)`、重读该包、重算摘要，再递归检查它自己的依赖，直到
  所有可达包都检查过。lock/spec 必须包含完整传递闭包：A→B→C 时缺 C、C 的
  digest 错误、重复身份、依赖环或任何边不符都是 `dependency-mismatch`；只检查
  直接依赖不算 verified。闭包深度仍受 §12 的 64 层限制。
- 普通作者路径不要求先改全局 spec：未选中包跑 `verify --package`（结构）和
  `package_conformance`；所有变更包还跑 `--release-evidence`，它要求完整发布
  证据但不声称闭包。`--release` 是 `--release-evidence` 加闭包：依赖为空时直接
  通过，依赖非空时没有 `--closure <lock>` 就是 `dependency-unverified`（退出码
  1）。作者可以在自己的 PR 里带一个精确的本地 lock 来跑 release；只有被发布
  spec 选中时才由 `--all --check` 以 spec 闭包做完整 release 校验。H2 的三个包
  都没有依赖。
- 同一 `(package_id, version)` 或同一 `path` 在 spec 中出现两次：拒绝。两个包
  通过不同 path 声明同一 `(package_id, version)` 且内容相同也拒绝——身份是
  发布事实，不是内容比较的结果。
- 同一 `package_id` 在同一闭包中最多出现一个版本；两个版本即使导出集合不相交
  也拒绝（`version-conflict`）。否则 lock 无法说清哪个版本拥有未来新增的行。
- 依赖缺失、版本不精确、digest 不匹配、依赖环：拒绝。
- 一个未被任何包依赖的列表项是合法的根包；构建器不要求「可达性」。
- `--all` 只枚举 `bundles/specs/*.json`，逐个按上述规则构建；它从不枚举
  `packages/**`。因此新增或损坏一个未选中的包不会改变旧 spec 的结果
  （`HE-AC-05` 的构建期部分）。
- `verify --package <path>` 不读 spec，用 `monasm-standalone/0.1` 独立身份检查
  单包契约（清单、路径、导出、`read`、用例覆盖、证据引用）；它和
  `verify --all` 是两条门禁：前者覆盖尚未进入发布 bundle 的新包，后者覆盖
  发布组合。CI 的变更路径列表只决定跑哪些 `--package`，不决定构建器选择什么。
  机器码执行由 `package_conformance` 承担（§2.4、§5.3）。
- **结构与依赖闭包是两个状态。** 每次 `verify --package` 分别报告
  `structure` 和 `dependency_closure`。没有显式闭包输入时，`dependencies`
  为空的包是 `dependency_closure: verified`（没有可解析项），非空则是
  `unverified`。`--release` 下非空且未提供 `--closure <lock>` 是
  `dependency-unverified`（退出码 1）；开发运行可以只为 structure 退出 0，但
  必须打印 unverified。`verify --all` 使用 spec 闭包。H2 三个包都无依赖；
  未来的共享类型包必须显式提供闭包，不能靠清单形状声称已验证。

### H2-D6 归属与冲突

构建时建立三张只读表：

```text
form_id    -> package_id + version + source_package_digest
type_id    -> package_id + version + source_package_digest     # 已定义键与摘要；H2 拒绝非空声明
profile_id -> package_id + version + source_package_digest     # 已定义键与摘要；H4 才使用语义
```

- 两个包导出同一 `form_id`，即使行内容完全相同，也必须失败。理由：归属是
  发布事实，不是内容比较的结果；last-wins 会让合并顺序决定语义。
- 公共依赖包在闭包中重复出现且精确身份一致时只加载一次。
- H2 只执行 `form` 资产。`type_id`/`profile_id` 的键、`{id, path}` 形状、
  排序和摘要输入已经定义；非空的 `exports.types`/`exports.profiles` 以
  `unsupported-asset` 拒绝，H4 才加入语义。H2 不会静默忽略未支持资产。

### H2-D7 规范化与顺序

- 所有输出使用 `fmp_model::canonical`：键排序、无空白、UTF-8、无 BOM、无
  尾随换行。
- 合并后的 `forms` 按 `form_id` 的 Unicode 码点升序规范化；**这是构建期的
  包集合规范化，不是程序布局排序**（设计 §4：包排序与布局排序分开）。
- slot、placement、modifier、excluded 的数组顺序保持声明顺序；这些顺序有
  位域语义，构建器不得重排。
- 包的 `exports.forms`/`types`/`profiles` 与 `dependencies` 已在清单层强制排序，
  重排是拒绝而不是第二种写法；spec 的 `packages` 也必须按
  `(package_id, version)` 严格排序（§8.2），逆序是拒绝，不是被静默重排。目录
  发现顺序和内部集合迭代顺序不参与摘要；构建器校验声明顺序后按身份哈希闭包。
- 集合字段 `requires_capabilities`、包的 `target_identity.enabled_extensions`
  和 spec/lock/sealed 的 `target.identity.enabled_extensions` 采用唯一写法：
  严格递增、无重复（第十二轮 P2-2）。逆序是 `extension-lexical`，重复的
  capability 是 `capability-lexical`（退出码 1），在集合关系之前拒绝；规范化
  只作用于构建器自己生成的排序，不修复作者写下的数组。

### H2-D8 摘要分层

所有摘要都是 SHA-256 作用于精确字节串，规则属于 `monasm-package/0.1`：

- 域分隔是 ASCII 字面量后紧跟一个 `0x00` 字节，无换行；
- `canonical` 是 `fmp_model::canonical`：UTF-8 无 BOM、键按码点排序、无多余空白、
  无尾随换行、只有整数；
- JSON 字符串里的摘要值是字面 `sha256:` + 64 个小写 hex，按这段文本哈希，
  不是 32 个原始字节，也不是大写 hex；
- `evidence/manifest.json` 的 `files[].sha256` 和 case 的 `evidence.sha256`
  是裸 64 个小写 hex，无前缀，并且是**原始文件字节**的 SHA-256（含换行和空白）；
  不先解析或规范化。CRLF/LF、缩进或尾随换行改变都会改变摘要，适用于
  `NOTICE`、Markdown、oracle 文本和 `tests/cases.json`；
- 连接就是字节连接，没有长度前缀或行中未写出的分隔符。

| 摘要 | 输入 | 不包含 | 反例（缺它会怎样） |
|---|---|---|---|
| `source_package_digest` | `sha256(b"monasm-package/0.1" ++ 0x00 ++ canonical(record))`，`record = {manifest, assets:[{kind, path, digest}]}`，assets 按 `path` 排序，`digest` 是字面 `sha256:<hex>` 文本 | README、NOTICE、evidence manifest、测试、作者路径 | 只哈希 manifest：换掉 form 的 template 而清单不变，包摘要不动 |
| `evidence_digest` | `sha256(b"monasm-evidence/0.1" ++ 0x00 ++ canonical(evidence/manifest.json))`；可发布包的 `files` 必须含 `tests/cases.json` 的哈希；文件不存在时省略 | 清单未列出的 README/NOTICE 文字、oracle 日志内容、作者路径 | 不哈希 `tests/cases.json`：改测试计划或期望后发布身份不变，同一 release 对应两套测试集 |
| `definition_digest` | `fmp_model::definition::read(merged).digest()`，即 `sha256(canonical(merged_document))`，无域分隔 | builder 版本、构建时间、主机 | 只哈希包集合：两个不同 form 行得到同一 bundle 身份 |
| `bundle_digest` | `sha256(b"monasm-bundle/0.1" ++ 0x00 ++ canonical(metadata))`；metadata 含 `bundle_id`、`definition_format`、`namespace`、`version`、`target`、排序后的 package 身份、`definition_digest`；嵌套摘要按字面 `sha256:` 文本 | bundle 自身的 `bundle_digest` 字段、builder 版本 | 把自身字段算进去：自引用，永远算不出固定点 |
| `release_digest` | `sha256(b"monasm-release/0.1" ++ 0x00 ++ canonical({bundle_id, bundle_digest, definition_digest, packages:[{package_id, version, source_package_digest, evidence_digest}]}))`，按包身份排序；嵌套摘要按字面文本。发布 lock 必写 `evidence_digest`；只有开发构建可省略，而开发构建不是发布身份 | 定义行本身、builder、sealed 字节 | 同一 bundle 的两份发布证据无法区分 |
| `builder` | `{name, version, build: Option<String>}`，只进 lock/收据；`build` 缺失时省略键，绝不写 `null` | 不进入 definition_digest | 把构建版本算进定义摘要：换一个 builder 版本就误报定义漂移（`HE-T19`） |

固定向量（H2a 的 Rust 与 Python 测试都必须逐字节通过；完整 canonical record
见 `ADR-0128` §7.0）：

```text
manifest canonical =
{"definition_format":"fmp-def/0.1","dependencies":[],"exports":{"forms":[{"id":"x86:example/form","path":"forms/example.json"}],"profiles":[],"types":[]},"package_format":"monasm-package/0.1","package_id":"monasm.x86.example","requires_capabilities":[],"target_identity":{"address_width":64,"byte_order":"little","enabled_extensions":[],"execution_mode":"64","isa_family":"x86","isa_variant":"x86-64"},"target_profile":"monasm.target.x86_64","version":"0.1.0"}
asset canonical = {"form_id":"x86:example/form","template":"90"}
asset digest = sha256:dedb7fdf0544fde88996bcc92886284ac32930e99c0db6bce62ef60fedb71301
source_package_digest = sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0
```

该向量已用 Python `hashlib` 和 .NET `SHA256` 独立计算，结果相同；它验证的是
字节，不是某个平台的序列化。它是**摘要预映像 fixture，不是可构建的包**：
`forms/example.json` 没有 `slots`、ID 也缺 `/legacy` 段，`definition::read` 会
拒绝它，`requires_capabilities: []` 对含 forms 的合法包也不成立（H2-D2）。
它只用来钉字节规则，永不进入 `read`；端到端合法例子是 §1 的两条真实 x86
`0.1.0` mov 行。

非空依赖数组的固定向量（同见 `ADR-0128` §7.0；它是依赖边格式，不是可构建的
H2 包）：

```text
dependency object canonical =
{"package_id":"monasm.x86.base","source_package_digest":"sha256:231b9034ecbe6c9f806f7f2a647295e47a57cddcff47e4afacb24c98510648bf","version":"0.1.0"}
dependent asset canonical = {"form_id":"x86:example/dependent","template":"90"}
dependent asset digest = sha256:93e471b1fda937f2a3cab2b0de0d6131f347a4b967972960ca76bf4a4d7b0ccc
dependent source_package_digest = sha256:637edab0e19dc949bf44994d36fd703b97ecf3d9145d2648f22729b16f748251
```

依赖对象只有 `package_id`/`version`/`source_package_digest` 三个键，键名或可选性
一变摘要就变；该值已用 Python `hashlib` 与 .NET `SHA256` 独立算出，结果相同。

bundle/release 元数据向量（完整形状与键集见 `ADR-0128` §8.2；`definition_digest`
取钉住的 x86 `0.1.0` 值，只固定字节规则，不声称是最终 H2 bundle 身份）：

```text
bundle metadata canonical =
{"bundle_id":"monasm.bundle.x86.example","definition_digest":"sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad","definition_format":"fmp-def/0.1","namespace":"monasm.isa.x86","packages":[{"package_id":"monasm.x86.example","source_package_digest":"sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0","version":"0.1.0"}],"target":{"identity":{"address_width":64,"byte_order":"little","enabled_extensions":[],"execution_mode":"64","isa_family":"x86","isa_variant":"x86-64"},"profile_id":"monasm.target.x86_64"},"version":"0.1.0-h2"}
bundle_digest = sha256:b6d925747e41428db2e6dd31d72d7bd05739ab8d552fb53bcd73402af54931fd

release metadata canonical =
{"bundle_digest":"sha256:b6d925747e41428db2e6dd31d72d7bd05739ab8d552fb53bcd73402af54931fd","bundle_id":"monasm.bundle.x86.example","definition_digest":"sha256:c6bfa90e3fa100f1613537c48cec23e510c424927a2ac62c9bb4449b7f4ebbad","packages":[{"package_id":"monasm.x86.example","source_package_digest":"sha256:1afee65ce87cd9e5ff52f7ae8db11fdb6f7c62201e315641417c4e78cb12bca0","version":"0.1.0"}]}
release_digest = sha256:4e3d44a86a966b7d1829d823c6aad00f92cc08a567eee7d23e70e4ecfa6bf8cc
```

域分隔字面量与算法名一起冻结；改算法名必须同时改域分隔。`legacy_source` 是
清单键，存在时进入 `source_package_digest`；`evidence/`、`README`、`NOTICE`
不进源摘要或定义摘要。`evidence_digest` 在证据清单存在时生成；可发布包必须
有该清单，因此发布 lock 总有它。它只进 lock 的 `release_digest`；执行规则
身份与审计证据身份因此分开，发布时仍可通过 lock 追踪二者。

上面的 release 向量是开发形状，故意不带 `evidence_digest`。发布形状另有一个
固定向量（完整字节见 `ADR-0128` §8.2），输入是同一包、同一定义、同一 bundle，
只有包项多一个 `evidence_digest`，因此 `bundle_digest` 不变：

```text
evidence_digest          = sha256:e94738716ffc56d6f1a865c463fee4afae03835d51ef234bff2c213e321f931a
release_digest (released) = sha256:ba60e8bab8f15ae57972ee24510798fc7721430fa4508dc810011a753a8d3235
```

Rust 与 Python 都必须复现开发向量和发布向量这两个值。差别恰好是包项是否带
`evidence_digest`：把开发形状写进提交的 lock 会在字节上失败，而不是静默发布一个
证据不在发布身份里的 bundle。`tests/cases.json` 的 fixture 字节只作为摘要输入，
真实发布仍需每个 form 的正例（§9.1）。

### H2-D9 spec、lock、sealed bundle、published registry

- `bundles/specs/<bundle_id>.json`：发布者写的显式选择（`monasm-bundle-spec/0.1`）。
  封闭键恰好是 `bundle_format`、`bundle_id`、`target`、`definition_format`、
  `namespace`、`version`、`packages`；`target` 恰好 `profile_id`/`identity`，
  `packages` 每项恰好 `package_id`/`version`/`path`/`source_package_digest`，
  且整个数组按 `(package_id, version)` 严格排序、无重复；逆序或重复是拒绝，
  不是被静默重排。
- 产物文件名是身份的一部分（第九轮 P2-1，`ADR-0128` §1.3）：
  `bundles/specs/<bundle_id>.json`、`bundles/locks/<bundle_id>.lock.json`、
  `bundles/sealed/<bundle_id>.bundle.json`、`bundles/legacy/<bundle_id>/definition.json`。
  `<file>` 与文档 `bundle_id` 不一致是 `bundle-file-mismatch`（退出码 1），
  `--all` 不靠目录约定猜归属。
- **派生产物只在其 spec 存在时存在（第十八轮 P2-2）。** 删除最后一个
  `bundles/specs/<bundle_id>.json` 的同一 PR 删除该 bundle 的 lock、sealed 和
  legacy 快照。`verify --all --check` 双向检查一一对应：每个 spec 仍有已提交的
  lock 和 sealed，`bundles/locks/`、`bundles/sealed/`、`bundles/legacy/` 下每个
  文件都必须有同树 spec，孤儿是 `orphan-bundle-artifact`（退出 1）。该检查只枚举
  目录项，不打开未选中包，也不改任何摘要，所以不影响 `HE-AC-05`。退役字节在发布
  它的提交上仍可重放；包快照与登记项保留，H2 不定义归档格式（`ADR-0128` §8.4）。
- 整个 spec 集合按 `bundle_id` 和 `(namespace, version)` 全局唯一：两个 spec
  共用 `bundle_id` 是 `bundle-id-conflict`，共用定义身份是
  `definition-identity-conflict`（均退出 1），即使 `definition_digest` 相同也
  拒绝。同时存活的 spec 不能共用一个 `bundle_id`：重名会让两份不同闭包的 lock
  共享同一身份（若产物名由它派生，还会互相覆盖），并使结果取决于目录迭代顺序。
  但 `bundle_id` 本身是**可移动的发布线**，退役后可由新 spec 推进到新版本；不可
  变标签是 `(bundle_id, bundle_digest)`。定义身份是 `Registry::find` 的唯一键，
  现有 reader 对两份同身份定义返回 `E-DEF-001`。三个 H2 spec 使用不同身份，
  H2 不引入共享身份的映射。
- `bundles/locks/<bundle_id>.lock.json`：构建器生成的 `monasm-lock/0.1`。封闭键
  恰好是 `lock_format`、`bundle_id`、`definition_format`、`namespace`、
  `version`、`target`、`bundle_digest`、`definition_digest`、`release_digest`、
  `packages`、`builder`；包项恰好 `package_id`/`version`/`path`/
  `source_package_digest`/`evidence_digest`。`builder` 恰好 `name`/`version`
  和可选 `build`，没有 build 标识时省略键，绝不写 `null`。`--check` 比较
  **去掉 `builder` 后的 canonical 字节**；builder 只做形状检查和打印。
- `bundles/sealed/<bundle_id>.bundle.json`：扁平化的 `monasm-bundle/0.1`，封闭键
  恰好 `bundle_format`、`bundle_id`、`definition_format`、`definition_digest`、
  `bundle_digest`、`definition`、`packages`；`definition` 是 §9 的合并定义
  文档，包项恰好 `package_id`/`version`/`source_package_digest`。没有 `path`、
  `builder`、`release_digest` 或 `evidence_digest`，因此逐字节比较，没有排除键。
- 若 `<legacy>/definition.json` 存在，`--check` 还要求它与已校验 sealed bundle
  的 `definition` 对象的 canonical 字节完全一致，不同是
  `legacy-snapshot-mismatch`（退出 1）；缺失则跳过，因为它是派生缓存。该比较
  只读 16 MiB 上限内的字节，不重建缓存，也不进入任何摘要（第十四轮 P1）。
- 三者的未知键/重复键都拒绝；spec、lock、sealed 的完整最小样例和
  `bundle_digest`/`release_digest` 固定向量见 `ADR-0128` §8.2。
- `bundles/published.json`：`monasm-published/0.1`，封闭键恰好
  `published_format`/`published`/`identities`。`published` 每项恰好 `path`/
  `package_id`/`version`/`source_package_digest`，按 `path` 严格排序；`path` 唯一，
  `(package_id, version)` 也**全局**唯一；同一逻辑版本永久绑定首次合并登记的
  `path` 和摘要，多个 spec 只能引用同一项。`identities` 每项恰好
  `definition_digest`/`namespace`/`version`，按 `(namespace, version)` 严格排序；
  首次合并登记永久绑定该定义名与摘要（细节见 H2-D1）。两个数组都可为空。
  它是**只追加的发布登记**：base 条目不得删除、改写或重排；删除/改写是
  `published-registry-modified`，`verify --all --check` 时 spec 选中但未登记是
  `published-registry-incomplete`，登记与包摘要不符、新增项
  未被任何 head spec 选中，或同名版本换路径/摘要再次登记是
  `published-registry-invalid`；定义名换摘要是 `definition-identity-conflict`。
  同一 PR 首次创建并登记版本是合法的首次发布：只保护 base 条目，head 条目在
  合并前按最终快照校验。它不进入 bundle/release 摘要，也不是选择输入；删除 spec
  不删除登记项。这是 `ADR-0128` §8.3 的 H2 形状。
- **首次发布无登记循环；`build` 先内存校验再替换文件（第九轮 P2-3）。** 顺序
  是：候选 `<version>/` 目录 → 计算 `source_package_digest` → 写 spec →
  `build` 生成候选 lock/sealed/legacy → 追加 `published` 与 `identities` 行 →
  `verify --all --check` 与 `verify --published --check` → 提交。`build` 不要求
  它正在构建的路径已有登记项，只把 registry 当防护（base 已发布路径被改仍是
  `published-package-modified`），并打印 publisher 写 `identities` 所需的
  `definition_digest`；它从不写 registry。「每个 head spec 选中的路径都必须有
  head 登记项」属于追加之后的 `verify --all --check`，因此首次发布是
  `build` 成功 → 追加 → 两项 `--check` → 提交，不是不动点。`build` 先在内存中
  算出并校验全部输出（lock/sealed/legacy、摘要、`read`、字节比较），再写同目录
  临时文件并重命名覆盖；确定性拒绝（退出 1）发生在第一个临时文件之前，不写任何文件。
  写阶段的 I/O/内部失败（退出 2）可能留下临时文件、缺失快照，或**来自不同
  构建的一对文件**：新 lock 配旧 sealed，或反过来。H2 不主张跨多文件原子事务，
  也不主张磁盘上永远不会出现该状态；它主张该状态**可检测且永远不是发布**：
  lock 与 sealed 都记录 `bundle_digest`/`definition_digest`，一新一旧必然让
  `verify --all --check` 失败，而退出 2 已经表示「未构建成功」。能被 `--check`
  接受的半写状态不存在，因为接受要求提交字节等于同一闭包的全新重建。若两者
  都是新字节而 legacy 缺失，`--check` 通过是正确结论（它只证明这两件发布产物），
  缓存按 H2-D12 已先删除、必须重新生成。`bundles/locks/`、`bundles/sealed/`、
  `bundles/legacy/` 是发布者控制的受信任输出路径，但 `--root` 下每个输出父目录
  段都必须走 §3 的不跟随检查，否则 `path-escape`（退出 1）；已提交 lock/sealed
  只按有界流式比较读取。三个时点必须分开：候选输出（`build` 退出 0）、registry 追加
  （publisher 用打印出的摘要写 `published`/`identities` 行，仍是候选首次发布）、
  发布（合并提交）。行只写在成功 build 之后、两项 `--check` 之前；
  `--all --check` 要求行已存在，所以「先 check 后写行」不可满足，失败的构建
  也不会留下登记项。Git 提供仓库级原子性，`build` 提供「退出 0 表示每个输出
  在写任何文件之前都已校验」。
- `verify --published --check` 是独立的历史审计：读取 `bundles/published.json`
  的每一项和每个 `identities` 行（包括已退役、无 spec 选中的版本），检查封闭
  形状、排序、`path` 与 `(package_id, version)` 及 `(namespace, version)` 唯一、
  目录与清单身份、重算摘要，以及仍在发布的定义名与当前构建摘要一致；失败是
  `published-registry-invalid`、`path-version-mismatch`、
  `definition-identity-conflict` 或 `published-registry-incomplete`，退出 1。它不
  选择任何包，也不改写 lock/sealed。`verify --all --check` 只读当前 spec 的精确
  闭包，两者都由 CI 运行（`ADR-0128` §8.4）。
- `bundles/legacy/<bundle_id>/definition.json`：构建器额外输出的纯定义文档，供
  现有 `fmp materialize <plan> --definitions <dir>` 读取。它不是 sealed
  bundle：`Registry::load_dir` 会递归读取目录下所有 `.json` 并调用
  `definition::read`，sealed 的 bundle 信封会被拒绝。这个快照是派生开发缓存，
  不是发布身份，也不进入任何摘要、缺失合法；若被提交，`--check` 要求它与
  已校验 sealed 内 `definition` 的 canonical 字节相同（不同是
  `legacy-snapshot-mismatch`，退出 1），下一次成功 `build` 重建它（H2-D12）。
- lock 与 sealed bundle 作为发布产物提交；CI 用 `verify --all --check` 重建并比较
  字节。它们不是手写计数，也不是普通扩展作者必须编辑的文件。
- `bundles/specs/` 采用本文的目录名，而不是设计草案的 `bundles/profiles/`：
  避免与 H4 的 fixup profile 混淆。这个改名写进 `ADR-0128`。

### H2-D10 错误与退出码

`fmp-definition` 是开发期工具，不是 `fmp` CLI 的替代品。它返回自己的
`BuildError` 枚举，不新增 `E-*` 错误码，也不伪装成 `fmp/0.1` 诊断：

| 类 | 例子 | 退出码 |
|---|---|---|
| 确定性拒绝 | 清单形状（必需/可选键）、身份/路径词法违规、`enabled_extensions`/`requires_capabilities` 逆序或重复、产物文件名不符、空 forms、路径越界或路径上出现链接/reparse point（含 `--root` 下的输出父目录）、打开的叶子不是普通文件（FIFO/socket/设备节点，或组件类型不符：需要文件处出现目录、需要目录处出现非目录）、版本目录与版本不符、已发布快照被改、发布登记被改/缺失/不符/重名版本、无 spec 的孤儿派生产物（`orphan-bundle-artifact`）、跨 spec 的 `bundle_id` 或定义身份冲突、声明与推导的 capability 不符、form 需求超出包声明（`form-extension-mismatch`）、复用保留的 legacy 定义名、依赖缺失/摘要错/环、同一 package ID 双版本、归属冲突、未知 capability、非空 reserved asset、闭包聚合上限、证据不完整/不符、用例缺失/未覆盖、用例格式不支持、用例与计划/form 绑定、基线或变异不符、用例 scope/stage 不符（form 负例用 `read`/`materialize`，或声明阶段不是第一个拒绝阶段）、form 诊断不在变异操作数上、完整诊断集不符、投影键集错误、legacy 目标不一致、已提交 legacy 快照与 sealed 内 `definition` 不一致（`legacy-snapshot-mismatch`）、无法映射的包路径、定义被 `read` 拒绝、资源上限（含已提交 lock/sealed 与已提交 legacy 快照超过字节预算） | 1 |
| 宿主/IO/内部 | 文件读失败、锁文件不可写、内部不变量破坏、conformance 遇到 `Internal`/`HostFailure` | 2 |
| 成功 | 构建或校验通过 | 0 |

`BuildError` 的变体名包括 `unsupported-capability`、`capability-mismatch`、
`unsupported-asset`、
`version-conflict`、`aggregate-limit`、`resource-limit`、`legacy-row-mismatch`、
`legacy-target-mismatch`、`legacy-snapshot-mismatch`、`evidence-mismatch`、
`evidence-incomplete`、
`missing-cases`、`uncovered-form`、`empty-package`、`case-evidence-mismatch`、
`case-plan-identity`、`case-form-mismatch`、`case-error-scope`、
`case-format-unsupported`、`case-baseline-invalid`、`case-mutation-mismatch`、
`case-diagnostics-mismatch`、`case-expect-shape`、`form-family-mismatch`、
`form-extension-mismatch`、`reserved-identity`、`path-version-mismatch`、
`path-escape`、`identifier-lexical`、`path-lexical`、`extension-lexical`、
`capability-lexical`、`bundle-file-mismatch`、
`published-package-modified`、`published-registry-modified`、
`published-registry-incomplete`、`published-registry-invalid`、
`bundle-id-conflict`、`definition-identity-conflict`、`unmapped-package-path`、
`dependency-unverified`、
`dependency-mismatch`、`not-a-regular-file`、`orphan-bundle-artifact`；它们
不是 `fmp/0.1` 诊断码。`case-materialize-fault` 是 conformance harness 对意外
`Internal`/`HostFailure` 的命名，退出码 2，绝不算通过。

`fmp` CLI 的 0/1/2 语义不变。H2 不把包构建错误送进 `bind` 的诊断数组。

### H2-D11 资源上限

H2 只加构建器自己的有界输入，不声称解决深层 JSON：

- 单个 manifest ≤ 1 MiB；
- 单个 form/type/profile 文件 ≤ 1 MiB；
- 单个 `tests/cases.json` ≤ 16 MiB；单个 `evidence/manifest.json` ≤ 1 MiB；
  单个 spec 或 lock ≤ 1 MiB；行比较读取的钉住 legacy 定义文件 ≤ 16 MiB；
  已提交 sealed bundle ≤ 80 MiB（64 MiB 闭包预算加至多 16 MiB 信封），
  `--check` 只按有界流式比较读取它，不 `read_to_end`；已提交的 legacy 桥快照
  也只按有界读取，≤ 16 MiB（等价门禁，不解析成第二份定义权威）；超预算的已
  提交 lock/sealed/legacy 快照是 `resource-limit`（退出 1）；
  `bundles/published.json` ≤ 16 MiB 且 ≤ 65 536 项；
- 每个包导出 forms ≤ 1024；每个包声明资产 ≤ 2048；每个包 cases ≤ 4096；
  每个包证据文件 ≤ 4096；
- 每个包的 manifest 加声明资产字节累计 ≤ 16 MiB，读取时累计检查（见下）；
- 每个包证据总字节 ≤ 16 MiB；
- 闭包内包数 ≤ 1024；闭包内实际读取的包根字节总数 ≤ 64 MiB（计数集合见下）；
- 闭包内声明资产总数 ≤ 65 536；闭包内 cases 总数 ≤ 65 536；闭包内证据文件
  总数 ≤ 65 536；
- 单条路径 ≤ 1024 字节；依赖深度 ≤ 64；
- manifest/form/type/profile/case/evidence/spec/lock/published registry 的 JSON
  嵌套深度 ≤ 64。

这些上限都假设输入是**普通文件**。FIFO、socket 或设备节点没有有界长度，`read`
还可能永不返回，大小检查无法约束它；路径层在应用任何预算之前按**已打开句柄**
的类型拒绝非普通叶子（`not-a-regular-file`，退出 1），也不以元数据大小代替类型
判定（第十八轮 P2-1，`ADR-0128` §3/§12）。

读取顺序是唯一的（第十九轮 P2-1）：词法校验→相对已打开目录句柄的 no-follow
打开→在已打开对象上确认普通文件→从**同一**句柄取大小提示→有界读取并按实际读出
字节累加→解析。元数据大小只用于尽早失败，绝不作为边界；边界是 §12.1 的累计
计数器，所以「类型检查后文件增长」不会绕过预算。

legacy 快照的 16 MiB 是**缓存读取上限，不是闭包上限**（第十九轮 P2-2）：闭包
64 MiB、sealed 80 MiB 都允许 canonical 定义超过 16 MiB。构建在内存中算出
canonical 字节后决定：≤ 16 MiB 才写 `bundles/legacy/<bundle_id>/definition.json`，
超过则省略并删除旧副本，仍退出 0；`verify --all --check` 对缺失本就合法，对
已提交且超过 16 MiB 的快照仍报 `resource-limit`（退出 1）。build 因此绝不写出
自己读不了的快照：构建成功意味着同一棵树的 `--all --check` 通过（`ADR-0128`
§8.3/§12）。

1024 forms 至少需要 2048 个用例（每个 form 一正一 form 负），4096 的上限给
plan 负例留出余量；16 MiB 的用例文件在最大规模下约合每例 4 KiB，足以容纳完整
的单 instruction `fmp/0.1` 文档和期望。原先的 1 MiB 连几百个 form 的强制用例
都装不下。

超限是确定性拒绝（退出码 1）。读取按上面的唯一顺序进行，因此一个未被 spec
选中的包也不能靠“没有闭包总字节”绕过 case/证据预算。
**单包资产预算是累计的，不能只看每文件元数据**：构建器用有界 reader 读取
manifest 和每个声明资产，按实际读出的字节累加，下一次读取会超过 16 MiB 时
立即拒绝；元数据只是提示，文件可能在类型检查与读取之间增长，所以边界是累计
计数器而不是声明的大小。读到剩余预算为止，短读或超读都是
`resource-limit`（退出码 1）。计数器按包重置，不是闭包总量。反例：2048 个
各 1 MiB 的文件通过每个单文件检查，却迫使单包读取 2 GiB。

**闭包预算是一个计数器、一个固定计数集合（第十二轮 P2-3）。** 任何打开选中包根
的命令为整次运行维护一个闭包计数器，累加它实际从包根读到的每个字节：
`package.json`、读取到的每个声明 form/type/profile 资产、`tests/cases.json`、
`evidence/manifest.json`，以及该清单列出且被读取的每个文件（`NOTICE`、
`README.md`、oracle 文本和用例证据）。spec、lock、`bundles/published.json`、
行比较用的钉住 legacy 定义和构建器自己的输出不进入这个计数器，它们另有单文件
上限（`ADR-0128` §12）。`build`、`verify --all` 和发布门禁会读到上述全集；读得
少的命令计数也少，但任何命令一次运行都不得读取超过 64 MiB 的包根字节。

同一路径在每个包根、每次运行只计一次，即使命令打开两次（例如一条 form 资产同时
被证据清单列出）；否则上限会取决于哪些字段提到了该路径。菱形依赖不重复计费：
spec 已把闭包每个成员恰好列一次，重复的 `packages[].path` 本身是 `path-lexical`
（H2-D4），没有第二次读取可计。拒绝发生在**会越界的那次读取**：reader 在剩余
预算处停止并返回 `aggregate-limit`（退出码 1），不消费越界字节；元数据仍然只是
提示。单包 16 MiB 资产预算和 16 MiB 证据总量预算独立生效，不能被闭包总量替代。

反例：3 个包各带 12 MiB 用例加 12 MiB 证据（每包 24 MiB，都在单包上限内），一次
运行读 72 MiB，超过名义 64 MiB；8 个这样的包读 192 MiB。因此负例必须是**多包
累计**超限，单包超限只测单包规则。

深度预算必须在解析**之前和解析过程中**生效：
构建器先对字节做迭代扫描（只数字符串外的 `{`/`[`），超过预算就在调用
`fmp_model::json::parse` 之前拒绝；后者是递归下降，先解析再测深度等于没有
防护。小于 1 MiB、但嵌套数万层的文档是必需反例，必须在不递归到栈上限的情况下
被拒绝。这个预算只保护构建器自己的输入，不声称 `fmp` 对深层 JSON 鲁棒；深层
文档造成的解析器栈溢出仍是 H4。H2 的包输入是开发者控制的输入，不把 `HE-T13`
算作完成。

### H2-D12 legacy 桥与不改的东西

- `fmp-validate`、`fmp-materialize` 的公开签名不改；`bind` 仍只接收
  `Plan` + `Arc<Definition>`。
- `Definition`、`Registry`、`check_form_id`、`load_dir` 不改；H2 的 bundle
  构建不经过 `Registry`。
- `fmp` CLI 不改；构建器在 canonical 定义不超过缓存读取上限时输出
  `bundles/legacy/<bundle_id>/definition.json`，现有 `--definitions <dir>` 可以
  读取它；sealed bundle 本身不是定义文档。
- **legacy 快照是派生开发缓存、不是发布身份，但提交时受等价门禁（第十四轮
  P1）。** 它不进入
  `source_package_digest`/`definition_digest`/`bundle_digest`/`release_digest`；
  缺失合法。若它被提交，`verify --all --check` 必须把它与已校验 sealed bundle
  内 `definition` 对象的 canonical 字节逐字节比较，不同即
  `legacy-snapshot-mismatch`（退出 1）。门禁是单向的：能让「兼容路径与发布对
  不是同一份定义」的树变红，绝不让缓存成为身份输入，也不在门禁里重建缓存。
  写阶段先删除旧的 `definition.json`，再依次替换 lock、sealed，最后写 legacy；
  所以「第三个文件写失败」（退出码 2）留下的是**缺失**（合法、`--check` 通过），
  而不是仍可被读成当前构建的旧文件；若留下旧文件，等价门禁会拒绝它。退出 2
  之后经 `--definitions` 读到的字节不能作为当前构建的证据，必须重新 `build`。
- **构建绝不写自己读不了的快照（第十九轮 P2-2）。** canonical 定义 ≤ 16 MiB
  才写；超过时省略快照并在同一写阶段删除旧副本，仍退出 0。省略只取决于字节，
  不取决于文件系统或上一次构建，所以同一闭包两次构建一致；`--all --check` 对
  缺失合法，对手工提交的超限快照仍是 `resource-limit`（退出 1）。因此合法闭包
  不会因为可选缓存而不可构建，也不会出现「build 成功、产物却过不了自己的
  `--check`」的组合（`ADR-0128` §8.3/§12）。
- `fmp-def/0.1` 行不在构建器里隐式转换成 `0.2`；混合格式闭包拒绝，显式
  版本化转换属于 H3。
- `definitions/` 一个字节不动；`check_definition.py` 继续只检查 legacy 定义和
  中心表，不扩展成包检查器。

## 4. 三个包

H2 每个 ISA 选一个代表性纵向切片，不迁移全部 forms：

| 目标 | 包 | 导出 forms | 对照正例 | 钉住的 legacy 源 | 覆盖点 |
|---|---|---|---|---|---|
| x86_64 | `packages/x86_64/monasm.x86.mov-register/0.1.0/` | `x86:mov/rm-r64/legacy`、`x86:mov/r64-rm/legacy` | `X86-P1` | `x86_64/0.1.0` | 两个方向、REX/legacy 放置、寄存器槽位 |
| aarch64 | `packages/aarch64/monasm.aarch64.add-immediate/0.1.0/` | `aarch64:add/x64-x64-x64-lsl0`、`aarch64:add/x64-imm12-lsl0`、`aarch64:add/x64-imm12-lsl12` | `A64-P1`、`A64-P2`（两个版本） | `aarch64/0.20.0` | 寄存器三元、imm12、`sh` 由 form ID 固定 |
| rv64 | `packages/rv64/monasm.riscv.integer-alu/0.1.0/` | `riscv:add/rd-rs1-rs2`、`riscv:addi/rd-rs1-imm12` | `RV-P1`、`RV-P2` | `rv64/0.1.0` | 三寄存器、imm12、整数域 |

选择规则：

- 每个导出 form 至少有一个既有正例；上表已核对 fixture 的 `form_id`。
- 每个导出 form 的行必须与**钉住的那一版** legacy 行 canonical JSON 逐字节相等；
  这一比较已经测量（§10）：rv64 的所选行在 `0.1.0` 与 `0.6.0` 之间相等；
  aarch64 的两个 `lsl0` 行在 `0.1.0`/`0.2.0`/`0.20.0` 之间相等，`lsl12` 行
  在 `0.1.0` 不存在、在 `0.2.0`/`0.20.0` 之间相等；**x86 的两个 `mov` 行在
  `0.1.0` 与 `0.78.0` 之间不相等** —— `0.78.0` 是 `fmp-def/0.2`，为每个
  寄存器槽位增加了 `bit_offset` 0/2 的 REX 放置和 `requires_extensions`。
  因此 x86 切片钉 `0.1.0` 并输出 `fmp-def/0.1`；若改成取 `0.78.0` 的行，
  就是定义语义漂移，而不是等价。
- x86 的 `X86-P1` 只使用寄存器 0 和 3（低寄存器），所以即使行不同，字节仍然
  相同；H2 不拿「字节相同」掩盖「行不同」，语义等价以钉住版本的逐行相等为准。
- rv64 钉 `0.1.0` 而不是 `0.6.0`：`0.6.0` 的 `target_identity.enabled_extensions`
  是 `["rv64i","rv64c"]`，而 `RV-P1`/`RV-P2` 计划声明 `["rv64i"]`；`fmp-def/0.1`
  的 `bind` 按集合相等比较，选 `0.6.0` 会直接以 `E-TARGET-001` 拒绝，与字节
  等价无关。aarch64 的 `0.20.0` 目标集合是 `[]`，与 `A64-P1`/`A64-P2` 一致，
  所选行也与 fixture 版本相等，所以可以钉最新。
- 包的 `enabled_extensions` 是**该包的保守扩展覆盖**（覆盖其所有行的需求），
  不是 bundle 的完整目标，也不是最小需求集合（H2-D4、第一轮 P1-3、第九轮
  P2-4）。三个 H2 包的格式都是 `fmp-def/0.1`，所以本轮额外
  要求该覆盖与 spec 选择完全相等（`h2-exact-target`）；这是过渡检查，不是未来
  组合规则。H3 解除它之前，不得声称不同扩展集合的包可以自由组合；解除后，
  新扩展族只新增自己的包和 spec 选择，不修改既有包清单。
- form 家族必须与包 `isa_family` 字符串相等（`family(form_id) ==
  target_identity.isa_family`，H2-D4、第二轮 P1-3）。这不是包格式里的三 ISA
  对应表；表单前缀与 target 不一致的包在 `read` 之前以
  `form-family-mismatch` 拒绝。
- 钉住的版本写在迁移包的 `legacy_source`（可选清单字段，存在时进入源摘要）；
  构建器只接受该版本的行，不提供「自动跟随最新」。新包没有 `legacy_source`
  时由包自述的 `target_identity`/`definition_format` 校验，不要求 legacy 目录
  里有对应文件。
- 三个包都不依赖另一个包；x86 与 aarch64/rv64 分别构建。
- 不选需要 fixup profile 的新语义；现有 fixup 仍由 legacy plan 表达。
- x86 切片因此**不覆盖** `fmp-def/0.2`；该路径仍由未改动的 legacy `0.78.0`
  定义和 H1 门禁覆盖。H2 的目标是包作者层，不是把全部定义迁到 0.2。

### 4.1 语义等价（定义不漂移）

对每个带 `legacy_source` 的迁移包、每个导出 form：

1. 在钉住的 legacy 定义版本里找到同名 `form_id`（x86 钉 `0.1.0`，
   aarch64 钉 `0.20.0`，rv64 钉 `0.1.0`，见各包 `package.json` 的
   `legacy_source`）；
2. 把包文件的 form 对象与 legacy 行分别转成 canonical JSON；
3. 断言两者逐字节相等；
4. 断言包导出的 form 集合恰好等于声明的集合，不多不少；
5. 断言包的 `definition_format` 与 legacy 文档相等，且 `target_identity` 满足
   `TargetEq`：除 `enabled_extensions` 外逐字段 canonical 相等，扩展按集合
   相等。目标由包自述，但迁移包必须证明自述没有改变来源语义；不一致
   是 `legacy-target-mismatch`（退出码 1），在合并文档交给 `read` 之前拒绝。

没有 `legacy_source` 的包跳过 1–3 和 5；`verify --package` 检查清单、路径、
导出、`fmp_model::definition::read` 和自述目标，机器输出由包自己的 case 证明。
它**不**执行用例的 `fmp_model::plan::read`、`fmp_model::validate::bind` 或
`fmp_model::materialize::materialize`；这些只在 `package_conformance` 里运行。
H2 至少用一个合成包
（沿用现有 ISA family，但 form ID 不在 legacy 目录中）验证这条路径，不把
「没有历史定义」当成「无法校验」。

钉住的版本是数据，不是「最新目录里的那份」。构建器发现包声明的行与钉住版本
不一致时必须拒绝，不能改用最新版本让测试变绿。两种路径分开：迁移包比钉住行，
新包比自己的用例和自述目标。

比较的是**行语义**，不是整份文档的摘要。包只含子集，合并后的 `forms` 还会
排序，所以 `definition_digest` 必然与 legacy 不同；不得为了「稳定」复用 legacy
摘要，也不得把不同的行顺序说成语义漂移。

### 4.2 字节等价（机器输出不漂移）

对每个对照正例：

1. 读取 legacy 计划；
2. 只把 `definition_identity` 替换为包 bundle 的 `{namespace, version, digest}`；
3. 用 `fmp_model::plan::read` 重新解析，`bind` 到 `VerifiedBundle::definition()`；
4. `materialize`；
5. 与 legacy 产物比较 §4.2.1 的精确、按 level 固定的投影。

**不比较** `fingerprint` 和 `materializer_version`：

- `fingerprint` 的输入是 `plan.legacy_document`，其中包含计划声明的
  `definition_identity`。换 bundle 身份必然改变它；这是 `ADR-0127` D12 已经
  记录的 legacy 行为，不是机器输出漂移。
- `materializer_version` 是构建收据，不是机器输出。

因此 H2 的等价投影是「机器输出」，不是 `payload/0.1`。`payload_digest` 包含
`fingerprint`，也不能作为这里的比较键。报告必须把这条写清楚，避免把
「payload 不同」误报成「字节不同」。

#### 4.2.1 精确投影（Level 0 / Level 1）

投影是封闭对象，harness 不补键、不删键、不把缺失键当空数组：

- **Level 0** 恰好 `format_version`、`level`、`bytes_hex`、`size`、`fixups`。
  `Artifact::level_zero_json()` 还输出 `fingerprint`/`materializer_version`，
  投影丢弃它们；它不输出 `symbols`，所以 Level 0 case 写 `symbols` 是
  `case-expect-shape`。
- **Level 1** 恰好 `format_version`、`level`、`sections`、`fixups`，并且当且
  仅当计划的 `output_contract.include_symbol_table` 为真时包含 `symbols`。
  `sections` 保留 materializer 输出的每个 section 对象（含可选
  `base_address` 和 `bytes_hex`）。`symbols: []`（真但空）与缺键（false）是
  两个不同的 JSON 值。
- 两个投影都不包含 `fingerprint` 或 `materializer_version`；case 的 `expect`
  与等价测试使用同一投影。

反向测试：同一派生计划把 digest 改回错误值，`bind` 必须在
`/definition_identity/digest` 返回 `E-DEF-001`；包路径不能绕过 H1 的身份检查。
这条反例**不是** `monasm-cases/0.1` 的一条 plan 负例：用例文法要求
`definition_identity` 恰为 `$standalone` 三字段哨兵（否则 `case-plan-identity`），
harness 只会把它替换成正确身份，无法制造 digest 错配，也**不提供** per-case
身份覆盖机制。定义身份负例由这个独立绑定测试承担。

### 4.3 独立测试（两个包可以分别验证）

- x86 包和 rv64 包各自在临时目录构建，不读取对方的包。
- 包根 `tests/cases.json` 是唯一用例发现点（`monasm-cases/0.1`），没有中央
  测试列表。`0.1` 只承诺单指令、有操作数的 `fmp/0.1` 用例；`fmp/0.2`、
  零操作数 form 和多指令 fixup 必须用后续 case 格式，不能静默复用 `0.1`
  （`ADR-0128` §9.2）。每个用例声明 `case_id`、`form_id`、`instruction_id`、
  `kind`（`positive`/`negative`）、完整 `fmp/0.1` 计划文档、期望结果和
  `evidence`。计划的 `definition_identity` 是 `$standalone` 哨兵；harness
  执行前替换成 §2.4 的独立身份，再走 `plan::read`。计划只能有一条 instruction，
  且其 `instruction_id`/`form_id` 必须与 case 一致（`case-form-mismatch`），
  否则“覆盖 B 却执行 A”会被当成通过。正例 `expect` 使用 §4.2.1 的精确投影，
  键集错误是 `case-expect-shape`。
- 负例必须声明 `scope`。`scope:"plan"` 可针对错误的 `expected_digest`、布局、
  目标或不可表示的值，但不计覆盖；定义身份错配**不是** plan 负例：判例计划必须
  写 `$standalone` 哨兵，harness 只会替换成正确身份，错误 digest 在
  `case-plan-identity` 处就被拒绝，也不存在 per-case 身份覆盖。它用
  `expect_error.stage` 区分
  `read`/`bind`/`materialize`，且声明的阶段必须恰是第一个拒绝的阶段（更早
  阶段已拒绝、或该阶段放行，都是 `case-error-scope`）。`scope:"form"` 必须
  绑定同 form/instruction 的正例 `baseline_case_id`，只改一个 `mutates` 操作数
  指针，且基线/用例 canonical 差分必须恰好等于该指针
  （`case-baseline-invalid`/`case-mutation-mismatch`）。这些是 `verify --package`
  的静态检查；声明的 stage 与完整诊断集由 `package_conformance` 执行证明。
  form 负例必须由
  `bind` 拒绝，`expect_error.stage` 必须是 `bind`，`read`/`materialize` 都是
  `case-error-scope`；至少一条 `(code, path)` 必须在 `mutates` 或其父操作数
  对象上，不能只指向 `expected_digest`/`expected_size`，且不得声明
  `E-BYTE-001`/`E-SIZE-001`。`expect_error.diagnostics` 必须与观察到的完整
  `(code, path)` 集合相等（`case-diagnostics-mismatch`）；`read` 阶段的观察集
  是 `plan::read` 返回的单个 `Diagnostic`，plan 负例的 `materialize` 中
  `Internal`/`HostFailure` 是 `case-materialize-fault`。
- 每个导出 form 至少一个正例和一个 `scope:"form"` 的非法邻域（立即数越界、
  错误寄存器宽度、错误 target type、非法 modifier 等，必须由 `bind` 拒绝）。
  没有用例文件是 `missing-cases`，没有 form 邻域负例是 `uncovered-form`。
- **代表性 form 带边界证据，但边界只取计划可表示的值（第十、十一轮 P2-2）。**
  一个正例加一个非法邻域只证明该 form 存在，不证明操作数取值域。域分两层：
  `D_Representable` 是 `plan::read` 能构造的值（`payload.reg` 是 `u64`，
  `payload.value` 是 `i128`，modifier 值是整数/字符串/布尔），`D_form` 是槽位
  接受的值，且 `D_form ⊆ D_Representable`。只有落在
  `D_Representable \ D_form` 的值才能做 `scope:"form"` 负例；超出表示域的值
  （例如 `{"reg": -1}`）是 `scope:"plan"` + `stage:"read"` 的 `plan::read`
  拒绝（`E-PLAN-002` 在 `payload/reg`），不能算 form 覆盖。
  对 H2a/H2b 实际交付的有界操作数，边界必须取自**最终合法域**，而不是原始
  编码区间。对有区间 `[L, U]`、对齐 `a`（`align_bits`）和排除集 `E` 的槽位：
  `D_form = {x ∈ D_Representable, L≤x≤U, x≡0 (mod 2^a)} \ E`。寄存器再取
  `L=0`、`U` 为 `2^w−1` 与 `u64::MAX` 的较小者、`a=0`。
  - 正例是 `D_form` 的最小值、最大值和一个有代表性的内部值。原始端点若被排除
    或不对齐就不是正例：`x86:mov/rm8h-r8h/legacy`（`w=3`，`E={0,1,2,3}`）的
    正例是 `4`/`7`；`aarch64:add/w32-w32-w32-imm6-lsl`（`E=32..63`）的正例上界
    是 `31`；`riscv:c.addi/rd-imm6`（`E={0}`）的正例下界是 `1`。
  - excluded 中可表示但非法的值是 `scope:"form"` 负例（`E-RANGE-004`）。
  - 相邻越界值（`min−1`/`max+1`，或寄存器的 `2^w`）只有在
    `D_Representable` 能表示时才能作 `stage:"bind"` 的 form 负例；不能表示的值
    只能作 `stage:"read"` 的 plan 负例，不能声明成读取器会先拒绝的 bind 负例。
  - 寄存器字段：编码宽度 `w` 是 placement 宽度之和，可超过 64 位（`ADR-0127`
    §7.1 只限制每个 placement，不限制总和；H1 的
    `prototype/crates/fmp-materialize/tests/he1_wide_register.rs` 已对
    64/127/128/192 位调用 `bind` 与 `materialize`）。`payload.reg` 仍是 `u64`，
    所以 `D_reg = ([0, 2^w−1] ∩ [0, 2^64−1]) \ E`：
    - `w < 64`：正例是 `D_reg` 的最小与最大成员（通常 `0`/`2^w−1`）；可表示的
      `2^w` 作 form 负例；
    - `w = 64`：正例是 `D_reg` 的最小与最大成员；`2^64` 不可表示，form 负例用
      可表示的排除值或错误 `target_type`/操作数类型；
    - `w > 64`：正例是 `D_reg` 的最小与最大成员（通常 `0`/`u64::MAX`）；
      `2^w−1` 与 `2^w` 都不可表示，因此不要求、也不允许声明 `max+1`；form 负例
      用排除值或错误 `target_type`/操作数类型。没有排除值的宽槽位没有数值 form
      负例，不得发明一个。
    `0−1` 不可表示，只能做 `scope:"plan"` 的 `stage:"read"` 负例。另需一个
    包级边界协议测试让 127/192 位槽位走完 `read`/`bind`/`materialize`，确保 H2
    作者层不会把 H1 已验证的编码能力缩回 64 位；它补充而不是替代三个实际包的
    窄字段边界用例。
  - modifier 是允许的 `(name, value)` 集合，不是连续整数区间：测一个允许对和
    一个可表示但不允许的对，不套 `min−1`/`max+1`。
  证据文件记录诊断**实际携带**的字段：立即数越界由 `E-RANGE-001`（target 操作数
  为 `E-RANGE-002`）拒绝，带 `min`/`max`/`value`（非 target 还有 `target_type`）；
  寄存器越界由 `E-OPERAND-004` 拒绝，带 `target_type`/`value`/`field_bits`，
  上界由 `field_bits` 推导（`w ≥ 64` 时可表示上界是 `u64::MAX`）；排除值由
  `E-RANGE-004` 拒绝，带
  `target_type`/`value`/`excluded`。不要求诊断不产生的字段（寄存器诊断没有
  `min`/`max`）。通过条件仍是 `(code, path)` 集合，`monasm-cases/0.1` 不变。
  缺少边界用例使该切片验收失败，但不新增覆盖错误码。这是 H2 实际切片的证据，
  不是「整个 ISA 边界已被证明」。
- 每个用例的 `evidence` 必须是 `oracle` 或 `manual-derivation`。没有证据清单
  的开发包直接核对 case 自带的 `sha256` 与原始文件字节；清单存在时以清单为准；
  可发布包还要求 `files` 列出 `tests/cases.json` 本身、`NOTICE`、每个用例证据、
  至少一条 `sources`、完整的 `oracle.status` 和 skip 理由（H2-D2、
  `--release-evidence`/`--release`）。
  哈希覆盖原始字节，CRLF/LF 或空白改变也是改变。
- 在**未发布候选包**上修改 `tests/cases.json` 但不更新 evidence manifest：
  `evidence-mismatch`；更新 manifest 后：`evidence_digest`/`release_digest` 改变，
  `source_package_digest`/`definition_digest` 不变。发布后同一改动是
  `published-package-modified`，必须新建版本。这是第二轮 P1-1 和第五轮 P2-3
  的验收测试。
- 复制一个未发布包到不同目录、改变工作目录，在没有 spec 的情况下运行
  `verify --package`：独立身份（`monasm-standalone/0.1`）、诊断和独立
  `definition_digest` 必须相同。这是第一轮 P1-1 的验收测试。
- 构造一个未进入任何 spec 的包，把合法 form 的 opcode 改错但保持 JSON 结构
  合法：`fmp_model::definition::read` 仍通过；`verify --package` 必须通过用例
  覆盖/证据检查暴露它，普通 PR 的 `package_conformance` 必须让正例的字节比较
  失败。这是第一轮 P1-2 的验收测试，也是「read 不是机器码权威」的证明。
- 包级 harness 只按清单/用例数据分派，不按 ISA 名称写执行分支；`HE-T14` 的
  「同一 harness」在 H2 只证明 harness 没有 ISA 分支，不证明三个真实工作流。
- 构建器不执行 oracle；它验证证据的存在、可追溯和哈希。报告必须说明这一点，
  不能把「记录在案」写成「本机重算」。

H2 报告必须把这些状态分开写，不能合并成「已验证」：

| 状态 | 含义 | 不表示 |
|---|---|---|
| 定义结构已验证 | `definition::read` 通过 | opcode/操作数范围正确 |
| 包结构已验证 | `verify --package` 通过清单、资产与证据检查 | 声明的依赖已经解析，或任用例已执行 |
| 用例文档静态有效 | `verify --package` 通过用例 schema、scope/stage 声明形状、`mutates` 语法、诊断数组形状与静态 `case-error-scope` 规则 | `read`/`bind`/`materialize` 确实在声明阶段拒绝 |
| 用例阶段与诊断已验证 | `package_conformance` 执行后确认声明阶段是第一个拒绝阶段，且完整 `(code, path)` 集合相等 | 独立 oracle 已运行 |
| 依赖闭包已验证 | 每个依赖都按 ID、版本和摘要匹配显式闭包 | H2 的包有依赖 |
| 包级机器码测试通过 | `package_conformance` 与声明期望和完整诊断集一致 | 独立 oracle 已运行 |
| 包目标覆盖关系已验证 | `⋃E_form ⊆ E_package ⊆ E_bundle`；`fmp-def/0.1` 下 `E_form = ∅`，实际只证明 `E_package ⊆ E_bundle` | 真实 ISA 扩展需求已被完整证明 |
| 证据文件可追溯 | 文件存在且摘要一致 | 记录的 oracle 结果真实 |
| 独立 oracle 已复验 | 本机实际重跑外部工具并核对 | H2 对新包做到这一项 |

除「独立 oracle 已复验」外，其余各行互不推出；尤其「用例文档静态有效」不推出
「用例阶段与诊断已验证」，因为前者不执行计划。H2 只做声明范围内的检查与执行；
报告不得写成「本机重算」。
「包目标覆盖关系已验证」这一行必须单列：三个 H2 包都是 `fmp-def/0.1`，
`E_form = ∅` 使第一项包含检查空真，`legacy_source` 只保证 target 与被复制行
一致，不从行体推导扩展需求；没有 `legacy_source` 的新包只由作者声明和用例/
证据支撑。报告不得据此写成「真实 ISA 扩展需求已完整证明」，也不得为此新增
ISA 专用推导器（H2-D4、`ADR-0128` §4.1）。

H2 不提交第二个 x86 真实包；`HE-T16` 的 H2 部分用同一合法 spec 的不同创建/
读取/集合迭代顺序证明确定性，逆序 spec 是拒绝输入，不是第二种合法写法。真正的
A/B 工作流合并留给 H5。

## 5. 测试计划

### 5.1 构建器

| 测试（拟名） | 断言 | 对应 |
|---|---|---|
| `the_same_inputs_build_to_the_same_bundle_digest` | 两次构建、两个临时目录、不同创建顺序 → 同一 `bundle_digest` 和同一 sealed 字节 | `HE-T05` |
| `a_file_change_between_digest_and_merge_is_not_observed` | 故障注入：包读取/摘要计算后、合并前替换一个 form 文件 → 构建使用加载时的同一份字节（摘要与合并一致），或在加载阶段失败；不允许摘要来自 A、合并来自 B。重放生成的 bundle 得到同一 `definition_digest` | 第九轮 P2-2、`ADR-0128` §9、`H2-D9` |
| `an_unsorted_spec_is_rejected` | spec 的 `packages` 逆序或非严格排序 → 确定性拒绝，不静默重排 | `HE-T16`、`ADR-0128` §8.2 |
| `package_discovery_order_does_not_change_the_bundle` | 同一合法 spec，改变临时目录创建顺序、文件读取顺序和内部集合迭代顺序 → 同一 `bundle_digest` 和同一 sealed 字节 | `HE-T05`、`HE-T16`（H2 部分） |
| `an_unselected_package_does_not_change_an_old_bundle` | 包根新增一个未列出的包（即使其清单损坏）→ 旧 spec 的 lock/bundle 不变；构建器从未打开它 | `HE-AC-05`（构建期部分） |
| `a_dependency_outside_the_spec_is_refused` | 依赖指向列表外的 `(package_id, version)` → 确定性拒绝，不扫描目录补齐 | `H2-D5`、`HE-T08` |
| `the_spec_lists_every_package_in_the_closure` | 删掉一个被依赖的列表项 → 拒绝；合法 spec 的顺序由另一个测试证明逆序是拒绝 | `H2-D5` |
| `a_dependency_must_match_its_exact_digest` | 改依赖内容保留版本 → 摘要不匹配，退出 1 | `HE-T08` |
| `a_dependency_cycle_is_refused` | A→B→A → 确定性拒绝，不递归溢出 | `HE-T08` |
| `the_same_dependency_reached_twice_is_loaded_once` | 菱形闭包 → 共享包在 spec 中只列一次，两条依赖边都校验通过，归属表无重复 | `HE-AC-04` |
| `two_packages_exporting_the_same_form_conflict` | 两包同一 `form_id`，内容相同也失败 | `HE-T07`、`HE-AC-09` |
| `a_package_path_cannot_escape_its_root` | `../`、绝对路径、从 `--root` 到文件的任一段是符号链接/reparse point → 拒绝（`path-escape`）；检查到实际读取之间替换目标也不跟随，不能只靠 `canonicalize()` | `H2-D3`、第六轮 P2-2 |
| `identifier_and_path_lexical_rules_are_platform_independent` | `package_id`/`bundle_id` 含大写、空段、尾点 → `identifier-lexical`；form 路径 `forms/Add.json` 与 `forms/add.json` 并存、`forms/NUL.json`、尾点/空格、`..` 段 → `path-lexical`；在 Linux/macOS/Windows 上都是同一格式拒绝（退出 1），不是某平台 I/O 失败或成功打开 | 第九轮 P2-1、`ADR-0128` §1.3、`H2-D1` |
| `the_same_relative_path_in_two_packages_is_legal` | 闭包同时选中 `packages/x86_64/monasm.x86.alu/0.1.0` 与 `packages/x86_64/monasm.x86.vector/0.1.0`，两包各带 `forms/add.json` 与 `tests/cases.json` → 构建通过；每个包按自己的根读取该文件，摘要覆盖各自字节。只比较裸相对字符串的实现会错误拒绝这个合法组合 | 第十轮 P1-1、`ADR-0128` §1.3、`H2-D1` |
| `a_cross_package_path_alias_is_rejected` | spec 分别选中 `packages/x86_64/monasm.x86.alu/0.1.0` 和 `packages/x86_64/MONASM.X86.ALU/0.1.0`，两个根折叠成同一仓库路径；或同一 `packages[].path` 被列两次 → `path-lexical`（退出 1），不是两个恰好大小写不同的目录 | 第十轮 P1-1、`ADR-0128` §1.3、`H2-D1` |
| `a_package_path_keeps_the_full_package_id` | 两个包 `monasm.x86.crypto` 与 `vendor.x86.crypto`，同 target `x86_64`、同 version `0.1.0`，分别位于 `packages/x86_64/monasm.x86.crypto/0.1.0/` 与 `packages/x86_64/vendor.x86.crypto/0.1.0/` → 两者各自 `build`/`verify --package --release` 通过，闭包可同时选中；若按最后点分段建目录，两者都要求 `packages/x86_64/crypto/0.1.0/`，无法共存。把目录段写成 `crypto` 或任一前缀不匹配完整 `package_id` → `path-lexical`（退出 1） | 第十七轮 P1-1、`ADR-0128` §1.3、`H2-D1` |
| `a_case_different_on_disk_name_is_rejected` | 声明小写合法的 `forms/add.json`，磁盘只有 `forms/Add.json`；以及磁盘目录是 `Forms/` 而声明 `forms/` → Linux/macOS/Windows 上都是 `path-lexical`（退出 1），不是 ext4 的缺文件（退出 2）或大小写不敏感卷的成功打开（退出 0）。精确名字查找在已打开父句柄上完成，与声明 `forms/Add.json` 的词法拒绝测试不同 | 第十轮 P1-2、`ADR-0128` §1.3/§3、`H2-D1`/`H2-D3` |
| `the_manifest_is_closed` | 未知键、必需键缺失、重复键 → 拒绝；可选键缺失 → 接受 | `INV-07` |
| `an_empty_forms_list_is_refused` | `exports.forms: []` → `empty-package`，在合并文档交给 `read` 前拒绝；类型/profile-only 包不走 H2 | `ADR-0128` §1、第四轮 P2-3 |
| `an_unknown_case_format_is_refused` | `cases_format: "monasm-cases/0.2"` 或其他值 → `case-format-unsupported`；`0.1` 只接受单指令、有操作数的 `fmp/0.1` 计划 | `ADR-0128` §9.2、第四轮 P2-1 |
| `an_unknown_capability_is_refused` | `requires_capabilities` 出现白名单外字符串 → `unsupported-capability`，退出 1 | `H2-D2`、`HE-T09`（H2 构建期部分） |
| `a_capability_must_be_declared_if_a_row_uses_it` | 声明 `[]` 但 form 有带 `placements` 的 slot → `capability-mismatch`；补上 `field-placement/v1` 后通过。由于 `read` 要求每个 form 的 `slots` 非空且每个 slot 的 `placements` 非空，任何含 form 的 `fmp-def/0.1` 包声明 `[]` 都必然失败 | `H2-D2`、`ADR-0128` §1.2、第七轮 P2-4、第八轮 P2-1 |
| `a_declared_capability_must_be_used_by_a_row` | 声明 `integer-domain/v1` 但所有 slot 都是寄存器、无 `range` → `capability-mismatch`；包含一条 `from: "operand_value"` 的 slot 后通过。测试不构造无 slot 的 form：`{"form_id":"x86:example/form","template":"90"}` 不是合法 Definition，`read` 先以 `E-DEF-001` 拒绝 | `H2-D2`、`ADR-0128` §1.2/§7.0、第七轮 P2-4、第八轮 P2-1 |
| `a_duplicated_capability_is_rejected` | `requires_capabilities` 写 `["field-placement/v1","field-placement/v1"]` → `capability-lexical`（退出 1），派生集合相同也不能放行；`["field-placement/v1"]` 通过。重复不进入任何摘要 | 第十二轮 P2-2、`ADR-0128` §1/§1.2、`H2-D7` |
| `a_reversed_extension_array_is_rejected` | 包 `enabled_extensions` 写 `["rv64i","rv64c"]`（同一集合的逆序写法）→ `extension-lexical`（退出 1）；spec/lock/sealed 的 `target.identity.enabled_extensions` 逆序同样拒绝。排序写法 `["rv64c","rv64i"]` 通过，且 `source_package_digest` 与逆序写法不同，证明这是两个身份而不是被静默规范化的一份 | 第十二轮 P2-2、`ADR-0128` §1/§6/§8.2、`H2-D7` |
| `a_non_empty_reserved_asset_is_refused` | `exports.types`/`profiles` 非空 → `unsupported-asset`，不静默忽略 | `H2-D2`、`H2-D6` |
| `a_non_empty_reserved_asset_is_refused_forever_under_0_1` | 同一份未改动的 `monasm-package/0.1` 清单（非空 `types` 或 `profiles`）：H2 构建器和任何后续版本的构建器都报 `unsupported-asset`（退出 1）；只有声明新 `package_format`（如 `monasm-package/0.2`）的清单才可能被接受，且该版本尚不存在。断言“构建器认识该字段”本身不改变 `0.1` 的结论 | 第十九轮 P1-2、`ADR-0128` §5、`H2-D2` |
| `two_versions_of_one_package_id_conflict` | 同一 `package_id` 两个版本、导出不相交 → `version-conflict` | `H2-D5` |
| `a_package_without_legacy_source_is_verified_from_its_own_target` | 合成包无 `legacy_source` → 按自述目标、`read` 和用例通过，不需要 spec | `H2-D2`、`H2-D4`、§4.1 |
| `a_file_form_id_must_match_its_export` | 交换两个 form 文件 → 归属不匹配，拒绝 | `H2-D2` |
| `the_target_profile_must_match_the_spec` | 包的 `target_profile` 与 spec 不一致 → 拒绝 | `H2-D4` |
| `the_standalone_identity_is_derived_from_the_package` | 复制包到不同目录、换 cwd、无 spec → 同一 `monasm.standalone.*`/`standalone+*` 和同一独立 `definition_digest` | `H2-D5`、§2.4、第一轮 P1-1 |
| `a_standalone_identity_cannot_be_written_into_a_spec` | spec 的 `namespace`/`version` 使用保留前缀 → `reserved-identity`，退出 1 | `H2-D5`、§2.4 |
| `a_frozen_legacy_definition_name_cannot_be_reused` | spec 用 `monasm.isa.x86`/`0.1.0` 只导出两条 mov 行 → 即使当前 spec 集合无冲突、登记表无行，仍是 `reserved-identity`；改用 H2 自己的 `0.1.0-h2` → 通过。`identities` 登记 `monasm.isa.riscv`/`0.1.0` → 同样 `reserved-identity`。保留集合读自 `<root>/definitions/*/*.json` 的 `namespace`/`version`，不进入任何摘要 | 第八轮 P1-2、`ADR-0128` §8 |
| `a_form_family_must_match_the_package_target` | `isa_family: aarch64` 的包导出 `x86:*` → `form-family-mismatch`，在 `read` 之前拒绝 | `H2-D4`、第二轮 P1-3 |
| `the_family_rule_is_equality_not_a_package_whitelist` | 合成包声明 `isa_family: loongarch` 并导出 `loongarch:*` → 通过包层家族检查，随后只被现有 `definition::read` 的家族集合拒绝；错误来自 reader，不是包格式白名单 | `H2-D4`、第二轮 P1-3 |
| `a_package_cover_is_a_subset_of_the_bundle_target` | `fmp-def/0.2` 合成包声明 `["rv64i"]`、spec 选择 `["rv64c","rv64i"]` → 接受；缺少 `rv64i` → 拒绝 | `H2-D4`、第一轮 P1-3、第九轮 P2-4 |
| `a_form_requirement_must_be_inside_its_own_package` | `fmp-def/0.2` 包声明 `["rv64i"]`、一条 form 的 `requires_extensions` 是 `["rv64c"]`，spec 选中 `["rv64c","rv64i"]` → `form-extension-mismatch`（退出 1），在包 ⊆ bundle 检查之前；把包声明改成 `["rv64c","rv64i"]` 后通过，且合并文档与包自己的 `read` 结论一致。`fmp-def/0.1` 下同一错误无法表达（`E_form = ∅`） | 第八轮 P1-3、`ADR-0128` §4.1 |
| `an_over_declared_extension_cover_is_legal_but_narrower` | 所有行只需 `rv64i`、包声明 `["rv64c","rv64i"]`、spec 选 `["rv64c","rv64i"]` → 通过，且 `source_package_digest` 保留作者声明；只选 `rv64i` 的 spec → 包 ⊆ bundle 失败；构建器不把声明裁剪成并集，也不因高报报错 | 第九轮 P2-4、`ADR-0128` §4.1、`H2-D4` |
| `fmp_def_0_1_keeps_the_transitional_exact_target` | `fmp-def/0.1` 包的声明覆盖与 spec 选择不等（即使是子集）→ `h2-exact-target`，退出 1 | `H2-D4`、第一轮 P1-3 |
| `a_profile_id_is_not_a_global_target_identity` | 两个 spec 使用同一 `target.profile_id`、但 `target.identity.enabled_extensions` 不同 → 各自构建通过，`definition_digest`/`bundle_digest` 不同；身份查取六键 `target.identity`，不按 profile 名建索引。该用例不要求构建器拒绝同名，H2 不加 `(profile_id, identity)` 跨 spec 唯一性 | 第十三轮 P2-3、`ADR-0128` §4.1、`H2-D4` |
| `the_case_file_is_required_and_covers_every_form` | 无 `tests/cases.json` → `missing-cases`；form 无正例或无 `scope:"form"` 负例 → `uncovered-form` | `H2-D2`、§4.3、第二轮 P1-2 |
| `a_case_must_bind_its_declared_form_to_the_plan` | case 声明 form B，计划只含 form A、空计划或多于一条 instruction、`instruction_id` 不一致 → `case-form-mismatch`，不进入执行 | `H2-D2`、`ADR-0128` §9.1、第二轮 P1-2 |
| `a_case_negative_must_target_the_declared_instruction` | 负例 `path` 是根级或 `/sections/...`（例如错误 `format_version`）→ `case-error-scope`；`scope:"form"` 的 `mutates` 指向 `expected_digest`、多改一个字段或没有实际改动 → `case-mutation-mismatch`；两者都不计为该 form 的覆盖 | `H2-D2`、`ADR-0128` §9.1、第三轮 P1-3 |
| `a_form_negative_must_be_a_bind_rejection_on_the_mutated_operand` | form 负例用 `stage:"read"` 或 `"materialize"`，或只返回 `/expected_digest` 的 `E-BYTE-001`、只返回 `/expected_size` 的 `E-SIZE-001`，或诊断不在 `mutates` 及其父操作数对象上 → `case-error-scope`，不计覆盖；合法寄存器 0→1 但保留旧 `expected_digest` 的反例必须被拒绝为 form 证据 | `ADR-0128` §9.1、第五轮 P1-1、第十三轮 P1 |
| `a_read_stage_rejection_is_a_plan_negative` | `{"payload":{"reg":-1}}` 在 `plan::read` 就以 `E-PLAN-002`（`/instructions/0/operands/<n>/payload/reg`）拒绝，只能写成 `scope:"plan"` + `stage:"read"`，观察集是读取器返回的单个 `Diagnostic`；把同一计划标成 `scope:"form"` 或 `stage:"bind"` 都是 `case-error-scope`，不计覆盖。合法的 0 与可表示上界（`w < 64` 时为 `2^w−1`，`w ≥ 64` 时为 `u64::MAX`）仍是 form 正例，只有 `w < 64` 时 `2^w` 才是 form 负例 | 第十一轮 P1-1、第十三轮 P1、第十五轮 P2-2、`ADR-0128` §9.1、`H2-D2` |
| `a_declared_stage_must_be_the_first_rejecting_stage` | 同一读取器拒绝的计划声明 `stage:"bind"` 或 `"materialize"`，以及一个 `bind` 可接受的计划声明 `stage:"read"` 或 `"materialize"` → 由 `package_conformance` 执行后全部判为 `case-error-scope`（退出 1），不产生证据；只有实际第一个拒绝的阶段被接受。`verify --package` 只检查声明形状，不会替代这条判定 | 第十三轮 P1、第十五轮 P2-1、`ADR-0128` §9.1、`H2-D2` |
| `a_modifier_value_change_is_a_single_form_mutation` | 合成 fixture（H2 三个包没有 modifier，现有定义行的 `modifiers` 全为空）：0.2 定义 fixture 允许 `(shift,0)`，基线正例写 `{"name":"shift","value":0}`，用例只把 `value` 改成不允许的 1 → 差分指针恰为 `/instructions/0/operands/<n>/modifiers/0/value`，`case-mutation-mismatch` 检查必须接受它是单次 form 变异；`bind` 在 `…/modifiers` 返回 `E-OPERAND-003`（`mutates` 的祖先），符合位置规则。只允许 `…/modifiers/<i>` 的实现会错误拒绝这条用例；它不是三个包的覆盖计数 | 第十一轮 P2-1、`ADR-0128` §9.1 |
| `a_case_evidence_must_be_listed_and_hashed` | 有证据清单时，用例证据未列入或哈希不符 → `case-evidence-mismatch`，退出 1 | `H2-D2`、第二轮 P1-2 |
| `a_development_package_verifies_without_an_evidence_manifest` | 有 forms/cases、无 `evidence/manifest.json` → 开发 `verify --package` 通过、不产生 `evidence_digest`；同一包 `--release` → `evidence-incomplete`；清单存在但漏列 case 证据 → `case-evidence-mismatch` | `ADR-0128` §7.1、第四轮 P1-2 |
| `an_evidence_hash_covers_raw_file_bytes` | 把 `NOTICE`/case 证据从 LF 改成 CRLF 或改缩进、不更新清单 → `evidence-mismatch`；同步更新清单 → `release_digest` 变化 | `ADR-0128` §7.0/§7.1、第四轮 P2-4 |
| `the_case_file_is_part_of_the_release_digest` | 在未发布候选包上改 `tests/cases.json` 不更新清单 → `evidence-mismatch`；更新清单 → `evidence_digest`/`release_digest` 变，`definition_digest` 不变；已发布包改同一文件 → `published-package-modified` | `H2-D8`、§7.1、第二轮 P1-1、第五轮 P2-3 |
| `the_release_mode_requires_complete_evidence` | 缺 `tests/cases.json` 条目、`NOTICE`、`sources`、`oracle.status` 或 skip 理由 → `evidence-incomplete`，退出 1 | `H2-D2`、`ADR-0128` §7.1、第二轮 P2-1 |
| `release_evidence_is_a_separate_gate` | 非空依赖包有完整证据但无闭包：`--release-evidence` 退出 0，`--release` 退出 1（`dependency-unverified`）；证据缺项时 `--release-evidence` 也退出 1（`evidence-incomplete`） | `ADR-0128` §7.1/§8、第五轮 P2-4 |
| `a_deep_json_document_is_refused_before_recursion` | ≤1 MiB、数万层嵌套 → 深度扫描在 `json::parse` 前拒绝，不栈溢出 | `H2-D11`、第一轮 P2 |
| `case_and_evidence_inputs_have_their_own_budget` | `tests/cases.json` 超过 16 MiB、证据清单/spec/lock 超过 1 MiB、forms 超过 1024、assets 超过 2048、cases/证据文件超过 4096、证据总量超过 16 MiB、单包资产累计超过 16 MiB、闭包 cases/证据文件总数超限；未选中包也受限 | `H2-D11`、第三轮 P2-1/P2-2 |
| `the_asset_budget_is_counted_while_reading` | 2048 个各 1 MiB 的文件或读时增长的文件 → 累计 reader 在 16 MiB 处拒绝，不只信 `stat` | `H2-D11`、`ADR-0128` §12.1、第三轮 P2-1 |
| `the_closure_budget_counts_case_and_evidence_bytes` | 3 个包各带 12 MiB `tests/cases.json` 加 12 MiB 证据文件（每包 24 MiB，都在单包 16 MiB 资产/证据上限内），闭包累计 72 MiB 越过 64 MiB → 在越界那次读取处 `aggregate-limit`（退出 1），不读剩余文件；去掉一个包后通过。菱形依赖里共享包只计一次，不因两条依赖边重复计费。只有单包超限的反例不算覆盖本规则 | 第十二轮 P2-3、`ADR-0128` §12/§12.2、`H2-D11` |
| `a_committed_sealed_bundle_over_its_budget_is_rejected` | 已提交 sealed bundle 超过 80 MiB（lock 超过 1 MiB）→ `--check` 的有界流式比较在预算处停止并报 `resource-limit`（退出 1），不把整个文件 `read_to_end`，也不改写任何文件；文件在预算内但字节与重建不符 → 仍是有界比较失败，不是通过 | 第十三轮 P2-2、`ADR-0128` §8.3/§12、`H2-D11`、N1 |
| `an_output_parent_that_is_a_symlink_is_refused` | `bundles/locks/`、`bundles/sealed/` 或 `bundles/legacy/` 在 `--root` 下任一段是符号链接或 Windows reparse point → 写阶段在创建临时文件之前以 `path-escape`（退出 1）拒绝，目标树外不出现文件；只证明输入路径拒绝符号链接不算覆盖本规则 | 第十三轮 P2-2、`ADR-0128` §3/§8.3、`H2-D3`、N1 |
| `the_legacy_source_path_components_are_strict` | `legacy_source.isa`/`version` 含 `../`、`/`、盘符或 scheme → 路径形成前拒绝 | `H2-D3`、第一轮 P2 |
| `a_deleted_package_path_is_not_skipped` | 删除未发布包的 `package.json`/目录/重命名 → 由 base 树解析；删除已发布版本目录 → `published-package-modified`；无法映射是 `unmapped-package-path` | `H2-D5`、§5.3、第三轮 P1-1 |
| `only_executable_inputs_enter_the_source_digest` | 改 README/NOTICE → 源摘要不变；改 form 行 → 变 | `H2-D8` |
| `evidence_changes_do_not_move_the_definition_digest` | 在未发布候选包上改 README/NOTICE 并更新 evidence manifest → `evidence_digest`/`release_digest` 变，`definition_digest` 不变 | `H2-D8` |
| `an_evidence_entry_must_stay_inside_the_package_and_match_its_hash` | evidence manifest 列 `../` 或错误 sha256 → `evidence-mismatch`，退出 1 | `H2-D8` |
| `release_digest_tracks_the_release_not_the_builder` | 同 bundle 不同证据 → release 摘要不同；builder 版本变化 → release 摘要不变 | `H2-D8` |
| `the_legacy_snapshot_is_readable_by_load_dir` | 生成 `bundles/legacy/<bundle_id>/definition.json` → `Registry::load_dir` 可读；sealed bundle 放入定义目录被拒绝 | `H2-D9`、`H2-D12` |
| `a_build_never_writes_a_snapshot_it_cannot_read` | 合成闭包：合并后的 canonical 定义略高于 16 MiB（包与闭包都在 64/80 MiB 预算内）→ `build` 退出 0、**不写** `bundles/legacy/<bundle_id>/definition.json`（若先前存在则被删除），随后的 `verify --all --check` 通过；手工放入同尺寸快照 → `--check` 报 `resource-limit`（退出 1）。同一闭包两次构建结果一致，且 lock/sealed/摘要不变 | 第十九轮 P2-2、`ADR-0128` §8.3/§12、`H2-D11`/`H2-D12` |
| `changing_the_legacy_source_changes_the_source_digest` | `legacy_source` 从 `0.1.0` 改成 `0.78.0` → 源摘要变化；行未改时行相等测试失败 | `H2-D8`、`HE-AC-11` |
| `the_builder_identity_is_not_part_of_the_definition_digest` | 两个 builder 版本 → 同 definition/bundle 摘要，lock 的 builder 不同；`verify --check` 不把 builder 差异算作失败 | `HE-T19` |
| `the_generated_definition_is_read_by_fmp_model` | 坏 form 行 → `fmp_model::definition::read` 拒绝，构建器包装该拒绝 | `H2-D12` |
| `the_output_is_canonical_json` | lock/sealed 无空白、键排序、无尾随换行；与 Python canonical 一致 | `H2-D7` |
| `the_spec_lock_and_sealed_shapes_are_closed` | 三者的未知键/重复键被拒；`builder.build` 缺省时键省略而不是 `null`；lock 去掉 `builder` 后比较，sealed 逐字节比较 | `ADR-0128` §8.2、第四轮 P2-2 |
| `the_artifact_filename_matches_its_bundle_id` | `bundles/specs/mov.json` 的 `bundle_id` 是 `monasm.bundle.x86.mov` → `bundle-file-mismatch`；lock/sealed/legacy 同样检查；改成 `<bundle_id>.json` 后通过 | 第九轮 P2-1、`ADR-0128` §1.3、`H2-D9` |
| `the_bundle_and_release_vectors_match` | `ADR-0128` §8.2 的 metadata 在 Rust 与 Python 中都得到 `b6d92574…`/`4e3d44a8…`；改域分隔或把嵌套摘要写成原始字节 → 不匹配 | 第四轮 P2-2/P2-3 |
| `the_release_shaped_vector_matches` | 包项带 `evidence_digest` 时 Rust 与 Python 都得到 `evidence_digest = e9473871…`、`release_digest = ba60e8ba…`；漏写 `evidence_digest` 会退化成 `4e3d44a8…`，因此提交 lock 不能写成开发形状 | 第七轮 P2-3、`ADR-0128` §8.2 |
| `resource_limits_are_enforced` | 超文件数/大小/路径/依赖深度/闭包累计包根字节（多包）/资产总数/嵌套深度/单包累计资产字节 → 拒绝 | `H2-D11` |
| `the_published_version_directory_is_immutable` | base registry 已登记 `0.1.0`；作者新增 `0.2.0/` 并只改自有路径 → 旧 spec `verify --all --check` 仍绿，新包 `--package --release` 通过；原地改 `0.1.0` 的 form 或 `evidence/`/`tests/cases.json` → `published-package-modified` | 第三轮 P1-1、第五轮 P2-3、§5.3 |
| `a_first_publication_may_be_created_and_registered_in_one_pr` | 同一 PR 新增 `packages/.../0.1.0/`、spec、lock、sealed 和首个 registry 条目 → 通过；条目与最终 path/version/摘要不一致或未被 head spec 选中 → `published-registry-invalid`；合并后下一 PR 改同一目录 → `published-package-modified` | 第六轮 P1-1、`ADR-0128` §1.1/§8.1/§8.3 |
| `first_publication_bootstraps_without_registry_cycle` | 新包/新 spec 尚无 registry 行：`build` 成功并打印 `definition_digest`（不要求该行）；追加 `published` 与 `identities` 后 `verify --all --check` 与 `verify --published --check` 通过，两项都通过后才允许提交；`build` 从不写 registry。把追加放到任一 `--check` 之后会使 `--all --check` 报 `published-registry-incomplete`，因此不存在「先 check 后写行」的第二种顺序；合并提交才使该行成为 base 发布 | 第九轮 P2-3、第十二轮 P1-1、`ADR-0128` §8.3、`H2-D9` |
| `failed_build_leaves_no_published_partial_artifact` | 注入写阶段 I/O 失败 → 退出 2，registry 未改，未报告成功；lock/sealed 一新一旧时 `--check` 失败；修复后重建并通过。确定性拒绝发生在写任何文件之前，也不删除 legacy 快照 | 第九轮 P2-3、第十二轮 P2-1、`ADR-0128` §8.3、`H2-D9` |
| `a_failed_legacy_write_leaves_no_stale_snapshot` | 故障注入让第三个输出 `bundles/legacy/<bundle_id>/definition.json` 的临时写入或重命名失败 → 退出 2；lock 与 sealed 都是新字节且互相一致，旧 legacy 在写阶段开始时已被删除，因此路径缺失——缺失对等价门禁合法，`--check` 仍通过；`--definitions` 读取失败而不是返回上一版行；重新 `build` 后快照恢复且 `--check` 仍通过。断言不存在「新 lock + sealed、旧 legacy 仍可读」的组合；若实现留下旧文件，等价门禁必须以 `legacy-snapshot-mismatch` 拒绝 | 第十二轮 P2-1、第十四轮 P1、`ADR-0128` §7/§8.3、`H2-D12` |
| `a_modified_committed_legacy_snapshot_fails_the_bridge_gate` | 对一个正确的已提交 bundle，只改 `bundles/legacy/<bundle_id>/definition.json` 的一个 opcode，不改 spec、lock、sealed 或源包 → `verify --all --check` 以 `legacy-snapshot-mismatch`（退出 1）失败，尽管全部已记录摘要仍匹配；改回 canonical 字节后通过，删掉该文件也通过（缺失合法）。门禁不重建缓存、不把快照字节喂给任何摘要 | 第十四轮 P1、`ADR-0128` §8/§8.3/§12、`H2-D9`、`H2-D12` |
| `a_nested_package_manifest_cannot_mask_a_published_ancestor` | base registry 已发布 `packages/x86/monasm.isa.x86/0.1.0/`；同一 PR 在该目录内新增更深的 `package.json` 并修改同目录的 form → 变更路径门禁先按 base registry 判定包含，直接 `published-package-modified`（退出 1），不按 head 侧最近的 `package.json` 重新归类；把同一新增 `package.json` 放到 base 未登记的新版本目录则按首次发布处理 | 第十四轮 P2-3、`ADR-0128` §8.1/§8.3 |
| `lifting_the_transition_needs_a_versioned_build_rule` | H3 验收：同一份不相等的 `fmp-def/0.1` 选择，用 `monasm-bundle-spec/0.1` 构建仍被 `h2-exact-target` 拒绝（退出 1）；只有新的版本化构建规则版本能构建成功，且得到的 bundle 能绑定目标集合为子集的计划。断言 Builder 软件升级本身不改变 `0.1` 的结论 | 第十四轮 P2-2、`ADR-0128` §4.1、`H2-D4` |
| `a_base_published_version_cannot_be_edited_with_a_registry_change` | base 已登记 `0.1.0`；同一 PR 改 `0.1.0/` 的 form 并同时改写/删除/替换该登记项 → 包改动是 `published-package-modified`，登记改动是 `published-registry-modified`，退出 1 | 第六轮 P1-1、`ADR-0128` §8.1/§8.3 |
| `a_retired_published_version_is_still_immutable` | PR A 删除最后一个引用 `0.1.0` 的 spec，但保留 registry 条目；PR B 只改旧 `0.1.0/` 目录 → 按 base registry 判为已发布，`published-package-modified` | 第五轮 P1-2、`ADR-0128` §1.1/§8.3 |
| `a_concurrent_publish_freezes_the_old_commit_side` | A、B 从同一个旧提交 `M0` 分叉（`M0` 已有 `P/0.1.0` 目录但未登记）；B 先发布 `P/0.1.0`（追加 registry 条目）并合入目标分支；A 随后只改 `P/0.1.0/README.md` 这类不进 `source_package_digest` 的辅助文件 → 门禁以**目标分支尖端 `B`** 为权威，判定 `Published(B) ∋ P/0.1.0` 而 `TreeBytes_B(P) ≠ TreeBytes_H(P)`，报 `published-package-modified`（退出 1）。用 merge-base（仍是 `M0`）会把它当作未发布候选而放行；`verify --published --check` 也不覆盖该字节。同一 PR 若同时改 form → 仍是同一条拒绝 | 第十七轮 P1-2、`ADR-0128` §8.1 |
| `a_stale_publication_verdict_cannot_authorize_a_merge` | A 在 `P/0.1.0` 未发布时改 `P/README.md` 并通过门禁（记录的 `B_checked = B_A`，`Published(B_A) = ∅`）；随后 B 登记并合入 `P/0.1.0`，目标尖端变成 `B'`；合并检查在落地提交上重算 `B_landed` 和 `Tree(M)` → `B_landed ≠ B_checked`，拒绝复用（非零退出），必须在新尖端重跑门禁；重跑后同一 diff 报 `published-package-modified`（退出 1）。另测：基线不变但落地树 `Tree(M) ≠ C_checked`（例如合并方式产生不同树）同样拒绝。只有 `(B_checked, C_checked, mode)` 与落地提交相符才授权；仅做 post-merge 审计可检测但不能授权 | 第十九、二十轮 P1-1、`ADR-0128` §8.1、N5 |
| `a_target_subset_requires_per_form_ownership` | H3 验收：bundle 选 `{rv64i, rv64c}`、包 A 覆盖 `{rv64i}`、包 B 覆盖 `{rv64c, rv64i}`；声明 `{rv64i}` 的计划选中 `c.addi` → 新子集格子拒绝（`target-subset-unproved` 或逐 form 需求错误），尽管 `E_plan ⊆ E_bundle` 成立；把 `rv64c` 加入计划目标后通过。同一测试断言：从 `fmp-def/0.1`/legacy form 没有归属证明时默认拒绝，不按空集放行；两个旧格子结果不变 | 第二十轮 P1-1、`ADR-0128` §4.1、`H2-D4` |
| `the_published_registry_is_append_only` | 删除、改写、重排或替换 base 条目 → `published-registry-modified`；head spec 选中但无条目 → `published-registry-incomplete`；新条目未被任何 head spec 选中或摘要不符 → `published-registry-invalid`；仅追加合法条目通过；head-only 条目在无 spec 选中时可撤销 | 第五轮 P1-2、第六轮 P1-1、`ADR-0128` §8.3 |
| `a_published_identity_is_globally_unique` | 两个 spec 分别在 `packages/x86_64/monasm.x86.mov/0.1.0` 和 `packages/amd64/monasm.x86.mov/0.1.0` 登记同一 `monasm.x86.mov`/`0.1.0`、摘要不同 → `published-registry-invalid`；同一 path+摘要被两个 spec 引用 → 通过。同一 target 目录下路径由完整 `package_id` 唯一决定，两路径只可能来自不同 target 标签 | 第六轮 P1-2、第十七轮 P1-1、`ADR-0128` §8.3 |
| `a_retired_definition_identity_cannot_be_reused_with_new_bytes` | PR A 发布 `monasm.isa.x86`/`0.1.0-h2`（D1），PR B 删除该 spec；PR C 用同名字段但得到 D2、当前 spec 集合无冲突 → `definition-identity-conflict`。用相同 D1 重新发布 → 通过且不新增第二行 | 第七轮 P2-2、`ADR-0128` §8 |
| `a_bundle_id_may_advance_to_a_new_definition` | 同一 `bundle_id` 退役后由新 spec 选中新包版本 → 通过；新 lock/sealed 的 `bundle_digest` 不同，`(bundle_id, bundle_digest)` 是 bundle 内容标签，`release_digest` 是证据完备发布身份；同时存活的两个 spec 共用 `bundle_id` 仍 `bundle-id-conflict` | 第七轮 P2-2、第八轮 P2-3、`ADR-0128` §8 |
| `two_specs_cannot_share_a_bundle_or_definition_identity` | 两个 spec 共用 `bundle_id` → `bundle-id-conflict`；共用 `(namespace, version)` 但 `definition_digest` 不同或相同 → `definition-identity-conflict`；三项都合法后 `verify --all --check` 通过 | 第六轮 P2-1、`ADR-0128` §8 |
| `the_publication_audit_reads_retired_entries` | 退役 spec 后 `verify --all --check` 不读旧包；`verify --published --check` 仍检查旧条目，改旧目录或写错摘要 → `published-registry-invalid`；审计不进入 lock/bundle，未选中包不影响 `--all` | 第六轮 P2-3、`ADR-0128` §8.4 |
| `the_publication_audit_covers_executable_assets_not_auxiliary_bytes` | 已退役版本改 `package.json` 或 form 资产且不同步登记 → 审计 `published-registry-invalid`；只把 `README.md`/`NOTICE`/`tests/cases.json` 改字节并同步 evidence 清单 → 审计仍通过，因为 `source_package_digest` 不含这些字节。该变更由变更路径门禁 `published-package-modified` 和 git 历史承担，文档不声称审计能证明整目录不可变 | 第八轮 P2-2、`ADR-0128` §8.4 |
| `the_no_follow_open_is_proved_on_three_platforms` | H2a N1：Linux/macOS/Windows 各跑中间目录链接、末段文件链接、Windows reparse point、以及检查与打开之间替换目标 → 打开拒绝并报 `path-escape`。同一门禁还跑两条精确拼写负例：声明 `forms/add.json` 而中间目录是 `Forms/`，以及最终文件是 `Add.json` → 三平台都报 `path-lexical`，大小写不敏感卷不得成功打开。另加**目录项替换**场景：名字匹配后、打开前把该项换成另一文件或链接 → 只能打开刚匹配的对象或以 `path-escape` 拒绝，不能读到未检查的新对象；POSIX 上再把声明的资产路径换成 FIFO → 打开不得阻塞，结论是 `not-a-regular-file`（退出 1），不是退出 2；只测符号链接不算覆盖。某平台无法表达 no-follow 打开、精确名字查找或把打开绑定到匹配项时该平台失败，且 H2a 判定失败，不降级为跟随打开；一个只在 Linux 通过的门禁不算通过 | 第八轮 P2-4、第十轮 P1-2、第十一轮 P2-3、第十八轮 P2-1、`ADR-0128` §3/§9、N1 |
| `a_fifo_leaf_never_blocks_or_passes` | POSIX（Linux/macOS）：把 `forms/add.json` 或 `evidence/manifest.json` 换成 FIFO（无写者）→ 构建/`verify --package` 必须立即以 `not-a-regular-file`（退出 1）拒绝，不得挂起，也不得按 0 字节普通文件通过；把同一路径换成目录同样拒绝；类型判定必须来自已打开句柄：普通文件在 `stat` 之后、打开之前被换成 FIFO，仍须被句柄类型检查拒绝。Windows 上用目录项替换与 reparse 场景覆盖同一规则 | 第十八轮 P2-1、`ADR-0128` §3/§12、N1 |
| `a_retired_bundle_artifact_must_leave_the_tree` | PR A 删除最后一个 `bundles/specs/<bundle_id>.json` 但不删 lock/sealed/legacy → `verify --all --check` 报 `orphan-bundle-artifact`（退出 1）；同一 PR 一并删除三者、保留包快照与登记项 → 通过；`verify --published --check` 仍校验该版本包目录；在发布它的提交上旧 lock/sealed 仍可重建 | 第十八轮 P2-2、`ADR-0128` §8.4 |
| `a_published_version_cannot_change_evidence_in_place` | base 已登记 `0.1.0` 的 `tests/cases.json` 改动并同步 manifest → 仍然是 `published-package-modified`；新版本 `0.2.0/` 才允许 `evidence_digest`/`release_digest` 变化 | 第五轮 P2-3、`ADR-0128` §1.1/§7.1 |
| `a_package_update_does_not_edit_an_old_spec` | 只新增版本目录、不动 spec/lock；旧 lock 字节不变 | 第三轮 P1-1、`HE-AC-05` |
| `a_legacy_package_target_must_match_its_source` | 复制 x86 行不变、把 `execution_mode` 改成 `"32"` 或 `address_width` 改成 32 → `legacy-target-mismatch`，在 `read` 前拒绝；扩展成员不同（不是顺序不同）同样拒绝 | 第三轮 P1-2、第十六轮 P1-1 |
| `a_set_equal_target_migrates_a_differently_ordered_legacy_array` | 测试用合成包从 `definitions/rv64/0.6.0.json` 原样迁移一条 form（不发布第四个包）：新包按 §1 写 `["rv64c","rv64i"]`，legacy 是 `["rv64i","rv64c"]` → `TargetEq` 通过，构建成功；把成员改成 `["rv64c"]` 或 `["rv64c","rv64i","rv64m"]` → `legacy-target-mismatch`；把新包写成 legacy 顺序 → `extension-lexical`。原始数组相等会产生前两种都失败、后一种也失败的不可满足组合 | 第十六轮 P1-1、`ADR-0128` §1.1、§1 |
| `a_boundary_positive_lies_in_the_final_legal_domain` | 对 `D_form = {x ∈ D_Representable, L≤x≤U, x≡0 (mod 2^a)} \ E`：`x86:mov/rm8h-r8h/legacy`（`w=3`，`E={0,1,2,3}`）正例是 `4`/`7`；`aarch64:add/w32-w32-w32-imm6-lsl`（`E=32..63`）正例上界是 `31`；`riscv:c.addi/rd-imm6`（`E={0}`）正例下界是 `1`。把原始端点 `0` 或 `63` 当正例 → 该用例被实际 `bind` 拒绝，测试失败；excluded 值作 form 负例，只有可表示的越界值才作 `stage:"bind"` 负例 | 第十六轮 P1-2、`ADR-0128` §9.1 |
| `the_digest_preimage_vector_matches` | H2-D8 向量在 Rust 与 Python 中都得到 `1afee65c…`；把嵌套摘要改成原始 32 字节 → 不匹配 | 第三轮 P2-3 |
| `a_dependency_object_is_closed_and_keeps_its_vector` | 非空 `dependencies` 的固定向量在 Rust 与 Python 中都得到 `637edab0…`，依赖项自身是 `sha256:231b9034…`；把 `source_package_digest` 改成 `digest`、删掉该键、加第四个键、写成 `latest` 或范围 → 清单形状拒绝（退出 1）；数组按 `(package_id, version)` 逆序 → 拒绝而不是静默重排 | 第十七轮 P2-1、`ADR-0128` §1/§4/§7.0、`H2-D2` |
| `level_zero_and_level_one_projections_are_exact` | Level 0 声明 `symbols` → `case-expect-shape`；Level 1 `include_symbol_table:false` 缺 `symbols` → 接受，写 `symbols: []` → 拒绝；`fingerprint`/`materializer_version` 永不在投影 | 第三轮 P2-4 |
| `a_dependent_package_is_structure_verified_but_closure_unverified` | 非空 `dependencies` 且无闭包：开发 `verify --package` 退出 0 并打印 `dependency_closure: unverified`；`--release-evidence` 在完整证据下退出 0；`--release` 退出 1（`dependency-unverified`）；`--release --closure <lock>` 且摘要匹配后通过 | 第三轮 P2-5、第四轮 P1-3、第五轮 P2-4 |
| `a_handwritten_closure_digest_is_not_trusted` | `--closure` 的 lock 里写一个不存在的 `path` 或错误 `source_package_digest` → `dependency-mismatch`，不报告 `verified`；重读实际包后通过 | `ADR-0128` §8、第四轮 P1-3 |
| `the_transitive_closure_is_fully_rechecked` | A→B→C：lock 只列 A/B 缺 C、C 摘要错误、B 声明的 C 版本不符、或 A→B→C→A 成环 → 全部 `dependency-mismatch`；只有完整传递闭包才报告 `dependency_closure: verified` | `ADR-0128` §8、第五轮 P2-1 |

### 5.2 包级

| 测试（拟名） | 断言 | 对应 |
|---|---|---|
| `every_package_form_equals_the_pinned_legacy_row` | 三个包逐 form canonical JSON 相等，比较对象是钉住版本 | `HE-AC-03`、`HE-AC-11` |
| `a_form_row_is_compared_against_its_pinned_version_not_the_newest_file` | 把钉住版本换成最新版本 → x86 行被判定不等；构建器不自动改用最新 | `H2-D8`、`HE-AC-11` |
| `the_package_export_set_is_exact` | 导出集合 = 清单声明集合；没有隐藏 form | `HE-AC-03` |
| `a_representative_form_proves_its_bounded_operand_domain` | 对 H2a/H2b 实际交付的有界 form，正例取最终合法域 `D_form = {x ∈ D_Representable, L≤x≤U, x≡0 (mod 2^a)} \ E` 的最小值、最大值和一个内部值；原始端点若被排除或不对齐就不是正例。立即数用 `D_form` 的端点与可表示的越界值；寄存器按 `D_reg = ([0, 2^w−1] ∩ [0, 2^64−1]) \ E`——`w < 64` 的上界是 `D_reg` 的最大成员（通常 `2^w−1`），`w = 64` 至多 `u64::MAX` 且用排除值或错误 `target_type` 作 form 负例，`w > 64` 同样至多 `u64::MAX` 且不得要求 `2^w`；`0−1` 只作 `scope:"plan"` 负例；modifier 给允许对与可表示但不允许的对。excluded 值作 form 负例，只有可表示的越界值才作 `stage:"bind"` 负例；form 负例由 `bind` 在被改动操作数处拒绝。证据记录诊断实际携带的键——立即数 `E-RANGE-001` 的 `min`/`max`/`value`、寄存器 `E-OPERAND-004` 的 `target_type`/`value`/`field_bits`、排除值 `E-RANGE-004` 的 `target_type`/`value`/`excluded`，不要求该诊断不产生的键。pass 条件仍是 `(code, path)` 集合 | 第十、十一、十五、十六轮、`ADR-0128` §9.1、§4.3 |
| `a_wide_register_slot_keeps_the_h1_encoding_domain` | 合成包的槽位宽度为 127 和 192 位（各 placement ≤ 64 位，总和超过 64），寄存器值 `0` 与 `u64::MAX` 走 `plan::read` → `bind` → `materialize` 并产生确定字节；边界证据不得要求 `2^127`/`2^192`，form 负例用排除值或错误操作数类型。实现把作者层寄存器域硬编码为 64 位、或拒绝宽槽位时失败 | 第十五轮 P2-2、`ADR-0128` §9.1、`prototype/crates/fmp-materialize/tests/he1_wide_register.rs` |
| `a_static_stage_claim_is_not_a_dynamic_rejection` | 用例声明 `scope:"plan"` + `stage:"bind"`，但其计划在 `plan::read` 就以 `E-PLAN-002` 拒绝 → `verify --package` 只做静态检查可通过；`package_conformance` 必须拒绝为 `case-error-scope`（退出 1），且该用例不计为有效负例。报告必须分别记录“静态文档有效”和“执行阶段已验证” | 第十五轮 P2-1、`ADR-0128` §9.1 |
| `verify_package_reads_the_definition_not_the_plan` | 包合成的 `Definition` 非法（例如 `form_id` 与文件名不符、slot 缺 `placements`）→ `verify --package` 在 `fmp_model::definition::read` 处失败（退出 1）；包定义合法但某用例的计划在 `fmp_model::plan::read` 就非法 → `verify --package` 仍退出 0，只有 `package_conformance` 执行后按 stage 规则判 `case-error-scope`。这钉住“执行 definition::read、不执行 plan::read/bind/materialize”的分工 | 第十七轮 P2-2、`ADR-0128` §9.1、`H2-D3` |
| `the_x86_package_reproduces_legacy_machine_output` | X86-P1 的 §4.2.1 精确投影相等 | `HE-T18`（H2 部分） |
| `the_aarch64_package_reproduces_legacy_machine_output` | A64-P1、A64-P2 的 §4.2.1 精确投影相等 | `HE-T18`（H2 部分） |
| `the_rv64_package_reproduces_legacy_machine_output` | RV-P1、RV-P2 的 §4.2.1 精确投影相等 | `HE-T18`（H2 部分） |
| `the_only_difference_is_the_definition_identity` | 除 `fingerprint`/`definition_identity` 外无字段差异；错误 digest 被 `bind` 拒绝 | `HE-T18`、`HE-AC-06` |
| `packages_build_independently` | x86 与 rv64 各自构建，不读对方目录 | `HE-AC-08`（H2 部分） |
| `a_package_without_a_spec_is_still_checked` | 新包不写进任何 `bundles/specs/*.json` → `verify --package` 仍给出确定性通过/失败 | `H2-D5`、§5.3 |
| `a_synthetic_package_without_legacy_source_is_accepted` | 沿用现有 ISA family、form ID 不在 legacy 目录 → 清单/目标/`read` 通过，证明协议不依赖历史定义 | §4.1 |
| `a_wrong_opcode_in_a_structurally_valid_row_fails_the_package_gate` | 改错 opcode 保持 JSON 合法 → `read` 仍通过，`package_conformance` 的正例字节比较失败 | `HE-T18`、第一轮 P1-2 |
| `the_conformance_harness_discovers_packages_without_a_central_list` | 新增包但不动任何中心文件 → harness 自动发现并执行它的 cases | `HE-T14`、第一轮 P1-2 |
| `a_copied_package_yields_the_same_standalone_check` | 在不同目录/不同 cwd 对副本跑 `verify --package` → 同一身份、同一诊断、同一独立摘要 | 第一轮 P1-1 |
| `a_cross_isa_form_is_rejected_before_read` | 包声明 aarch64、导出 x86 form → `form-family-mismatch`，不进入合并文档 | 第二轮 P1-3 |
| `a_case_form_claim_is_bound_to_the_executed_plan` | 两个 form 的包里把 case 的 `form_id` 改成 B、计划仍编码 A → `package_conformance` 失败（`case-form-mismatch`），不把 B 记成已覆盖 | `HE-T18`、`ADR-0128` §9.1、第二轮 P1-2 |
| `an_unrelated_plan_error_does_not_cover_a_form` | 一个 `scope:"plan"` 负例故意写错 `expected_digest`：它可以通过 schema/执行，但不计入 form 覆盖；若标成 `scope:"form"`，`mutates` 不在操作数表面或差分不符 → `case-mutation-mismatch` | `HE-T18`、`ADR-0128` §9.1、第三轮 P1-3 |
| `a_form_negative_mutates_exactly_one_operand_field` | 基线正例只把 src2 改成 32 → 通过；同时改 `offset` 或 `expected_size` → `case-mutation-mismatch` | `ADR-0128` §9.1、第三轮 P1-3 |
| `the_case_diff_pointer_is_algorithm_independent` | 差分定义在两个**最终值**上，固定向量：`payload.reg` 10→11 → 指针为 `/instructions/0/operands/2/payload/reg`；`payload` 从对象变成标量 → 指针为该位置；新增一个对象成员 → 该成员指针，不是容器；改数组长度 → 数组本身；`payload` 的 `reg` 换成 `value` → 两个指针，因此不是单次变异。两个实现（Rust harness 与测试内独立实现）结果相同；改写整个对象与只改一个成员在最终值上不可区分，格式不尝试区分 | 第七轮 P2-5、第八轮 P1-1、`ADR-0128` §9.1 |
| `a_form_negative_matches_the_complete_diagnostic_set` | 声明一条 `E-OPERAND-004` 但实际还返回第二条诊断 → `case-diagnostics-mismatch`；把期望改成完整集合 → 通过 | `ADR-0128` §9.1、第三轮 P1-3 |
| `editing_cases_json_changes_the_release_identity` | 改用例并更新证据清单 → `evidence_digest`/`release_digest` 变，`definition_digest` 与机器码不变；不更新清单则 `evidence-mismatch` | `H2-D8`、§7.1、第二轮 P1-1 |
| `evidence_digest_tracks_case_evidence` | 改用例证据/证据清单 → `evidence_digest` 和 `release_digest` 变，`definition_digest` 不变 | `H2-D8`、第二轮 P1-1/P1-2 |
| `the_three_isa_harness_has_no_isa_branch` | harness 只读清单/用例数据；源码审查 + 测试覆盖三种包 | `HE-T14`（H2 部分） |
| `a_package_change_does_not_touch_legacy_roots` | `definitions/`、`fixtures/`、`payload_root` 不变 | `HE-AC-10`（H1 已证，H2 复跑） |

### 5.3 门禁

H2 每个提交至少通过：

- `cargo fmt --all -- --check`；
- `cargo test --workspace`（含新增的 `fmp-definition` 测试和
  `package_conformance`）；
- `python tools/check_ids.py`；
- `python tools/check_definition.py`（legacy 定义不变，必须仍绿）；
- `python tools/he1_baseline.py --check research/he1/compatibility-results.json`
  （128 payload + 两个 root 不变）；
- `tools/oracle/rerun.py`（`122/128`，6 跳过，0 失败）；
- `git diff --check`。

新增的构建检查可以放进现有 `workspace` job：

```text
cargo run -p fmp-definition -- verify --all --check
cargo run -p fmp-definition -- verify --published --check
```

第一条按 `bundles/specs/*.json` 显式重建，不按目录扫描决定选择；它还要求
派生产物与 spec 一一对应：`bundles/locks/`、`bundles/sealed/`、
`bundles/legacy/` 下的每个文件都必须有同树的 spec，孤儿是
`orphan-bundle-artifact`（退出 1），而每个 spec 仍必须有已提交的 lock 和
sealed。这条规则只枚举目录项，不打开未选中包，也不改变任何摘要，所以不影响
`HE-AC-05`。比较范围是 sealed bundle 全字节、lock 除 `builder` 外的字节；
`builder` 只做形状检查和打印，理由与 `ADR-0126` 的 payload/envelope 分层相同。
legacy 快照不在摘要或发布身份里：它是派生开发缓存（`H2-D12`），但若被提交，
`--check` 还要求它与 sealed 内 `definition` 的 canonical 字节相同，否则
`legacy-snapshot-mismatch`（退出 1）。第二条只审计
`bundles/published.json` 的全部条目（含退役版本），不选择任何包，也不影响
lock/sealed。两者分开，未选中包不会混入 bundle 构建，退役版本也不会漏检
（`ADR-0128` §8.4）。

普通扩展还需要独立门禁，且必须同时证明结构和机器码。作者的默认路径不要求先
改全局 spec，也不因包声明了依赖就被卡住：

```text
cargo run -p fmp-definition -- verify --package <changed-package-path>
cargo run -p fmp-definition -- verify --package --release-evidence <changed-package-path>
cargo test -p fmp-definition --test package_conformance
# 无依赖的包还跑完整发布检查；有依赖时加 --closure <lock>
cargo run -p fmp-definition -- verify --package --release <changed-package-path>
```

`verify --package` 用 `monasm-standalone/0.1` 独立身份，校验清单、路径/版本目录
一致、导出、`fmp_model::definition::read`、自述目标、legacy 目标一致性、用例
schema/覆盖/排序、`scope`/`baseline_case_id`/`mutates` 与计划差分、单指令
`form_id` 绑定、完整诊断数组形状与错误范围、证据引用与哈希、累计资产预算；
开发模式没有证据清单时
直接核对 case 自带哈希，有清单时以清单为准。它**不**执行用例的
`fmp_model::plan::read`、`bind` 或 `materialize`；`definition::read` 是它唯一
交给读取器的步骤。
`--release-evidence` 额外要求完整证据，但不声称闭包；非空依赖包仍能通过这一
证据门禁。`--release` 等于 `--release-evidence` 加闭包：依赖为空时通过，非空
时还要求 `--closure <lock>`，否则 `dependency-unverified`（退出码 1）。作者
可以在自己的 PR 里带一个精确的本地 lock 跑 `--release`，但只有被发布 spec
选中时，`verify --all --check` 才用 spec 闭包递归重读所有依赖并做完整 release
校验。`package_conformance` 执行每个包的 `tests/cases.json`：替换独立身份 →
`plan::read` → `bind` → `materialize`，比较 §4.2.1 的精确投影，并断言负例的完整
`(code, path)` 集合；`Internal`/`HostFailure` 不算通过。这些检查一起才能让
「opcode 改错但 JSON 合法」「声明 form B、实际执行 form A」或「用
`expected_digest` 冒充 form 边界」的包失败。

CI 从 PR diff 提取 `packages/**` 和 `bundles/published.json` 的变更：

- 修改/新增包文件：**先**用 base registry 判断包含——base registry 是**目标分支
  尖端 `B`** 的发布集合，不是 merge-base；只要变更路径位于某个 `B` 已登记的版本
  目录之内，直接 `published-package-modified`，退出 1；head 树里更深的
  `package.json` 不能把它重新归类成别的、未发布的根（第十四轮 P2-3）。门禁同时
  要求 `Published(B) ⊆ Published(H)`，并对每个 `p ∈ Published(B)` 比较
  `TreeBytes_B(p) = TreeBytes_H(p)`，所以分支从哪个旧提交分叉不影响结论。
  只有落在所有 `B` 已登记目录之外的变更，才在 **head** 树找最近的含
  `package.json` 的祖先；其目录名必须等于清单 `version`（`path-version-mismatch`）。
  只有 **`B` 中**已登记的
  版本目录才在本 PR 内不可变，任何修改是 `published-package-modified`，
  退出 1；当前 spec 是否仍选中它不影响判断。head-only 条目是首次发布：允许同一
  PR 创建和调整候选目录，但必须按最终 head path/version/重算摘要校验，否则
  `published-registry-invalid`。
- 删除包文件/目录：在 **`B`** 树找版本目录；若它在 base registry 中，删除其中
  任何文件是 `published-package-modified`。删除未发布包时，同一 PR 必须更新/
  删除引用它的 spec，`verify --all --check` 是「没有活引用」的证明；head-only
  登记项若路径已不存在且仍保留是 `published-registry-invalid`，无 spec 选中时
  可在同 PR 撤销。
- 重命名/移动：旧根和新根都检查；移动 base 已登记版本目录是
  `published-package-modified`；新增版本必须用同级新目录。移动未发布候选会改变
  spec 的 `path`，head 登记项必须指向最终路径；移动跨 target 目录还必须继续
  满足 form 家族一致性。
- 无法映射到任何版本目录的 `packages/**` 变更（例如直接放在 `packages/` 下的
  散落文件，或 base 树也找不到根）是 `unmapped-package-path`，退出 1，绝不
  静默跳过。
- `bundles/published.json`：删除/改写/重排 base 条目是
  `published-registry-modified`；head spec 选中的路径没有条目是
  `published-registry-incomplete`；新增条目未被任何 head spec 选中、与包摘要
  不符，或与另一条目共用 `(package_id, version)` 却换 path/摘要，是
  `published-registry-invalid`；只有追加合法条目通过，head-only 条目可撤销。
- **合并新鲜度（第十九、二十轮 P1-1）。** 门禁读取并记录
  `(B_checked, C_checked, mode)`：基线提交 SHA、被测候选树 SHA、合并模式。
  落地提交 `M` 必须满足 `B_landed = B_checked`、`Tree(M) = C_checked` 且
  `mode(M) = mode`；自动化检查在落地提交上重算并比较，不一致或缺失即失败
  （非零退出）。不能用提交 SHA 对代替树：每种合并模式都产生新提交，
  `refs/pull/N/merge` 的临时提交不是最终写入的提交。可建立等式的机制是 merge
  queue（在 merge-group 候选上跑门禁且只合并该候选，目标前进时组重建）或把记录
  的候选提交以「目标移动即被 git 拒绝」的方式落到记录的基线上；普通 up-to-date
  required checks 只在基线前进时重跑，不承诺落地树相等，不能单独作为授权依据。
  不得复用旧绿色结果，绕过保护路径的手工合并不是合法发布。H2a 通过平台 API 读取
  生效的 branch protection/merge queue 并把查询端点、生效配置与实际允许的合并
  操作写进报告；**403、空 ruleset 或读不到设置是未取到证据，本轮失败**，不能
  推断为没有保护。
- 合并后在目标分支再跑一次同一门禁，重算 `Tree(M)` 与 `B_landed`：已发布目录
  被改或落地树不符即失败。该运行只提供可检测性，不替代上面的等式。

这条路径不要求包已被任何 spec 选中，也不改中心 `bundles/specs/`。只改
`forms/*.json` 而不改清单也会触发检查。变更路径列表只决定跑哪些包，不决定
构建器选择什么。`verify --all` 覆盖发布组合，`verify --published --check` 覆盖
历史审计，`verify --package` 覆盖作者单包；
所有变更包跑 `--release-evidence`，无依赖的还直接跑 `--release`，有依赖的包
则由作者本地 closure 或被 spec 选中后的 `--all --check` 完成传递闭包重读。
这些门禁都列为 H2 退出门槛，不推迟到 H5。H2 不新增 per-package job matrix；单命令
加 diff 提取足够，完整 matrix 属于 `ADR-0130`。

## 6. 提交拆分

H2 是一个阶段，但按 `ADR-0125` §13.1 拆成两个可回归提交（同一 PR）：

| 提交 | 内容 | 必过 |
|---|---|---|
| H2a | `ADR-0128` 评审通过后接受 + 本文状态更新 + `fmp-definition` crate（manifest、spec、build、digest、error、CLI）+ `monasm-standalone/0.1` 独立身份 + **完整的单包发布证据与摘要机制**（`tests/cases.json` 入清单、`NOTICE`、`sources`、`oracle.status`/skip、`evidence_digest`/`release_digest`、跨语言摘要向量、用例/证据/spec/lock/registry 预算与单包累计资产预算）+ **版本目录不可变（只保护 base 条目、同一 PR 首次发布合法、追加登记、退役后仍不可变、全局 `(package_id, version)` 唯一且永久绑定 path/摘要）** + **`identities` 定义名历史与永久摘要绑定** + **spec 严格排序 + 跨 spec `bundle_id`/定义身份唯一** + **`bundle_id` 可移动、`(bundle_id, bundle_digest)` 为 bundle 内容标签、`release_digest` 为证据完备发布身份** + **打开动作 no-follow 的读取边界（含 Linux/macOS/Windows 可行性门禁与 `--root` 下的输出父目录）** + **已提交 lock/sealed 的有界流式比较** + **`requires_capabilities` 声明等于推导** + **冻结 legacy 定义名保留** + **form ⊆ 包 ⊆ bundle 与合并前逐包 `read`**（含 `form-extension-mismatch`） + **`structure`/`--release-evidence`/`dependency_closure` 三态**（含传递闭包重读、缺项/摘要错/环检测）+ **legacy 目标一致性（`TargetEq`：扩展按集合、其余字段严格相等）** + **边界正例取最终合法域 `D_form`** + **`scope:"form"` 仅 `bind` 拒绝、诊断落在变异操作数上、禁止 `E-BYTE-001`/`E-SIZE-001`** + **用例 stage 三态（`read`/`bind`/`materialize`）且声明阶段必须是第一个拒绝阶段；`verify --package` 只验静态契约，`package_conformance` 验执行阶段与完整诊断集，报告分开记录** + **Level 0/1 精确投影** + **值定义用例差分（成员编辑→成员指针、kind 变化→该位置、数组长度→数组）** + `verify --package --release`、`verify --published --check` 与变更路径门禁（含删除/重命名、registry 变更）+ x86 `mov-register` 包（`0.1.0/`）及其 `tests/cases.json`/`evidence` + 无 `legacy_source` 的合成包契约测试 + 错误 opcode 与错误 form 声明反例 + 构建器单测 + X86-P1 字节等价 + `bundles/` 的 x86 spec/lock/sealed/legacy snapshot + 初始 `bundles/published.json` + `gates.yml` 的 verify 三步与 conformance | fmt、workspace test（含 `package_conformance`）、`check_ids`、`check_definition`、baseline、whitespace |
| H2b | aarch64 `add-immediate`（`0.1.0/`）+ rv64 `integer-alu`（`0.1.0/`）+ 三 ISA conformance harness + 这两个包的 cases/evidence/NOTICE 资产 + 跨 ISA/跨包测试 + 全部 lock/sealed/legacy snapshot + 各自 registry 登记项 + `research/he1/H2-report.md` + `STATUS.md` 的 H2 记录 | 同上 + oracle |

H2a 必须先全绿再开 H2b：先证明一个包的构建、摘要、完整发布证据和字节等价，
再证明跨 ISA 与独立包。H2a 的 `--release` 必须已经具备完整的来源、`NOTICE`、
oracle 状态和用例证据校验；H2b 不回头补齐 H2a 的信任边界，只增加 AArch64/RV64
资产和跨包测试。H2a 不引入 H2b 才需要的多包 harness；H2b 不修改 H1 的身份代码。

H2a 的阶段边界不变，但按五个可独立 review 的回归节点推进；每个节点先加反例
测试再写实现，前一个节点全绿才进入下一个：

1. **N1 解析、路径门禁与摘要**：先做**平台可行性门禁**——在 Linux、macOS、
   Windows 上分别用中间目录链接、末段文件链接、Windows reparse point 和
   「检查后替换」场景证明所选路径层能在**打开动作本身**拒绝跟随；同一门禁还要
   证明已打开父句柄上的**逐字节精确名字查找**：声明 `forms/add.json` 而中间
   目录是 `Forms/` 或最终文件是 `Add.json` 时，三平台都报 `path-lexical`，
   大小写不敏感卷不得成功打开；再加**目录项替换**——名字匹配后、打开前把该项
   换成另一文件或链接——实现只能打开刚匹配的对象或以 `path-escape` 拒绝，不能
   读到未检查的新对象。任一平台只能以跟随打开通过、以「拒绝所有包读取」通过、
   无法做精确名字查找或无法把打开绑定到匹配项，N1 即失败，H2a 停止，不把失败
   改成降级。同一门禁还要覆盖**输出父目录**：`--root` 下 `bundles/locks/`、
   `bundles/sealed/`、`bundles/legacy/` 的任一段是链接或 reparse point 时，
   写阶段必须在创建临时文件之前以 `path-escape`（退出 1）拒绝。
   门禁通过后再做 manifest/spec/lock/published 封闭形状、路径/版本一致、
   标识符/路径段/产物文件名词法（`identifier-lexical`/`path-lexical`/
   `bundle-file-mismatch`）、包内相对路径与闭包仓库根相对路径两个冲突域、
   单一 `LoadedPackage` 生命周期（摘要、legacy 行/目标比较、逐包 `read` 与
   合并都消费同一份已加载值）、`capability-mismatch` 推导、
   `source_package_digest`、`evidence_digest` 与开发/发布两个跨语言向量。
2. **N2 闭包与 sealed**：严格排序、显式闭包、依赖边、归属冲突、spec 集合的
   `bundle_id` 与定义身份唯一、保留的 legacy 定义名（`reserved-identity`）、
   form ⊆ 包 ⊆ bundle 的逐包检查（`form-extension-mismatch`）、保守覆盖语义
   （高报合法、不裁剪）、合并前逐包 `read` 且合并消费同一 `LoadedPackage`、
   lock/sealed 字节和 `builder` 投影。
3. **N3 独立身份与 conformance**：`monasm-standalone/0.1`、`verify --package`、
   cases/证据、值定义差分指针、Level 0/1 投影、错误 opcode 与错误 form 声明反例。
4. **N4 发布生命周期**：base/head 登记、首次发布、全局身份唯一、`identities`
   定义名历史（永久摘要绑定、保留名不得登记、追加与撤销规则）、append-only、
   退役不可变、首次发布无登记循环（`build` 不要求其行、从不写 registry）、
   `build` 先内存校验再替换输出（失败不留已发布部分产物）、
   `--check` 以有界流式比较读取已提交 lock/sealed（1 MiB/80 MiB 预算，越界是
   `resource-limit`，不 `read_to_end`）、
   `--check` 对已提交 legacy 快照做 canonical 字节等价门禁（16 MiB 有界读取、
   缺失合法、不重建缓存、不进入任何摘要；不同是 `legacy-snapshot-mismatch`）、
   `build` 在 canonical 定义超过 16 MiB 时省略快照并删除旧副本（退出 0，
   随后 `--all --check` 通过；手工提交超限快照仍是 `resource-limit`）、
   `verify --published --check` 的有界断言（可执行资产与身份，
   不含 README/NOTICE/证据用例字节）。
5. **N5 门禁与 x86 包**：变更路径 CI（先按 base registry 判定包含，再做 head 侧
   包根发现，嵌套 `package.json` 不能遮蔽已发布祖先）、**合并新鲜度**
   （门禁记录 `(B_checked, C_checked, mode)` 并在落地提交上比较
   `B_landed`/`Tree(M)`/`mode`，不一致即拒绝；merge queue 或写入记录候选的合并
   操作由平台 API 证据证明；普通 up-to-date 检查不单独作为证明，合并后审计只作
   可检测性；403/空 ruleset 视为未取到证据）、x86 包与 bundles、
   `gates.yml`（`verify --all --check` 与 `verify --published --check` 都是必过
   项，取消其一即门禁失败）、H2a 报告（N4 增加 legacy 等价门禁与快照省略规则，
   N5 增加 base-first 映射与合并新鲜度证据）。

每个节点是一个可独立回归、可独立回滚的提交（或子 PR），各自带失败反例和
门禁，不是实施者内部的检查清单；前一个节点全绿才进入下一个，尤其不能在 N1 的
no-follow 可行性未证明前开始大量资产迁移。N1–N5 不改变 H2a/H2b 的交付边界；
N4 的发布门禁不能推迟到 H2b。

`ADR-0128` 目前在 PR #4 中为 `proposed`；评审合并后才写 `accepted`，H2a 也从
那里开始实现。`ADR-0130` 不在 H2 内，除非 H2b 决定增加 per-package job
matrix。若增加，先写 `ADR-0130`，再改 workflow。

## 7. 风险与回滚

| 风险 | 处置 |
|---|---|
| 构建器变成第二套定义权威 | 构建器只做清单/闭包/归属/合并/摘要；form 结构一律交给 `fmp_model::definition::read` |
| canonical 实现漂移 | 复用 `fmp_model::canonical`；与 Python `check_definition.py` 的 canonical 对照测试 |
| 包顺序、spec 顺序或目录顺序影响摘要 | spec 的 `packages` 按 `(package_id, version)` 严格排序，逆序是拒绝而不是第二种写法；显式列出完整闭包与 `path`；合并后按 `form_id` 排序；从不扫描 `packages/`；同一合法 spec 在不同创建/读取/集合迭代顺序下必须得到同一摘要与 sealed 字节 |
| 摘要来自 A、合并来自 B（同一路径被重读） | 每个包只读取一次为不可变 `LoadedPackage`；`source_package_digest`、legacy 行/目标比较、逐包 `read` 和合并消费同一份值；禁止摘要后按路径重开；故障注入测试覆盖两次阶段之间的文件替换 |
| 把 form 排序误当程序布局排序 | 文档与测试分开「包集合规范化」和「指令/节/fixup 顺序」；后者不由构建器触碰 |
| 归属冲突被 last-wins 吞掉 | 构建期唯一归属表；相同内容也失败；`HE-T07` |
| 路径逃逸/符号链接 | 从 `--root` 到实际读取的每一段都 no-follow；链接或 reparse point 是 `path-escape`；不用 canonicalize-then-open，也不接受「先 non-follow 预检、再按路径打开」；打开动作本身必须拒绝跟随 |
| 同一非法名字在某平台成功、在另一平台 I/O 失败 | 标识符/路径段/产物文件名按 `ADR-0128` §1.3 的词法在打开前校验；大小写折叠冲突、尾点/空格、Windows 设备名都是 `path-lexical`，`package_id`/`bundle_id` 违规是 `identifier-lexical`，产物名与 `bundle_id` 不符是 `bundle-file-mismatch`；三平台测试同一退出码 |
| 跨包同名相对路径被误判冲突 | 冲突比较域随根而定：包内按相对字符串，闭包按 `packages[].path` 拼接后的仓库根相对路径；不同包根下的 `forms/add.json`/`tests/cases.json` 合法共存；只有折叠后相同的包根或重复 `path` 是 `path-lexical`；两个验收向量分别证明合法组合与根别名拒绝 |
| 声明小写合法，磁盘目录项大小写不同 | 精确名字查找在已打开的父句柄上完成，中间目录和最终文件都要求逐字节同名；大小写不敏感卷上的 `Add.json` 打开是 `path-lexical`，不是成功；N1 三平台门禁包含这两条负例，与 `forms/Add.json` 的声明词法测试分开 |
| 名字核对后、打开前目录项被替换 | 打开必须绑定到刚匹配的目录项（句柄或对象身份核对），不能按同名重开；发现替换以 `path-escape` 拒绝；N1 三平台门禁包含该场景，只测符号链接不算覆盖 |
| 合法路径指向 FIFO/socket/设备节点，打开阻塞或绕过预算 | 中间段必须是目录、叶子必须是普通文件，类型取自已打开句柄（`fstat`/`GetFileInformationByHandle`），不取自路径 `stat`；POSIX 输入打开带 `O_NONBLOCK`，FIFO 在类型判定前不会挂起；非普通叶子是 `not-a-regular-file`（退出 1），不是退出 2；N1 的 POSIX FIFO 负例必须立即返回 |
| 解除 `h2-exact-target` 变成静默放宽 | 目标兼容是（计划, 定义）矩阵：`fmp/0.1`+`fmp-def/0.1` 保持相等，`fmp/0.1`+`fmp-def/0.2` 保持子集加逐 form 需求；增加格子需要新计划协议**加**版本化构建规则，构建选项不能绕过；H3 在矩阵各格跑同一包与不同扩展集合 |
| 按计划格式判断目标关系，重新拒绝合法输入 | `check_target` 的 `subset_rule` 只读定义格式；`fmp/0.1`+`fmp-def/0.2` 是既有合法格子，H3 验收必须显式覆盖它不被重新拒绝 |
| 只加 `fmp/0.2` 计划协议就以为解除了构建期拒绝 | Builder 在绑定计划前按 `h2-exact-target` 拒绝不相等的 `fmp-def/0.1` 选择；解除需要版本化构建规则，且 `monasm-bundle-spec/0.1` 对同一选择永久保持拒绝，Builder 升级不能改变旧格式的接受语义 |
| 嵌套 `package.json` 遮蔽已发布祖先 | 变更路径先按 base registry 做祖先包含判断，命中即 `published-package-modified`；只有 base 之外的变更才做 head 侧包根发现 |
| 并行发布后用 merge-base 判定，已发布目录被改仍放行 | base registry 取**目标分支尖端 `B`**，不取 merge-base；门禁要求 `Published(B) ⊆ Published(H)` 且每个 `p ∈ Published(B)` 的 `TreeBytes_B(p) = TreeBytes_H(p)`。反例：A、B 从 `M0` 分叉，B 先发布 `P/0.1.0`，A 再改 `P/0.1.0/README.md`（不进 `source_package_digest`）→ 必须 `published-package-modified` |
| 包目录只取 `package_id` 末段，独立作者命名空间相撞 | 目录段等于**完整** `package_id`：`packages/<target>/<package_id>/<version>/`，映射是单射；`monasm.x86.crypto` 与 `vendor.x86.crypto` 可同 target 同版本共存，不需求改名或协调版本 |
| 负寄存器被当成 form 边界负例 | `payload.reg` 是 `u64`，`{"reg":-1}` 在 `plan::read` 就被拒绝，`bind` 从未运行；`D_form ⊆ D_Representable`，该值只能作 `scope:"plan"` + `stage:"read"` 负例，寄存器 form 负例用可表示的排除值或（`w < 64` 时）`2^w` |
| 宽寄存器槽位被 64 位假设压缩 | `w` 是 placement 宽度之和，可超过 64；`D_reg = ([0, 2^w−1] ∩ [0, 2^64−1]) \ E`。`w ≥ 64` 用 `0`/`u64::MAX` 和排除值或错误 `target_type`，不要求 `2^w`；127/192 位包级测试防止作者层缩回 H1 已验证的能力 |
| 用 `bind` 阶段记录读取期拒绝 | `read` 是独立阶段：`plan::read` 返回单个 `Diagnostic`，该用例写 `scope:"plan"` + `stage:"read"`；声明的阶段必须恰是第一个拒绝阶段，否则 `case-error-scope`（退出 1），不产生证据；form 覆盖仍只认 `bind` |
| 证据要求诊断不产生的 `min`/`max` | 只有立即数 `E-RANGE-001`/`E-RANGE-002` 带 `min`/`max`；寄存器 `E-OPERAND-004` 只带 `target_type`/`value`/`field_bits`，`E-RANGE-004` 只带 `target_type`/`value`/`excluded`；证据记录实际字段，寄存器上界由 `field_bits` 推导，pass 条件仍是 `(code, path)` |
| 单个 modifier 值变化无法表达 | `mutates` 允许 `…/modifiers/<i>/name` 与 `…/modifiers/<i>/value`；`bind` 在 modifiers 数组的 `E-OPERAND-003` 是它们的祖先，符合位置规则；modifier 按允许值集合测，不套整数区间 |
| 单段包根文件被路径产生式拒绝 | 产生式是 `pseg ("/" pseg)*`，`NOTICE`/`README.md` 是单段且是仅有的两个大写例外；发布证据门禁要求它们可声明 |
| 一个非法邻域被当成完整操作数域 | 边界只在 `D_Representable` 内取，正例取 `D_form` 的最小/最大成员与内部值（`D_form = {x ∈ D_Representable, L≤x≤U, x≡0 (mod 2^a)} \ E`）；寄存器按 `D_reg` 取端点，`w < 64` 才有可表示的 `2^w`；modifier 用允许/不允许对；不可表示的值是 plan 负例；证据记录实际诊断字段，pass 条件仍是 `(code, path)`，不引入新错误码 |
| 原始区间端点被排除或不对齐，却被当成正例 | `x86:mov/rm8h-r8h/legacy` 的 `E={0,1,2,3}`、`aarch64:add/w32-w32-w32-imm6-lsl` 的 `E=32..63`、`riscv:c.addi/rd-imm6` 的 `E={0}` 都排除原始端点；正例必须取 `D_form` 的端点（`4`/`7`、`31`、`1`），否则正例会被 `bind` 拒绝而无法提交证据 |
| 迁移包的扩展数组顺序与冻结 legacy 不同 | `TargetEq`：`definition_format` 相等，`target_identity` 除 `enabled_extensions` 外逐字段 canonical 相等、该字段按集合相等。`rv64/0.6.0` 的 `["rv64i","rv64c"]` 与规范写法 `["rv64c","rv64i"]` 等价；原始数组相等会让两种写法分别被 `legacy-target-mismatch` 与 `extension-lexical` 拒绝 |
| 静态用例校验被当成真实阶段证明 | `verify --package` 只证明声明形状、scope/stage 取值、诊断数组形状和指针语法，不执行 `plan::read`/`bind`/`materialize`；`package_conformance` 才证明第一个真实拒绝阶段与完整诊断集。声明 `bind` 但 `read` 已拒绝的用例必须由 conformance 判为 `case-error-scope`，报告分别记录两种状态 |
| 独立身份随目录/cwd 漂移 | 固定 `monasm-standalone/0.1` 函数；复制到不同目录/换 cwd 的摘要相等测试；保留前缀禁止写入 spec |
| 新包没有机器码证据也能通过 | 每个导出 form 强制正例+负例；`package_conformance` 执行；错误 opcode 反例；`--release-evidence` 检查证据完整性，`--release` 再加闭包 |
| 用例声明 form B、计划实际执行 A | 计划恰好一条 instruction，`instruction_id`/`form_id` 必须等于 case 字段；不一致 `case-form-mismatch`；正例比较实际执行的 form |
| 负例被无关错误满足 | 只有 `scope:"form"` 计入覆盖；它必须绑定同 form 的正例、只改一个操作数指针、由 `bind` 拒绝，并匹配完整 `(code, path)` 集合；至少一条诊断必须落在变异操作数或其父对象上；`expected_digest`/`E-BYTE-001`/`E-SIZE-001` 只能作为 `scope:"plan"` |
| 已发布包被原地改写，旧 spec 无法重建 | 版本目录是发布快照；`bundles/published.json` 永久登记已发布路径；只有 `B` 中已发布的条目在 PR 内不可变，同一 PR 首次创建并登记合法；旧目录禁止修改/删除；新版本用同级新目录；CI 按目标分支尖端判 `published-package-modified`，删除 spec 不清除登记；删除 base 条目本身是 `published-registry-modified` |
| 旧绿色结果在目标分支前进后仍被当作授权，或落地树与被测树不同 | 门禁结论绑定 `(B_checked, C_checked, mode)`；在落地提交上重算 `B_landed`/`Tree(M)`/`mode`，不一致即失败并重跑；用 merge queue 或写入记录候选的合并操作；普通 up-to-date 检查不单独作为证明；平台设置由 H2a 通过 API 证明，403/空 ruleset 视为未取到证据；post-merge 运行只提供可检测性 |
| 退役后留下无 spec 的 lock/sealed，语义不明 | 派生产物与 spec 一一对应：删除最后一个 spec 的同一 PR 删除 lock/sealed/legacy；`--all --check` 双向检查，孤儿是 `orphan-bundle-artifact`（退出 1）；包快照与登记项保留，退役字节由 git 历史保存；不定义归档格式，不留下未选中 sealed 文件 |
| 首次发布被登记顺序卡死，或写失败留下半成品 | 三个时点分开：候选输出（`build` 退出 0）、registry 追加（publisher 用打印出的摘要写 `published`/`identities`）、发布（合并提交）。顺序固定为 build → 追加 → 两项 `--check` → 提交；`--all --check` 要求行已存在，所以不存在「先 check 后写行」。`build` 先内存校验全部输出，再写临时文件并重命名，确定性拒绝不写文件，写阶段失败退出 2 且不写 registry；lock/sealed 一新一旧必被 `--check` 拒绝；`build` 从不写 registry |
| legacy 快照被当成发布身份，或提交后与 sealed 漂移 | 它是派生开发缓存，不进入四个摘要、缺失合法；但提交副本要与已校验 sealed 内 `definition` 的 canonical 字节完全一致，不同是 `legacy-snapshot-mismatch`（退出 1），该门禁不重建缓存也不喂摘要；写阶段先删旧 `definition.json`，最后写新文件，第三个文件写失败留下缺失而不是旧行；退出 2 后读到的字节不算当前构建证据 |
| 合法闭包因可选缓存而不可构建，或 build 写出自己读不了的快照 | canonical 定义超过 16 MiB 时 `build` 省略快照并删除旧副本（退出 0），`--all --check` 接受缺失；手工提交超限快照仍是 `resource-limit`；合成测试覆盖略高于 16 MiB 的定义，断言同一闭包两次构建一致且摘要不变 |
| 构建器升级把旧 `0.1` 清单从拒绝变成接受 | 接受语义属于声明的 `package_format`，不属于读取它的工具版本；`monasm-package/0.1` 永久拒绝非空 `types`/`profiles`，H4 必须用显式新格式版本启用语义，键名复用不放宽 `0.1`；测试用同一份未改动清单断言结论与构建器版本无关 |
| 同一扩展/能力集合有两种 JSON 写法 | `enabled_extensions`/`requires_capabilities` 必须严格递增、无重复；逆序是 `extension-lexical`、重复是 `capability-lexical`，在集合关系之前拒绝；构建器不静默重排，派生集合按成员比较 |
| 闭包预算只算 manifest/资产，漏掉 cases 与证据 | 单闭包计数器累加实际读取的包根字节：manifest、声明资产、`tests/cases.json`、证据清单及其列出的文件；同一路径每包根计一次，菱形共享包只计一次；在越界读取处 `aggregate-limit` |
| 把「目标覆盖已验证」当成「ISA 需求已完整证明」 | `fmp-def/0.1` 下 `E_form = ∅`，只证明 `E_package ⊆ E_bundle`；`legacy_source` 只加 target 一致性；报告必须单列这条限制，且不为消除它新增 ISA 专用推导器 |
| H3 只查计划 ⊆ bundle，子集计划选中目标不支持的指令 | 逐指令检查 `E_owner(form(i)) ⊆ E_plan`；归属证据来自版本化 bundle 映射或另一冻结来源，`monasm-bundle/0.1` 不补；无证明的 legacy form 在子集组合下默认拒绝（`target-subset-unproved`），不按空集放行；验收含 `c.addi`/`rv64i` 反例与旧格子回归 |
| 同一逻辑包版本有两个内容 | registry 的 `(package_id, version)` 全局唯一，首次登记永久绑定 path 和摘要；多个 spec 只能引用同一项；第二项换 path/摘要是 `published-registry-invalid` |
| 两个 spec 共用产物或定义身份 | 同时存活的 spec 不能共用 `bundle_id`（`bundle-id-conflict`），也不能共用 `(namespace, version)`（`definition-identity-conflict`）；不以摘要相同为由接受 |
| 退役后同名定义被换成不同字节 | `identities` 永久绑定 `(namespace, version)` 与 `definition_digest`；退役 spec 不删除该行；换摘要即 `definition-identity-conflict`，同摘要重发合法且不新增行 |
| 发布线推进被误当成身份冲突 | `bundle_id` 是可移动的发布线，退役后可由新 spec 推进到新定义；不可变的 bundle 内容标签是 `(bundle_id, bundle_digest)`，由 lock/sealed 与 git 历史记录；证据完备的发布身份是 `release_digest` |
| 复用冻结 `definitions/` 的名字产生第二份同名定义 | 构建器把 `<root>/definitions/*/*.json` 的 `(namespace, version)` 作为只读保留集合；spec 或 `identities` 命中即 `reserved-identity`；H2 自己的 bundle 用 `0.1.0-h2`，不占用旧名 |
| 更宽的 bundle 让欠声明的包变合法 | 每个包先按自己的 `target_identity` 生成文档并 `read`，再合并；form 需求超出包声明是 `form-extension-mismatch`；`verify --package` 与 `verify --all` 对同一包结论一致 |
| 把 `profile_id` 当成全局目标身份 | 它只是包内名义标签；兼容性、生成文档、lock/sealed 与摘要都用六键 `target.identity`；同名的两个 spec 可声明不同 identity，H2 不加跨 spec 唯一性，也不建中央 profile 表 |
| 把保守覆盖当成最小集合，或擅自裁剪声明 | 契约只证明 `⋃E_form ⊆ E_package ⊆ E_bundle`；高报合法且只缩小可选 bundle 范围；构建器不裁剪声明（否则 `source_package_digest` 与作者写的不同，包会无编辑变可选）；精确性留待后续版本化规则 |
| 路径层在某个平台没有 no-follow 打开 | H2a N1 是三平台可行性门禁：中间目录链接、末段链接、reparse point、检查后替换都必须被拒绝；某平台做不到就停止 H2a，不以「拒绝所有读取」或「跟随打开」通过 |
| 输出目录被仓库内链接重定向 | 输出目录是发布者控制的受信任路径，但 `--root` 下每个父段都 no-follow；链接/reparse point 在创建临时文件前以 `path-escape` 拒绝；N1 用链接化的 `bundles/locks/` 证明 |
| 审计被当成整目录不可变证明 | `verify --published --check` 只证明清单、可执行资产和身份；README/NOTICE/证据/用例字节由变更路径门禁与 git 历史承担，文档写明边界，不新增 `snapshot_digest` |
| 差分指针随 JSON 库或编辑操作漂移 | 差分定义在两个最终值上：成员增删→成员指针，kind 变化→该位置，数组长度→数组；两成员改动是两个差异因此拒绝；改写整体对象与改一个成员不可区分，格式不尝试区分 |
| 回滚删掉了发布证据 | 首次发布合并前可删除实验产物；合并后运行时回退为 H1，但快照与 base 登记项保留；撤销是退役 spec，不是删目录 |
| 迁移包行相同但执行目标变了 | 有 `legacy_source` 时比较 `definition_format`（严格相等）和 `TargetEq`（`target_identity` 除 `enabled_extensions` 按集合外逐字段相等）；不一致是 `legacy-target-mismatch` |
| Rust 与 Python 对同一摘要字节不一致 | 冻结域分隔、`sha256:` 文本规则和两个固定向量（开发形状与带 `evidence_digest` 的发布形状）；H2a 两种语言都必须通过 |
| 发布 lock 用了开发形状的 `release_digest` | 第二个向量的包项必带 `evidence_digest`；漏写得到 `4e3d44a8…` 而不是 `ba60e8ba…`，字节比较即失败 |
| 缺失键被 harness 归一化成空数组 | Level 0/1 投影键集固定；缺 `symbols` 与 `symbols: []` 不等价；由 `case-expect-shape` 拒绝 |
| 单包验证声称依赖已证明 | 分别报告 `structure`、`--release-evidence` 和 `dependency_closure`；无显式闭包时非空依赖是 `unverified`，`--release` 退出 1；闭包验证递归重读所有可达依赖 |
| 改测试集不改变发布身份 | `tests/cases.json` 列入证据清单；未发布候选上未更新清单是 `evidence-mismatch`，更新后 `release_digest` 改变而 `definition_digest` 不变；已发布目录改证据是 `published-package-modified` |
| 不同扩展集合的包无法组合 | 包 `enabled_extensions` 是需求、spec 是选择；H2 用 `h2-exact-target` 过渡，H3 用新的计划/定义协议增加矩阵格子并在 H5 前生效；既有两个（计划, 定义）格子保持原结论 |
| form 家族与 target 张冠李戴 | 规则是 `family(form_id) == isa_family` 字符串相等，不是包格式 ISA 白名单；跨 ISA 注入反例；在 `read` 之前拒绝 |
| 新增 ISA 被迫改包格式 | 包格式不列家族；H3 的第四种 reader 家族只要自述相等就通过；构建器不追加 ISA 名单 |
| 包输入预算只覆盖闭包 | `tests/cases.json` ≤ 16 MiB，证据清单/spec/lock 各 ≤ 1 MiB；forms ≤ 1024、assets ≤ 2048、cases/证据文件 ≤ 4096；单包 manifest+资产累计 ≤ 16 MiB，按实际读取累加；闭包累计读取包根字节 ≤ 64 MiB（含 cases 与证据）；未选中包也受限 |
| `--check` 把已提交 sealed 整体读入内存 | 已提交 lock/sealed 按预算有界流式比较（1 MiB/80 MiB），越界是 `resource-limit`（退出 1），不是宿主错误，也不 `read_to_end` |
| 删除/重命名包逃过路径门禁 | 删除在 base 树解析包根；删除 `package.json`/包目录必须同步改 spec；无法映射是 `unmapped-package-path` |
| 深 JSON 先解析后测深度 | 迭代扫描在 `json::parse` 之前执行；≤1 MiB 数万层反例不得栈溢出 |
| 证据完整性只是名义存在 | `--release-evidence` 要求 `tests/cases.json`、`NOTICE`、`sources`、`oracle.status`、skip 理由；证据清单进入 `evidence_digest`；`--release` 在此基础上加闭包 |
| H2a 的发布校验不完整 | H2a 就交付单包完整证据与摘要机制；H2b 只增加 ISA 资产和跨包测试，不补信任边界 |
| 退役版本漏检，或未选中包混入 bundle | `verify --all --check` 只读当前 spec 的精确闭包；`verify --published --check` 单独审计 registry 全部条目；两者都由 CI 运行，且都是 `gates.yml` 的必过项（不是可选命令），互不选择 |
| 包文件改动漏进 legacy | `definitions/` 只读；`payload_root`/`definitions_root` 复跑；PR diff 检查 |
| lock/sealed 提交后过期 | CI `verify --all --check` 重建；sealed 全字节、lock 除 `builder` 外比较 |
| 把 H2 做成 H3/H4 | §9 明确排除；`bind` 签名、`fmp/0.2`、profile、深层 JSON 不动 |
| 普通扩展仍要改中心表 | 包测试由 `verify --package` + PR 变更路径驱动；`STATUS.md` 计数不手工加；`check_definition.py` 不扩展 |
| 未发布的新包没有门禁 | `verify --package` 不依赖 spec；CI 提取变更 `packages/**` 路径逐个跑 |
| 未知 capability 进入已验证快照 | build/verify 拒绝白名单外的 `requires_capabilities`；声明必须等于从行结构推导的集合（`capability-mismatch`）；运行时协商仍属 H3 |
| 包漏报自己用到的 capability | 推导规则：有 `placements` → `field-placement/v1`，`from: operand_value` → `integer-domain/v1`；每个合法 `fmp-def/0.1` form 都至少有一个 slot 和 placement，所以含 forms 的包声明 `[]` 一律 `capability-mismatch`，没有「无 slot → 空集」的合法情形；两个方向不符都拒绝 |
| 不同 diff 库对同一用例给出不同指针 | 差分定义在两个最终值上：成员增删报告成员、kind 变化报告该位置、数组长度变化报告数组；固定向量覆盖成员级改动、kind 变化与两成员改动（后者因两个指针被拒） |
| 宽 bundle 替欠声明的包放行 | 每个包先按自己的 `target_identity` 生成文档并 `read`，再做 form ⊆ 包 ⊆ bundle；违规是 `form-extension-mismatch` |
| 复用冻结 legacy 定义名 | 构建器保留 `definitions/*/*.json` 的 `(namespace, version)`；spec 或 `identities` 命中即 `reserved-identity` |
| 发布审计被当成整目录证明 | 审计只覆盖清单、可执行资产与身份；README/NOTICE/证据/用例字节由变更路径门禁与 git 历史承担 |
| 不同定义格式被隐式混用 | 闭包要求所有包 `definition_format` 一致；混合即拒绝，不转换 |
| 证据改动改变执行身份 | 证据只进 `evidence_digest`/`release_digest`，不进 `definition_digest` |
| 旧定义快照无法被旧入口读取 | 额外输出 `bundles/legacy/<bundle_id>/definition.json`；sealed 不是定义文档 |

**回滚分两种，两种都不能删除已发布的历史。**

运行路径的回退与发布历史的保留是两件事。H2 只新增 crate、包和 bundle；
`bind`/`materialize`/`Definition` 不变，`packages/` 和 `bundles/` 也不是运行期
发现路径。

- **首次发布合并之前**：H2 仍是实验。撤回 H2 提交即可回到 H1 状态，删除
  `packages/`、`bundles/` 和空的 `bundles/published.json` 不违反任何发布义务，
  也不需要迁移持久状态。
- **首次发布合并之后**：运行时仍可回退为 H1（不链接、不调用 `fmp-definition`，
  legacy 构建照旧），但已公布的 `packages/**/<version>/` 快照和
  `bundles/published.json` 的 base 条目必须保留。撤销一个已发布版本是**退役**：
  删除或改写选中它的 spec，让 `verify --all --check` 只覆盖剩余 spec，
  `verify --published --check` 继续审计该版本的登记项与字节。若这是该
  `bundle_id` 的最后一个 spec，同一 PR 还必须删除它的 lock、sealed 和 legacy
  快照，否则 `verify --all --check` 以 `orphan-bundle-artifact`（退出 1）拒绝。
  删除快照或登记项是 `published-package-modified`/`published-registry-modified`，
  不是回滚。

代价是仓库保留历史版本的目录；收益是任何已公布的 lock 仍能在其提交处
`verify --all --check` 重建，且回退运行时不会静默销毁发布证据。退役留下的
lock/sealed/legacy 由 git 历史保存，当前树只保留与现存 spec 一一对应的派生产物；
H2 不定义归档格式，也不提供恢复已退役 bundle 的工具；至于什么时候可以删除
历史包目录，是 H5 之后的决定，不在本计划内。

## 8. 明确不在 H2 内

- `fmp/0.2` 计划格式、命名空间化 ISA 身份、零操作数 form（H3）。
- 运行期 bundle reader、运行期能力协商、未选中包损坏隔离（H3）；H2 只在
  构建期拒绝未知能力字符串。
- `fmp-def/0.1` 与 `0.2` 的隐式转换或自动迁移（H3 的显式转换）。
- `type`/`profile` 资产的执行或输出；非空声明在 H2 被拒绝（H4）。H2 只冻结
  外层身份、排序、摘要输入和拒绝语义，不冻结其内部语义。
- `bind` 接受 `VerifiedBundle`、`fmp-validate → fmp-definition` 依赖（H3）。
- 解除 `h2-exact-target` 的 H3 计划侧目标兼容；H2 只声明过渡限制和退出门槛。
  H3 的解除必须同时包含新计划协议与版本化构建规则，并保持 `fmp/0.1` +
  `fmp-def/0.1`（相等）
  与 `fmp/0.1` + `fmp-def/0.2`（子集加逐 form 需求）两个格子不变；验收测试
  `lifting_the_exact_target_requires_a_new_protocol` 用同一包与不同扩展集合跑
  矩阵三行：前两行必须复现今天的相等/子集结论（包括 `fmp-def/0.2` 的逐 form
  需求仍拒绝缺少扩展的行），只有新计划协议那一行按其自身规则接受子集。不能靠
  删除构建器里的相等检查、按计划格式重判或增加构建选项完成；同一份不相等的
  `fmp-def/0.1` 选择在 `monasm-bundle-spec/0.1` 下必须永久保持拒绝，
  `lifting_the_transition_needs_a_versioned_build_rule` 断言 Builder 升级本身
  不改变旧格式的接受语义。
- 对新增包实际重跑或联网调用外部 oracle；H2 只校验证据记录、来源、哈希和
  用例执行，fixtures 的 `rerun.py` 仍只覆盖 legacy 语料（H3/H4 可扩展）。
- fixup profile、非零 addend、Hi/Lo 配对、范围/字段所有权语义（H4）。
- 深层 JSON、重复键、超大输入的完整鲁棒性与模糊测试（H4）。
- 真实同 ISA A/B 包、三个并行工作流、`HE-AC-01`/`02`/`07`/`12` 的完整验收（H5）。
- 迁移全部 104 份定义或 619 个负例；不批量重命名 form。
- 新增指令覆盖；`unsupported-capability` 的运行时路径（H3/H4）。
- 发布任何 `fmp-def/0.2` 包；form ⊆ 包规则用 H2a 的合成 0.2 fixture 测，三个实际包仍是 `0.1`。
- 为发布审计新增 `snapshot_digest` 或等价的全目录摘要；H2 只声称清单、可执行资产与身份，整目录不可变由变更路径门禁与 git 历史承担。
- 从 form 行推导完整、精确的 `enabled_extensions` 需求集合；H2 只证明保守覆盖的
  包含关系（`⋃E_form ⊆ E_package ⊆ E_bundle`），而 `fmp-def/0.1` 下第一项空真
  （`E_form = ∅`），实际证明的是 `E_package ⊆ E_bundle`。精确性需要版本化规则，
  不让构建器凭空补基础 ISA 需求；H2 验收报告必须单列这条限制。
- 把路径层做成可携带的 `std::fs` 调用：no-follow 打开必须由显式路径层或平台原生调用在三平台证明，做不到就停止而非降级。

## 9. 待审决策

| # | 问题 | 建议 | 代价/备选 |
|---|---|---|---|
| O1 | `exports.forms` 用 `{id, path}` 还是裸字符串 | **`{id, path}`**：文件内容与声明逐项绑定 | 裸字符串更短，但交换文件只能靠文件名猜归属 |
| O2 | Bundle spec 目录叫 `bundles/specs/` 还是设计草案的 `bundles/profiles/` | **`specs/`**：避免与 H4 fixup profile 混淆；写进 `ADR-0128` | 沿用 `profiles/` 更贴设计原文，但读者会误以为是 fixup profile |
| O3 | H2 的类型叫 `VerifiedBundle` 还是 `BuiltBundle` | **`VerifiedBundle`**，但文档限定为 H2 的包/闭包/归属验证；运行期能力验证仍属 H3 | `BuiltBundle` 更保守，但与 H1 D1 的命名不一致 |
| O4 | 包级 harness 放哪里 | **`fmp-definition/tests/` + dev-dependencies**，不新增产品 crate | 独立 `fmp-conformance` crate 边界更干净，但 H2 会增加一个 workspace 成员 |
| O5 | 开发工具入口 | **`fmp-definition build\|verify\|digest` 独立 binary**，不改 `fmp` CLI | 加到 `fmp` 子命令更集中，但会扩大 CLI 兼容面 |
| O6 | 包用例格式 | **完整 `fmp/0.1` 文档 + `$standalone` 哨兵**；计划恰好一条 instruction，其 `instruction_id`/`form_id` 必须绑定 case；负例分 `scope:"plan"`/`scope:"form"`，`expect_error.stage` 取 `read`/`bind`/`materialize` 且必须恰是第一个拒绝阶段（`read` 只观察 `plan::read` 的单个诊断，只有 plan 负例可用），form 负例绑定正例基线、只改一个操作数指针、只接受 `bind` 拒绝，并匹配完整 `(code, path)` 集合；**定义身份错配不是 case 种类**：`definition_identity` 只能写 `$standalone` 哨兵，harness 只会替换成正确身份，错误 digest 在 `case-plan-identity` 处就被拒绝，该反例由派生计划绑定测试承担 | 独立 DTO 更短，但会把关键映射留给实现者各自解释；允许任意负例会让错误的 `expected_digest` 冒充操作数边界测试；只留 `bind`/`materialize` 会让读取期拒绝没有合法表示 |
| O7 | lock/sealed 是否提交 | **提交**，CI `--check` 重建；它们是发布产物，不是手写计数 | 只在测试里构建更轻，但发布 bundle 无法审计 |
| O8 | 三个包/forms 是否按 §4 表 | **按表**；已测量：x86 与 rv64 钉 `0.1.0`（前者行漂移，后者目标集合），aarch64 钉 `0.20.0` | 选更多 form 会增加等价面，不增加平台证明力 |
| O9 | `exports.types`/`profiles` 现在预留还是等新格式版本 | **现在预留**：键、`{id, path}` 形状、排序和摘要都定义；非空在 H2 以 `unsupported-asset` 拒绝 | 版本化延后更少代码，但会同时承诺封闭格式和无缝扩展 |
| O10 | H2 如何处理 `requires_capabilities` | **构建期拒绝未知字符串，并要求声明等于推导集合**：只承认 `field-placement/v1`、`integer-domain/v1`，按 slot/placement 结构推导；不符是 `capability-mismatch` | 只做白名单更宽松，但漏报的包会进入已验证快照并让 H3 低估需求 |
| O11 | 新包没有 `legacy_source` 时如何验证 | **包自述 `target_identity`/`definition_format` + 独立身份 + `read` + 包用例**；用一个合成包证明不依赖历史定义 | 强制新包也写 legacy 来源会永久绑定旧目录 |
| O12 | `verify --package` 的 Definition namespace/version 从哪来 | **`monasm-standalone/0.1` 固定函数**：`monasm.standalone.<package_id>` / `standalone+<source digest>`；保留前缀禁止进入 spec | 从 spec 借用会碰撞；从目录推导会随 cwd 漂移 |
| O13 | 包级机器码测试是否强制 | **强制**：每个 form 正例+负例、证据引用、`package_conformance` 执行、`--release-evidence` 检查证据完整性，`--release` 再加闭包 | 只靠 `read` 会放过合法结构里的错误 opcode |
| O14 | 包 target 与 bundle target 的关系 | **包声明保守覆盖、spec 声明选择**；只证明 `⋃E_form ⊆ E_package ⊆ E_bundle`（`fmp-def/0.1` 下 `E_form = ∅`，实际只证明包 ⊆ bundle），高报合法且只缩小可选范围，不裁剪声明；`fmp-def/0.1` 用 `h2-exact-target` 过渡；H3 解除它需要**三件事**：新计划协议、版本化构建规则（`monasm-bundle-spec/0.1` 的拒绝结论永久不变）、以及版本化 bundle 或另一冻结来源提供的逐指令归属/需求证据（检查 `∀i: E_owner(form(i)) ⊆ E_plan`），缺一不可；`fmp/0.1`+`fmp-def/0.1` 相等、`fmp/0.1`+`fmp-def/0.2` 子集两个格子不变。`profile_id` 只是包内名义标签，目标身份是六键 `target.identity`；同名不同 identity 合法，H2 不加 `(profile_id, identity)` 唯一性 | 逐字段相等会把新增扩展族变成对既有包的强制改版；把声明当最小并集会改变作者摘要或错误拒绝合法 bundle；按计划格式重判会重新拒绝已合法的 `fmp-def/0.2` 组合；把 profile 名当全局身份需要中央表且会让同名多义无法表达；只加 `fmp/0.2` 并查 `E_plan ⊆ E_bundle` 会放行 `{rv64i}` 计划选中 `c.addi`，因为 bundle 本就比计划宽，`monasm-bundle/0.1` 又没有归属映射 |
| O15 | form 家族与 target 的一致性 | **通用相等规则** `family(form_id) == target_identity.isa_family`；包格式不列 ISA；第四种家族由 H3 的 reader 支持，不需要改包协议 | 三 ISA 对应表实际全是字符串相等，会迫使 H3 再改一次公共格式 |
| O16 | 证据文件是必需还是可选 | **开发包可选、可发布包必需**；`--release-evidence`/`--release`/spec 选中时要求 `tests/cases.json`、`NOTICE`、`sources`、`oracle.status`、skip 理由和用例证据；`tests/cases.json` 本身被哈希 | 永远可选或只哈希用例证据会让 `release_digest` 不代表完整审核证据 |
| O17 | 已发布包与定义名如何继续演进 | **版本目录是不可变快照**：`packages/<target>/<package_id>/<version>/`；发布路径记入只追加的 `bundles/published.json`，`(package_id, version)` 全局唯一且永久绑定首次 path/摘要；`identities` 永久绑定 `(namespace, version)` 与 `definition_digest`，退役后仍拒绝换字节重发；`bundle_id` 是可移动发布线，不可变的 bundle 内容标签是 `(bundle_id, bundle_digest)`，证据完备的发布身份是 `release_digest`；只有 base 条目在 PR 内不可变，同一 PR 首次创建并登记合法；退役 spec 不删除登记；更新创建同级新目录；旧 spec 未改时旧 lock 原样重建，退役后旧快照/lock 仍可由旧提交重放；发布者另行选择新版本 | 原地覆盖会迫使作者改旧 spec；仅按当前 spec 判断会让退役后的旧目录和旧定义名失去保护；把 `bundle_id` 当不可变身份会拒绝正常的版本推进 |
| O18 | `legacy_source` 迁移等价性 | **行相等 + `definition_format` 相等 + `TargetEq`**：`target_identity` 除 `enabled_extensions` 外逐字段 canonical 相等，扩展按集合相等；不一致是 `legacy-target-mismatch`。包仍用 §1 的规范升序写法，legacy 字节不变 | 只比行会放过 `execution_mode`/`address_width` 被改、但行逐字节相同的包；原始数组相等会与 §1 的规范排序冲突，使冻结的 `rv64/0.6.0` 无法迁移 |
| O19 | 每个 form 的负例覆盖 | **`scope:"form"` + 正例基线 + 单操作数变异 + 仅 `bind` 拒绝 + 诊断落在变异操作数 + 完整诊断集**；`scope:"plan"` 不计覆盖 | 任意负例可被 `expected_digest`/`E-BYTE-001`/`E-SIZE-001` 或根级错误满足，不能证明 form 边界 |
| O20 | 摘要预映像的字节规则 | **canonical record + 域分隔 + 嵌套 `sha256:` 文本 + 跨语言固定向量** | 原始 32 字节/大写 hex 会让 Rust 与 Python 得到不同摘要 |
| O21 | 机器输出投影 | **Level 0/1 各自封闭键集**；Level 0 无 `symbols`；Level 1 仅在 `include_symbol_table` 时含 `symbols` | 共用并集投影会把缺失键和空数组混为一谈 |
| O22 | 单包验证能否证明依赖 | **分开报告 `structure`、`--release-evidence` 与 `dependency_closure`**；无显式闭包时非空依赖是 `unverified`，`--release` 退出 1，闭包验证递归重读全部可达依赖 | 只检查清单形状会把“声明了依赖”当成“依赖已解析” |
| O23 | 写阶段失败与输出目录的边界 | **只保证可检测、不是成功发布**：允许退出 2 留下旧/新混合的 lock/sealed 或临时文件，`--check` 必定拒绝该组合；输出目录是发布者控制的受信任路径，但 `--root` 下每个输出父段都 no-follow（`path-escape`，退出 1）；已提交 lock/sealed 用有界流式比较（1 MiB/80 MiB，越界是 `resource-limit`） | 主张跨文件原子性无法由重命名保证；信任目录却不检查父段会让仓库内链接把写重定向；无界读取会让 `--check` 成为内存攻击面 |
| O24 | 已提交 legacy 快照要不要进入一致性门禁 | **要，但只是等价门禁**：提交副本必须与已校验 sealed 的 `definition` canonical 字节相同（`legacy-snapshot-mismatch`，退出 1）；缺失合法，门禁不重建缓存、不进入任何摘要，读取 ≤ 16 MiB | 只改 legacy 的 opcode 而 `--check` 仍绿，会让文档规定的兼容路径读到发布对里不存在的定义；把快照升成身份输入又会让派生缓存决定发布 |
| O25 | 已发布路径与嵌套 `package.json` 的判定顺序 | **先 base registry（目标分支尖端 `B`）包含、后 head 侧发现**：变更落在 `B` 已登记版本目录内即 `published-package-modified`，其中的新 `package.json` 也属于该快照的修改；只有 `B` 之外的变更才解析最近 head 清单。merge-base 只用于分析祖先关系，不决定「哪些版本已发布」 | head-first 会让更深清单把已发布快照的改动重新归类为未发布候选，绕开不可变约束；用 merge-base 会漏掉分支创建之后目标分支上的发布 |
| O26 | 阶段声明由静态校验还是执行证明 | **两者分开**：`verify --package` 只校验 `stage` 取值、form 只 `bind`、诊断数组形状、指针语法等静态契约；`package_conformance` 执行 `read`/`bind`/`materialize`，证明第一个真实拒绝阶段与完整 `(code, path)` 集合，报告分别记录“静态有效”和“执行已验证” | 让不执行计划的命令声称证明阶段，会让“声明 bind、实际 read 拒绝”的用例通过并留下无效覆盖；把两者合成一个布尔值则无法定位失败性质 |
| O27 | 超过 64 位的寄存器槽位如何取边界 | **按编码宽度 `w` 区分**：`D_reg = ([0, 2^w−1] ∩ [0, 2^64−1]) \ E`；正例取 `D_reg` 的最小/最大成员，`w < 64` 时 `2^w` 可作 form 负例，`w ≥ 64` 用排除值或错误操作数类型；127/192 位包级测试保留 H1 已验证的编码能力 | 把字段宽度当计划域会要求不可表示的 `2^w`，使宽槽位无法给出合法边界证据；缩回 64 位则会静默丢掉 H1 已证明的能力 |
| O28 | 迁移目标的扩展数组按顺序还是按集合比较 | **按集合比较，其余字段严格相等**（`TargetEq`）：`definition_format` 相等；`target_identity` 的 `enabled_extensions` 按集合，其他字段 canonical 相等；包内仍用 §1 的规范升序，legacy 原字节不动 | 原始数组相等与 §1 的规范排序不可同时满足；`rv64/0.6.0` 的 `["rv64i","rv64c"]` 会被 `extension-lexical` 拒绝，而规范写法会被 `legacy-target-mismatch` 拒绝 |
| O29 | 边界正例取原始区间端点还是最终合法域 | **取最终合法域 `D_form = {x ∈ D_Representable, L≤x≤U, x≡0 (mod 2^a)} \ E` 的端点与内部值**；excluded 值作 form 负例，只有可表示的越界值能作 `bind` 负例 | 原始端点可能被排除或不对齐（`rm8h` 的 `0`、`add imm6` 的 `63`），把它当正例会要求非法操作数通过 |
| O30 | 包目录段取完整 `package_id` 还是末段 | **完整 `package_id`**：`packages/<target>/<package_id>/<version>/`，映射是单射；目录段与清单完整 ID 不等是 `path-lexical` | 末段映射非单射，`monasm.x86.crypto` 与 `vendor.x86.crypto` 争同一目录，独立作者必须协调命名；发布后再改规则会撞上已发布目录的不可变性 |
| O31 | 「已发布」以 merge-base 还是目标分支尖端为准 | **目标分支尖端 `B`**：`Published(B) ⊆ Published(H)` 且每个已发布路径字节相等；merge-base 只分析祖先关系 | merge-base 会漏掉分支创建后目标分支上的发布，A 改已发布包的未摘要辅助文件（如 `README.md`）仍被当成候选而放行 |
| O32 | 非空依赖项的格式写在哪 | **写进 `ADR-0128` §1/§4 并给固定向量**：`{package_id, version, source_package_digest}` 三键必需、未知键拒绝、数组按 `(package_id, version)` 升序；§7.0 有非空依赖向量 | 只写在实施计划里，等于让格式语义依赖非规范文档；无向量时键名/可选性改动不会被任何测试发现 |
| O33 | 打开的叶子是否只接受普通文件，类型在哪判定 | **只接受普通文件，类型取自已打开句柄**：中间段必须是目录、叶子必须是普通文件；POSIX 输入打开带 `O_NONBLOCK`，FIFO 在类型判定前不会挂起；非普通叶子是 `not-a-regular-file`（退出 1），所有字节预算都假设普通文件 | 只做 no-follow 不排除 FIFO/socket/设备节点；靠路径 `stat` 或元数据大小判定有 check-then-use 缺口，且 FIFO 无长度、`read` 可永久阻塞，预算无法约束 |
| O34 | 退役 spec 后 lock/sealed 留在树里还是删除 | **与 spec 一一对应，随最后一个 spec 删除**：同一 PR 删除 lock/sealed/legacy，`--all --check` 双向检查一一对应，孤儿是 `orphan-bundle-artifact`（退出 1）；包快照与登记项保留，退役字节由 git 历史保存，不定义归档格式 | 留下未选中的 sealed 没有任何门禁重建，改字节或过期都不可检测，状态语义不明；另立归档格式等于为只被 `git log` 读取的字节增加第二生命周期和第二门禁 |
| O35 | 发布门禁的绿色结果在目标分支前进后是否仍有效 | **只对读到的 `(B_checked, C_checked, mode)` 有效**：`B_checked` 是基线提交 SHA，`C_checked` 是被测候选**树** SHA，`mode` 是合并模式；落地提交 `M` 必须满足 `B_landed = B_checked`、`Tree(M) = C_checked`、`mode(M) = mode`；自动化检查在落地提交上重算，不一致即失败并重跑；用 merge queue（在 merge-group 候选上跑并只合并该候选）或写入记录候选的合并操作；普通 up-to-date required checks 只约束基线新鲜度，不证明落地树相等，不能单独授权；H2a 通过平台 API 读取设置并把端点、生效配置与允许的合并操作写进报告，403/空 ruleset 即未取到证据、本轮失败；post-merge 运行只提供可检测性 | 复用旧绿色结果会让「A 改未发布包的 `README.md`、B 先发布该版本并合入、A 用旧结果合并」改动刚发布的目录，而 A 跑过的检查当时都正确；只做合并后审计能发现却已无法阻止；用提交 SHA 对代替树还会在每种合并模式下都必然失配（临时 test-merge 提交不是最终写入的提交） |
| O36 | `monasm-package/0.1` 的非空 `exports.types`/`profiles` 是否随构建器升级放宽 | **不放宽，`0.1` 永久拒绝**：接受语义属于清单声明的 `package_format`，不属于读取它的工具版本；升级不得把同一份未改动 `0.1` 从拒绝变成接受；H4 必须引入显式新包格式（如 `monasm-package/0.2`），在版本内定义 type/profile 语义、归属/冲突规则、摘要输入和验证；既有键名、`{id, path}` 形状、排序和摘要输入可直接复用，但复用不放宽 `0.1`，与 `h2-exact-target` 在 `monasm-bundle-spec/0.1` 的永久拒绝同理 | 按「新构建器认识该字段」放宽会让重放依赖二进制版本，同一份旧文档的接受语义随工具升级而变；现在就设计完整类型系统会超出 H2/H4 边界 |
| O37 | canonical 定义超过 legacy 快照 16 MiB 读取上限时 build 怎么办 | **省略快照，不失败**：闭包 64 MiB、sealed 80 MiB 都允许更大的 canonical 定义；`build` 依据内存中的 canonical 字节决定，≤ 16 MiB 才写 `bundles/legacy/<bundle_id>/definition.json`，超过则省略并在同一写阶段删除旧副本，仍退出 0 并在人类可读输出中说明；`--all --check` 对缺失本就合法，对手工提交的超限快照仍是 `resource-limit`（退出 1）；因此 build 成功意味着所写树的 `--all --check` 通过。加合成测试：合并定义略高于 16 MiB | 让 build 失败会使 64/80 MiB 预算内的合法闭包不可构建，等于让可选缓存决定有效上限；写超限快照会让 build 产出自己的 check 拒绝的树，失败要到发布者提交后才暴露；引入压缩或归档格式需要新的读取路径和门禁 |

## 10. 证据状态

| 结论 | 依据 | 状态 |
|---|---|---|
| 仓库当前没有 `packages/`、`bundles/`、`fmp-definition` | `Get-ChildItem`/workspace `Cargo.toml` | 高（已核对） |
| `Definition` 已封闭、`bind` 只接收 `Arc<Definition>` | `ADR-0127` §1；`fmp-validate/src/lib.rs` | 高（已读） |
| 定义/正例/负例计数 | `definitions/**/*.json`、`fixtures/**/*.fmp.json` 计数 | 高（已测量） |
| 最新定义版本与 forms 数 | 读取 `0.78.0`/`0.20.0`/`0.6.0` | 高（已测量） |
| 三个包所选 form 都有既有正例 | `X86-P1`、`A64-P1`、`A64-P2`、`RV-P1`、`RV-P2` 的 `form_id` | 高（已核对） |
| 所选 form 行跨版本是否相等 | fixture 钉住版本 vs 最新版本的 canonical JSON 比较 | 高（已测量）：rv64 相等；aarch64 两个 `lsl0` 行三版相等，`lsl12` 在 `0.1.0` 不存在、在 `0.2.0`/`0.20.0` 相等；x86 两个 `mov` 行不等（`0.2` 增加 REX 位放置与 `requires_extensions`），因此 x86 钉 `0.1.0` |
| 钉住版本的目标集合与对照计划的 `target_identity` 一致 | `target_identity` 逐字段比较 | 高（已测量）：x86 `0.1.0` 与 aarch64 `0.20.0` 一致；rv64 `0.6.0` 是 `["rv64i","rv64c"]`，计划是 `["rv64i"]`，`fmp-def/0.1` 要求集合相等，故 rv64 钉 `0.1.0` |
| `fmp_model::canonical` 可复用 | `fmp-model/src/canonical.rs` | 高（已读） |
| `definition_digest` 是 `sha256(canonical(document))`，无域分隔 | `fmp-model/src/definition.rs` line 252 `canonical::canonical_digest(document)` | 高（已读） |
| Level 0 不输出 `symbols`；Level 1 仅在 `include_symbol_table` 时输出 | `fmp-materialize/src/lib.rs` `level_zero_json`/`to_json` 及调用点 | 高（已读） |
| 摘要固定向量跨实现一致 | H2-D8 向量；Python `hashlib` 与 .NET `SHA256` 都得 `1afee65c…` | 高（已双重测量） |
| `fmp-plan` 可用于包用例 | `fmp-plan/src/lib.rs` 有 `PlanBuilder` | 高（已读签名） |
| `check_form_id` 不比较 form 家族与 `target_identity.isa_family` | `fmp-model/src/definition.rs`：`check_form_id` 只匹配已知家族，`bind_target` 独立读取 | 高（已读） |
| 构建器确定性、摘要分层、行相等、字节相等 | 尚未实现 | **未验证** — H2a/H2b 落地时测量 |
| 独立身份、包级用例执行、用例与 plan/form 绑定、负例错误范围、变更路径删除/重命名、保留身份 | 尚未实现 | **未验证** — H2a |
| `tests/cases.json` 进入证据清单、`release_digest` 随用例集改变 | 尚未实现 | **未验证** — H2a |
| 通用 `family(form_id) == isa_family` 规则（不含 ISA 白名单） | 尚未实现；`check_form_id` 只孤立检查家族 | **未验证** — H2a |
| 未知能力/保留资产/双版本/聚合上限 | 尚未实现 | **未验证** — H2a |
| case/证据/spec/lock/registry 的单文件、数量与总量预算，含读取时累计的单包资产预算和单闭包计数器 | 尚未实现 | **未验证** — H2a |
| 版本目录不可变（只保护 base 条目、同一 PR 首次发布合法）、`published-package-modified`、`path-version-mismatch` | 尚未实现 | **未验证** — H2a |
| `bundles/published.json` 追加登记、首次发布、全局 `(package_id, version)` 唯一、退役后仍不可变、三个 registry 错误 | 尚未实现 | **未验证** — H2a |
| 跨 spec `bundle_id`/定义身份唯一 | 尚未实现；`Registry::find` 对两份同 `(namespace, version)` 定义返回 `E-DEF-001`（`fmp-model/src/definition.rs` 843–865） | **未验证** — H2a |
| 无链接/reparse point 的读取边界（打开动作本身 no-follow） | 尚未实现；文字已规定「元数据预检 + 按路径打开」不算满足；`std::fs` 无可携带的 no-follow 打开，三平台可行性未测 | **未验证** — H2a N1 平台门禁 |
| 叶子只接受普通文件，类型在已打开句柄上判定，POSIX FIFO 打开不阻塞 | 尚未实现；没有路径层；`a_fifo_leaf_never_blocks_or_passes` 待写，Linux/macOS 的 FIFO 负例属于 N1 | **未验证** — H2a N1 |
| 派生产物与 spec 一一对应，退役 spec 同时移除 lock/sealed/legacy，孤儿被 `--all --check` 拒绝 | 尚未实现；只有文档规则；`a_retired_bundle_artifact_must_leave_the_tree` 待写 | **未验证** — H2a |
| 标识符/路径段/产物文件名词法在打开前以格式拒绝 | 尚未实现；规则见 `ADR-0128` §1.3，构建器还没有包读取器 | **未验证** — H2a |
| 单一 `LoadedPackage` 贯穿摘要、行/目标比较、逐包 `read` 与合并 | 尚未实现；当前没有包读取路径 | **未验证** — H2a |
| 首次发布无 registry 循环，`build` 先内存校验再写文件且从不写 registry | 尚未实现；只有文档规则。顺序固定为 build → 追加行 → 两项 `--check` → 提交，`--all --check` 要求行已存在 | **未验证** — H2a |
| `--check` 证明 lock+sealed，并对已提交 legacy 快照做等价门禁（缺失合法、不重建缓存、不进摘要） | 尚未实现；只有文档规则；第三个输出写失败的故障注入与 legacy 改动测试待写 | **未验证** — H2a |
| 扩展/能力数组的严格排序与去重写法 | 尚未实现；`extension-lexical`/`capability-lexical` 只是文档中的格式拒绝 | **未验证** — H2a |
| 64 MiB 闭包预算的固定计数集合、每路径一次与越界读取处拒绝 | 尚未实现；没有包读取器 | **未验证** — H2a |
| `enabled_extensions` 是保守覆盖而非最小集合 | 尚未实现；`fmp-def/0.1` form 没有需求键，构建器不存在 | **未验证** — H2a |
| `identities` 定义名历史、永久摘要绑定与 `definition-identity-conflict` | 尚未实现 | **未验证** — H2a |
| 保留的 legacy 定义名（`definitions/*/*.json` 的 `(namespace, version)`）与 `reserved-identity` | 尚未实现；保留集合可从现有 104 个文件读出，实际是 `monasm.isa.{x86,aarch64,riscv}` 系列 | **未验证** — H2a |
| `requires_capabilities` 的推导等式与 `capability-mismatch` | 尚未实现；`bind_forms` 要求非空 `slots`、`bind_slot` 要求非空 `placements`，因此每个合法 `fmp-def/0.1` form 都推导出 `field-placement/v1`；§7.0 的无 slot 字节是摘要预映像，`read` 会先拒绝，不能作为「空集合法」的样例 | **未验证** — H2a |
| 带 `evidence_digest` 的发布形状 `release_digest` 向量 | Python 已按文中字节算出 `e9473871…`/`ba60e8ba…`；Rust 侧尚未复现 | **部分验证** — H2a 补 Rust |
| 值定义用例差分（成员→成员指针、kind 变化→位置、数组长度→数组） | 尚未实现 | **未验证** — H2a |
| form ⊆ 包 ⊆ bundle 的逐包扩展检查与合并前逐包 `read` | 尚未实现；`bind_forms` 把 0.2 form 的 `requires_extensions` 对**合并后**目标检查，这是本规则要补的缺口。`fmp-def/0.1` 下 `E_form = ∅`（`FORM_FIELDS` 拒绝该键），所以 0.1 包只证明 `E_package ⊆ E_bundle`；H3 的子集格子还要逐指令证明 `E_owner(form(i)) ⊆ E_plan`，证据不在 `monasm-bundle/0.1` 里 | **未验证** — H2a（H3 另计） |
| 回滚语义（发布前可删、发布后只退役） | 文档规则；无实现可测 | **specified, not implemented** — H2a |
| `verify --published --check` 独立历史审计与**有界**断言（可执行资产/身份，不含 README/NOTICE/证据用例字节） | 尚未实现 | **未验证** — H2a |
| `legacy_source` 的目标一致性 | 尚未实现；规则是 `definition_format` 相等加 `TargetEq`（扩展按集合） | **未验证** — H2a |
| 迁移包的规范扩展序 `["rv64c","rv64i"]` 与冻结 `rv64/0.6.0` 的 `["rv64i","rv64c"]` 等价 | `definitions/rv64/0.6.0.json` 实测该数组；`check_target` 用 `BTreeSet` 比较；`a_set_equal_target_migrates_a_differently_ordered_legacy_array` 待写 | **未验证** — H2a |
| 边界正例取 `D_form` 的端点，而非原始区间端点 | `x86:mov/rm8h-r8h/legacy` 的 `excluded [0,1,2,3]`、`aarch64:add/w32-w32-w32-imm6-lsl` 的 `excluded 32..63`、`riscv:c.addi/rd-imm6` 的 `excluded [0]` 已读；包级用例待写 | **未验证** — H2a/H2b |
| `scope:"form"` 基线变异、`bind`-only 拒绝、变异操作数诊断、完整诊断集、Level 0/1 精确投影 | 尚未实现；`fmp-materialize` 的 `E-BYTE-001` 反例已确认存在 | **未验证** — H2a |
| 不同包根下的同名相对路径合法，根折叠别名是 `path-lexical` | 尚未实现；没有闭包读取路径 | **未验证** — H2a |
| 声明小写路径不打开大小写不同的磁盘目录项（中间目录与最终文件） | 尚未实现；精确名字查找必须与打开动作同一句柄 | **未验证** — H2a N1 三平台门禁 |
| 名字匹配与打开之间目录项被替换时，只能打开匹配项或以 `path-escape` 拒绝 | 尚未实现；没有路径层，三平台均未实测 | **未验证** — H2a N1 三平台门禁 |
| 单段包根路径（`NOTICE`、`README.md`）是合法 `path` | 文字规则；无读取器 | **未验证** — H2a |
| `payload.reg` 是 `u64`，负寄存器在 `plan::read` 就被拒绝 | `fmp-model/src/plan.rs` `bind_payload` 调用 `bind::u64_in`；`bind.rs` `u64_in` 只接受 `0..=u64::MAX` | 高（已读源码） |
| `check_target` 按**定义**格式选择集合关系 | `fmp-validate/src/lib.rs` `subset_rule = definition_format == DEFINITION_FORMAT_V0_2` | 高（已读源码） |
| `E-OPERAND-004` 带 `target_type`/`value`/`field_bits`；`E-RANGE-004` 带 `target_type`/`value`/`excluded` | `fmp-validate/src/lib.rs` `check_operand` 与 `excluded_diagnostic` | 高（已读源码） |
| modifier 是 `{name, value}`，单改值产生 `…/modifiers/<i>/value` | `fmp-model/src/plan.rs` `bind_modifier` 只闭合这两个键 | 高（已读源码） |
| `plan::read` 只返回一个 `Diagnostic`，所以 `stage:"read"` 的观察集是单元素 | `fmp-model/src/plan.rs` `read` 返回 `Result<Plan, Diagnostic>`；越界值经 `bind::u64_in` 的 `Fault::Domain` 映射为 `E-PLAN-002` | 高（已读源码） |
| 用例 stage 三态与「声明阶段必须恰是第一个拒绝阶段」 | 尚未实现；没有包级 harness。静态契约由 `verify --package`、动态阶段与诊断集由 `package_conformance` 分别验证 | **未验证** — H2a |
| 静态阶段声明不等于真实拒绝阶段：`stage:"bind"` 的用例可被 `read` 拒绝 | 尚未实现；静态检查不执行计划，`a_static_stage_claim_is_not_a_dynamic_rejection` 待写 | **未验证** — H2a |
| 输出父目录 no-follow 与已提交 lock/sealed 的有界流式比较 | 尚未实现；没有写阶段，也没有 `--check` | **未验证** — H2a N1/N4 |
| 中断写入留下新旧混合的 lock/sealed 时 `--check` 必拒绝 | 尚未实现；故障注入测试待写 | **未验证** — H2a |
| 只改已提交 legacy 快照而不改 spec/lock/sealed/源包时，`--check` 以 `legacy-snapshot-mismatch` 拒绝 | 尚未实现；只改了文档中的门禁规则；`a_modified_committed_legacy_snapshot_fails_the_bridge_gate` 待写 | **未验证** — H2a |
| 定义身份错配不能表示为 `monasm-cases/0.1` 用例 | 用例要求 `$standalone` 哨兵且 harness 替换为正确身份，错误 digest 在 `case-plan-identity` 处被拒绝；`plan::read`/`bind` 的既有行为已读 | **specified；reader 行为已读** — H2a 绑定测试 |
| 变更路径先按 base registry 判定包含，嵌套 `package.json` 不能遮蔽已发布祖先 | 尚未实现；没有变更路径映射器；`a_nested_package_manifest_cannot_mask_a_published_ancestor` 待写 | **未验证** — H2a |
| 已发布集合以目标分支尖端 `B` 为准，`Published(B) ⊆ Published(H)` 且已发布路径字节相等 | 尚未实现；反例是 A、B 从 `M0` 分叉、B 先发布、A 只改 `README.md`；`a_concurrent_publish_freezes_the_old_commit_side` 待写 | **未验证** — H2a |
| 发布结论只对读到的 `(B_checked, C_checked, mode)` 有效，基线或落地树不同即不能授权合并 | 尚未实现；仓库的 branch protection/merge queue 设置无法从树内读出，审核期间的 API 读取返回 403、ruleset 查询无结论，这是未取到证据而非没有保护；`a_stale_publication_verdict_cannot_authorize_a_merge` 与 API 证据都待写 | **未验证** — H2a N5 必须补 API 证据 |
| `monasm-package/0.1` 永久拒绝非空 `exports.types`/`profiles`，与构建器版本无关 | 只有文档规则；`a_non_empty_reserved_asset_is_refused_forever_under_0_1` 待写；后续包格式版本未写 | **未验证** — H2a |
| 输入顺序固定为词法校验→no-follow 打开→句柄类型检查→同句柄大小提示→有界读取→解析，元数据大小不是边界 | 尚未实现；没有包读取器；「类型检查后文件增长」由累计计数器覆盖，测试待写 | **未验证** — H2a |
| 超过 16 MiB 的 canonical 定义由 `build` 省略快照并删除旧副本，`--all --check` 通过；手工超限快照是 `resource-limit` | 尚未实现；闭包内 64/80 MiB 预算允许该尺寸；`a_build_never_writes_a_snapshot_it_cannot_read` 待写 | **未验证** — H2a |
| 包目录段等于完整 `package_id`，两个同末段 ID 可同版本共存 | 词法上 `pseg` 已允许点号（`ADR-0128` §1.3）；映射器不存在；`a_package_path_keeps_the_full_package_id` 待写 | **未验证** — H2a |
| 非空依赖对象是封闭三键结构，固定向量 `637edab0…` | 已用 Python `hashlib` 与 .NET `SHA256` 对文中字节算出同一值；Rust 侧复现待写；`a_dependency_object_is_closed_and_keeps_its_vector` 待写 | **部分验证（Python/.NET）** — H2a 补 Rust |
| `verify --package` 执行 `definition::read`、不执行 `plan::read`/`bind`/`materialize` | 规则已写入 `ADR-0128` §9.1 与本文 §5.3；命令不存在；`verify_package_reads_the_definition_not_the_plan` 待写 | **未验证** — H2a |
| 目标兼容矩阵保持 `fmp/0.1`+`fmp-def/0.1` 相等、`fmp/0.1`+`fmp-def/0.2` 子集，新计划协议**加版本化构建规则、再加逐指令归属来源**才加格子 | 前两格可从 `check_target` 读出；新计划格子、构建规则与归属映射都不存在；`monasm-bundle-spec/0.1` 尚无 Builder；`a_target_subset_requires_per_form_ownership` 待写 | **部分验证** — H3 门禁 |
| `profile_id` 是包内名义标签，身份是六键 `target.identity` | 文字规则；没有 spec 或 bundle 可测，也不新增跨 spec 唯一性 | **specified, not implemented** — H2a |
| 边界证据只在 `D_Representable` 内取，寄存器用 `D_reg = ([0, 2^w−1] ∩ [0, 2^64−1]) \ E`，且只记录诊断实际字段 | 尚未实现；三个包与用例不存在；`w ≥ 64` 的公式与 H1 宽字段证据一致 | **未验证** — H2a/H2b |
| 127/192 位寄存器槽位在包级协议中仍可 `bind` 与 `materialize` | `prototype/crates/fmp-materialize/tests/he1_wide_register.rs` 已对 64/127/128/192 位调用 `bind`/`materialize` 并校验字节；包级测试待写 | **H1 已测量；H2 包级测试未实现** — H2a |
| `structure`/`--release-evidence`/`dependency_closure` 三态分离与传递闭包重读 | 尚未实现 | **未验证** — H2a |
| 证据完整性、`evidence_digest` 与 release 摘要分层 | 尚未实现 | **未验证** — H2a（机制）；H2b 只增加资产 |
| 解析前 JSON 深度拒绝 | 尚未实现；H0 探针只证明现有递归解析器会栈溢出 | **未验证** — H2a 加迭代预算 |
| 深层 JSON 鲁棒性 | H0 探针已测栈溢出；H2 不改 `fmp` 解析器 | **未验证/不在 H2** — H4 |
| 完整的 per-package CI matrix | 未实现；H2 只做单命令 | **未实现** — `ADR-0130`/H5 |

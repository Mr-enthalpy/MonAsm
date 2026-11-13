# H2 实施计划：目标包作者层与确定性定义构建

- 状态：**待审提案**（2026-11-14；同日按三轮审计 P1/P2 修订）。规范决策见
  `docs/adr/0128-package-and-bundle-contract.md`，该 ADR 仍为 `proposed`；
  评审合并前本文和 ADR 都不是冻结依据。本文保留为实施计划与验收映射。
  **H2 尚未实现，本文不把任何 H2/H3/H4/H5 项目算作已完成。**
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
packages/<target>/<package>/<version>/
  package.json
  forms/*.json
  tests/cases.json
  evidence/manifest.json
  NOTICE
  README.md
          |
          |  fmp-definition build --spec <spec> --root <repo-root>
          v
bundles/specs/<bundle>.json          # 显式选择，不是扫描结果
bundles/locks/<bundle>.lock.json     # 精确闭包 + 摘要
bundles/sealed/<bundle>.bundle.json  # 扁平化定义快照

执行期（H2 不改）
  plan + Arc<Definition> -> bind -> ValidatedPlan -> materialize
```

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

- `fmp-definition` 的**产品依赖**只有 `fmp-model`；它不依赖 `fmp-validate` 或
  `fmp-materialize`。
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
- `expect_error` 是封闭对象：`stage`（`bind`/`materialize`）和非空的
  `diagnostics` 数组；每项恰好 `code`/`path`，按 `(path, code)` 排序且唯一。
  观察到的全部 `(code, path)` 对排序后必须与声明数组**完全相等**；多一条、
  少一条或只匹配其中一条都失败（`case-diagnostics-mismatch`）。`materialize`
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
  `mutates` 指针语法与计划差分、证据引用和哈希；它不执行 `bind`/`materialize`
  （产品依赖仍只有 `fmp-model`）。
- `package_conformance` 测试执行所有用例：替换独立身份 → `plan::read` →
  `bind` → `materialize`，比较 §4.2.1 的精确机器输出投影；负例断言完整的
  `(code, path)` 诊断集合，而不是只找一条符合预期的错误。
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

- 叶包路径：`packages/<target>/<package>/<version>/`，`target` 是目录名
  （`x86_64`、`aarch64`、`rv64`），不是 form ID 前缀；`<version>` 必须等于
  清单 `version` 和 spec 的 `packages[].version`，否则 `path-version-mismatch`。
- 版本目录是**已发布快照的不可变边界**：一旦任何已提交 spec 列出该路径，
  目录内任何文件（含 `package.json`、`NOTICE`、`README`、`evidence/`）都不得
  新增、修改、重命名或删除；违反是 `published-package-modified`（退出码 1）。
  新 form 或修正必须创建同级新版本目录，旧目录原样保留，旧 spec/lock 仍能
  `verify --all --check` 重建。发布者另行决定何时把 spec 指向新版本。删除 spec
  只退役发布，不删除快照；H2 不提供归档/删除工具。
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
- 有 `legacy_source` 时，迁移等价性不止是行相等：包的 `definition_format` 和
  完整 `target_identity` 必须与钉住文档的对应值 canonical 相等（`isa_family`、
  `isa_variant`、`execution_mode`、`enabled_extensions`、`byte_order`、
  `address_width` 及 legacy 目标实际声明的字段）。不一致是
  `legacy-target-mismatch`（退出码 1），在合并文档交给 `read` 之前拒绝。历史
  文件仍不是目标权威；包自述目标，legacy 只用于证明迁移保持语义。把
  `execution_mode` 改成 `"32"` 或 `address_width` 改成 32、同时保留逐字节相同
  form 行的反例，必须被这条检查拒绝。
- `exports.forms` 用 `{id, path}` 而不是裸字符串：文件内容里的 `form_id` 必须
  等于声明的 `id`；交换两个文件不会静默改变归属。
- `exports.forms` 必须按 `id` 严格升序，重复 `id` 拒绝；这样清单只有一种写法，
  重排不是「另一个合法清单」。
- `dependencies` 的每项是 `{package_id, version, source_package_digest}`，三项
  都必须精确匹配；数组按 `(package_id, version)` 严格升序。没有 `latest`、没有
  semver 范围、没有隐式升级。
- spec 里的 `source_package_digest` 是作者输入，不是构建器补全。新包先用
  `fmp-definition digest <package-path>` 得到该值，再写进 spec；`build` 发现
  不匹配即拒绝，不自动改写 spec。
- `requires_capabilities`：H2 只承认已经由 `fmp-def/0.1` 和 H1 执行的
  `field-placement/v1`、`integer-domain/v1`；任何其他字符串在 build/verify
  时以 `unsupported-capability` 拒绝（退出码 1）。H2 不做运行时能力协商；
  拒绝未知声明是为了不让内核不理解的包进入已验证快照。
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
  `case-evidence-mismatch`。`--release` 缺清单是 `evidence-incomplete`，绝不
  降级为开发模式。结构、资产、`read` 和用例契约两种模式完全相同，只有这一组
  发布证据不同。
- 可发布包（被任一已提交 spec 选中，或以 `--release` 校验）还要求：`files`
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
  `expected_digest`、布局或目标，但不计入 form 覆盖。`scope:"form"` 必须
  绑定同文件、同 form/instruction 的正例 `baseline_case_id`，并给出单个
  `mutates` 操作数指针；基线和用例计划的 canonical 差分必须恰好是
  `{mutates}`，否则 `case-baseline-invalid`/`case-mutation-mismatch`。
- `expect_error` 恰好是 `stage` 和非空 `diagnostics`；`diagnostics` 每项恰好
  `code`/`path`，按 `(path, code)` 排序且唯一。harness 比较完整的
  `(code, path)` 集合，多/少/重复都失败（`case-diagnostics-mismatch`）；
  `materialize` 只接受 `PostEncodeAssertion`，`Internal`/`HostFailure` 是
  `case-materialize-fault`。form 负例的所有 path 必须在 `/instructions/0`
  范围内，否则 `case-error-scope`；plan 负例不限。
- 每个用例的 `evidence`（`kind`、`path`、`sha256`）在有证据清单时必须与
  `evidence/manifest.json` 一致；开发模式没有清单时直接核对 case 自带的
  `sha256` 与原始文件字节。没有文件是 `missing-cases`，没有
  `scope:"form"` 负例是 `uncovered-form`，证据对不上是
  `case-evidence-mismatch`（均退出码 1）。这个文件是唯一发现点，不引入中央
  测试列表。
- `verify --package` 使用 §2.4 的独立身份；包级 conformance 用同一身份执行
  用例。`verify --package` 只校验用例契约（含 `scope`、基线链接、`mutates`
  指针与基线/用例计划差分、诊断数组形状和错误范围），不执行
  `bind`/`materialize`；执行在 `fmp-definition/tests/` 的
  `package_conformance` 中完成。
- `cases_format` 只接受 `monasm-cases/0.1`；其他值在解析用例前以
  `case-format-unsupported` 拒绝（退出码 1）。`0.1` 只承诺 H2 的模型：单个
  `fmp/0.1` 计划、恰好一条 instruction、有操作数的 form 和操作数表面变异。
  H3 的 `fmp/0.2` 和零操作数 form、H4 的多指令/配对 fixup 场景必须引入
  `monasm-cases/0.2`（或显式场景格式）及自己的覆盖规则，不能把 `0.1` 静默
  重解释。case 格式版本与 `package_format` 独立，新增版本不重命名包，也不改
  `source_package_digest`。
- `exports.types` / `exports.profiles`：可选的 `{id, path}` 列表，文件和
  `exports.forms` 一样按 `id` 严格排序，每个文件只放一个 type/profile 对象，
  其 `type_id`/`profile_id` 必须等于声明的 `id`。它们已进入封闭键集和源摘要，
  但 H2 不执行也不输出这些资产，非空列表以 `unsupported-asset` 拒绝。缺省与
  空列表都表示零资产，但它们是不同的清单、得到不同的源摘要；lock 钉住实际
  发布的那一种写法。**冻结的是外层身份、排序、摘要输入和拒绝语义**；文件内部
  的 type/profile 语义（共享类型、组合 profile）是 H4 的提案，若 H4 需要不同
  结构，必须通过新格式版本演进，不能把 H2 的占位形状当作已验证语义。
- 每个 `forms/*.json` 只放一个 form 对象；迁移包里它就是 legacy 定义里的
  对应行，新包里它由包自己的用例和 oracle 证明。这样归属、摘要和差异都可以
  逐行审查。

### H2-D3 路径边界

- 所有清单路径必须是包内规范化相对路径，使用 `/`。
- spec 的 `packages[].path` 相对于 `--root`；解析后仍必须位于 `--root` 之下。
- `legacy_source.isa` 和 `legacy_source.version` 在拼成
  `<root>/definitions/<isa>/<version>.json` 之前也按路径组件校验：`isa` 匹配
  `^[a-z0-9_]+$`，`version` 匹配 `^[0-9]+(\.[0-9]+)+$`；含 `/`、`\`、`..`、
  整段 `.`、盘符、URL scheme 或 NUL 的值直接拒绝，不做「规范化后合法」的修补。
- 拒绝绝对路径、`..`、空段、`.`、反斜杠、NUL、URL scheme、盘符。
- 拒绝符号链接逃逸：构建器在打开文件前检查 `canonicalize()` 结果仍位于包根
  之下；Windows 上同时拒绝 reparse point 逃逸。
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
      "path": "packages/x86_64/mov-register/0.1.0",
      "source_package_digest": "sha256:..."
    }
  ]
}
```

- `packages` **就是完整闭包**，不是「根集合」。构建器只读取这里列出的
  `path`，从不扫描 `packages/` 目录；依赖边只用于校验，不用来发现新包。
- 每个 `path` 的末段必须同时等于 spec 的 `version` 和包清单的 `version`；
  不一致是 `path-version-mismatch`（退出码 1）。已发布版本目录不可变
  （H2-D1）：普通包更新不会改写旧 path，旧 spec/lock 仍可重建。
- `target.identity` 的结构字段（`isa_family`、`isa_variant`、`execution_mode`、
  `byte_order`、`address_width`）和 `definition_format` 必须与**每个包自己声明
  的**对应字段相等；它们不再从包钉住的 legacy 定义推导。`fmp-def/0.1` 与
  `fmp-def/0.2` 的 form 行不是同一种对象：0.2 的 x86 行多出 REX 位放置和
  `requires_extensions`，而 0.1 的 reader 会因未知键拒绝 0.2 行；反之 0.1 行
  放进 0.2 文档会缺必需键。构建器必须让 spec、包自述和行三者互相一致；混合
  格式的闭包直接拒绝，不做隐式转换，显式版本化转换属于 H3。
- **`enabled_extensions` 是需求，不是完整配置（第一轮 P1-3）。** 包的列表表示
  「这个包的 rows 至少需要哪些扩展」，spec 的列表表示「这个 bundle 选中了哪些
  扩展」。一般规则是包需求 ⊆ bundle 选择；其他目标字段仍相等。这样新增一个
  `rv64c` 包时，`rv64i` 算术包的清单不需要改，源摘要不变，不会把无关包重新
  发布一次。
- H2 的过渡规则：`fmp-def/0.1` 的 `bind` 仍按集合相等比较
  `enabled_extensions`，所以 `definition_format == fmp-def/0.1` 时额外要求
  包需求与 spec 选择**完全相等**（`h2-exact-target`）。这不是永久包契约；
  `fmp-def/0.2` 已按子集处理。H3 必须在计划侧定义同样的兼容规则，才能解除
  `h2-exact-target`；该规则必须在 H5 并行扩展演练之前生效，否则先修订 ADR，
  不得直接开始 H5。H2 不声称这个等号是最终组合规则。
- `target.profile_id` 必须与每个包的 `target_profile` 一致，否则构建失败。
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
- 普通作者路径不要求先改全局 spec：未选中包跑 `verify --package`（结构）和
  `package_conformance` 即可；`--release` 对非空依赖要求 `--closure <lock>`，
  否则是 `dependency-unverified`（退出码 1）。作者可以在自己的 PR 里带一个
  精确的本地 lock 来跑 release；只有被发布 spec 选中时才由 `--all --check`
  以 spec 闭包做完整 release 校验。H2 的三个包都没有依赖。
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
  重排是拒绝而不是第二种写法；spec 的包列表顺序和目录发现顺序不参与摘要，
  构建器先按 `(package_id, version)` 排序闭包。

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
字节，不是某个平台的序列化。

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
身份与审计证据身份因此分开，发布时仍可通过 lock 追踪二者。上面的 release
向量故意不带 `evidence_digest`（它用的是 §7.0 的开发形状），只固定 preimage
形状和缺键写法；发布 lock 的 `release_digest` 会因它而不同。

### H2-D9 spec、lock、sealed bundle

- `bundles/specs/<bundle>.json`：发布者写的显式选择（`monasm-bundle-spec/0.1`）。
  封闭键恰好是 `bundle_format`、`bundle_id`、`target`、`definition_format`、
  `namespace`、`version`、`packages`；`target` 恰好 `profile_id`/`identity`，
  `packages` 每项恰好 `package_id`/`version`/`path`/`source_package_digest`。
- `bundles/locks/<bundle>.lock.json`：构建器生成的 `monasm-lock/0.1`。封闭键
  恰好是 `lock_format`、`bundle_id`、`definition_format`、`namespace`、
  `version`、`target`、`bundle_digest`、`definition_digest`、`release_digest`、
  `packages`、`builder`；包项恰好 `package_id`/`version`/`path`/
  `source_package_digest`/`evidence_digest`。`builder` 恰好 `name`/`version`
  和可选 `build`，没有 build 标识时省略键，绝不写 `null`。`--check` 比较
  **去掉 `builder` 后的 canonical 字节**；builder 只做形状检查和打印。
- `bundles/sealed/<bundle>.bundle.json`：扁平化的 `monasm-bundle/0.1`，封闭键
  恰好 `bundle_format`、`bundle_id`、`definition_format`、`definition_digest`、
  `bundle_digest`、`definition`、`packages`；`definition` 是 §9 的合并定义
  文档，包项恰好 `package_id`/`version`/`source_package_digest`。没有 `path`、
  `builder`、`release_digest` 或 `evidence_digest`，因此逐字节比较，没有排除键。
- 三者的未知键/重复键都拒绝；spec、lock、sealed 的完整最小样例和
  `bundle_digest`/`release_digest` 固定向量见 `ADR-0128` §8.2。
- `bundles/legacy/<bundle>/definition.json`：构建器额外输出的纯定义文档，供
  现有 `fmp materialize <plan> --definitions <dir>` 读取。它不是 sealed
  bundle：`Registry::load_dir` 会递归读取目录下所有 `.json` 并调用
  `definition::read`，sealed 的 bundle 信封会被拒绝。这个快照是开发期桥，
  不是发布身份；`--check` 可以重建它。
- lock 与 sealed bundle 作为发布产物提交；CI 用 `verify --check` 重建并比较
  字节。它们不是手写计数，也不是普通扩展作者必须编辑的文件。
- `bundles/specs/` 采用本文的目录名，而不是设计草案的 `bundles/profiles/`：
  避免与 H4 的 fixup profile 混淆。这个改名写进 `ADR-0128`。

### H2-D10 错误与退出码

`fmp-definition` 是开发期工具，不是 `fmp` CLI 的替代品。它返回自己的
`BuildError` 枚举，不新增 `E-*` 错误码，也不伪装成 `fmp/0.1` 诊断：

| 类 | 例子 | 退出码 |
|---|---|---|
| 确定性拒绝 | 清单形状（必需/可选键）、空 forms、路径越界、版本目录与版本不符、已发布快照被改、依赖缺失/摘要错/环、同一 package ID 双版本、归属冲突、未知 capability、非空 reserved asset、闭包聚合上限、证据不完整/不符、用例缺失/未覆盖、用例格式不支持、用例与计划/form 绑定、基线或变异不符、完整诊断集不符、投影键集错误、legacy 目标不一致、无法映射的包路径、定义被 `read` 拒绝、资源上限 | 1 |
| 宿主/IO/内部 | 文件读失败、锁文件不可写、内部不变量破坏、conformance 遇到 `Internal`/`HostFailure` | 2 |
| 成功 | 构建或校验通过 | 0 |

`BuildError` 的变体名包括 `unsupported-capability`、`unsupported-asset`、
`version-conflict`、`aggregate-limit`、`legacy-row-mismatch`、
`legacy-target-mismatch`、`evidence-mismatch`、`evidence-incomplete`、
`missing-cases`、`uncovered-form`、`empty-package`、`case-evidence-mismatch`、
`case-plan-identity`、`case-form-mismatch`、`case-error-scope`、
`case-format-unsupported`、`case-baseline-invalid`、`case-mutation-mismatch`、
`case-diagnostics-mismatch`、`case-expect-shape`、`form-family-mismatch`、
`reserved-identity`、`path-version-mismatch`、`published-package-modified`、
`unmapped-package-path`、`dependency-unverified`、`dependency-mismatch`；它们
不是 `fmp/0.1` 诊断码。`case-materialize-fault` 是 conformance harness 对意外
`Internal`/`HostFailure` 的命名，退出码 2，绝不算通过。

`fmp` CLI 的 0/1/2 语义不变。H2 不把包构建错误送进 `bind` 的诊断数组。

### H2-D11 资源上限

H2 只加构建器自己的有界输入，不声称解决深层 JSON：

- 单个 manifest ≤ 1 MiB；
- 单个 form/type/profile 文件 ≤ 1 MiB；
- 单个 `tests/cases.json` ≤ 16 MiB；单个 `evidence/manifest.json` ≤ 1 MiB；
  单个 spec 或 lock ≤ 1 MiB；行比较读取的钉住 legacy 定义文件 ≤ 16 MiB；
- 每个包导出 forms ≤ 1024；每个包声明资产 ≤ 2048；每个包 cases ≤ 4096；
  每个包证据文件 ≤ 4096；
- 每个包的 manifest 加声明资产字节累计 ≤ 16 MiB，读取时累计检查（见下）；
- 每个包证据总字节 ≤ 16 MiB；
- 闭包内包数 ≤ 1024；闭包总包字节 ≤ 64 MiB；
- 闭包内声明资产总数 ≤ 65 536；闭包内 cases 总数 ≤ 65 536；闭包内证据文件
  总数 ≤ 65 536；
- 单条路径 ≤ 1024 字节；依赖深度 ≤ 64；
- manifest/form/type/profile/case/evidence/spec/lock 的 JSON 嵌套深度 ≤ 64。

1024 forms 至少需要 2048 个用例（每个 form 一正一 form 负），4096 的上限给
plan 负例留出余量；16 MiB 的用例文件在最大规模下约合每例 4 KiB，足以容纳完整
的单 instruction `fmp/0.1` 文档和期望。原先的 1 MiB 连几百个 form 的强制用例
都装不下。

超限是确定性拒绝（退出码 1）。构建器先从文件元数据检查长度，再打开读取；
因此一个未被 spec 选中的包也不能靠“没有闭包总字节”绕过 case/证据预算。
**单包资产预算是累计的，不能只看每文件元数据**：构建器用有界 reader 读取
manifest 和每个声明资产，按实际读出的字节累加，下一次读取会超过 16 MiB 时
立即拒绝；元数据只是提示，文件可能在 `stat` 与 `read` 之间增长，符号链接/
reparse point 也可能报告不同大小。读到剩余预算为止，短读或超读都是
`resource-limit`（退出码 1）。计数器按包重置，不是闭包总量。反例：2048 个
各 1 MiB 的文件通过每个单文件检查，却迫使单包读取 2 GiB。

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
- `fmp` CLI 不改；构建器额外输出 `bundles/legacy/<bundle>/definition.json`，
  现有 `--definitions <dir>` 可以读取它；sealed bundle 本身不是定义文档。
- `fmp-def/0.1` 行不在构建器里隐式转换成 `0.2`；混合格式闭包拒绝，显式
  版本化转换属于 H3。
- `definitions/` 一个字节不动；`check_definition.py` 继续只检查 legacy 定义和
  中心表，不扩展成包检查器。

## 4. 三个包

H2 每个 ISA 选一个代表性纵向切片，不迁移全部 forms：

| 目标 | 包 | 导出 forms | 对照正例 | 钉住的 legacy 源 | 覆盖点 |
|---|---|---|---|---|---|
| x86_64 | `packages/x86_64/mov-register/0.1.0/` | `x86:mov/rm-r64/legacy`、`x86:mov/r64-rm/legacy` | `X86-P1` | `x86_64/0.1.0` | 两个方向、REX/legacy 放置、寄存器槽位 |
| aarch64 | `packages/aarch64/add-immediate/0.1.0/` | `aarch64:add/x64-x64-x64-lsl0`、`aarch64:add/x64-imm12-lsl0`、`aarch64:add/x64-imm12-lsl12` | `A64-P1`、`A64-P2`（两个版本） | `aarch64/0.20.0` | 寄存器三元、imm12、`sh` 由 form ID 固定 |
| rv64 | `packages/rv64/integer-alu/0.1.0/` | `riscv:add/rd-rs1-rs2`、`riscv:addi/rd-rs1-imm12` | `RV-P1`、`RV-P2` | `rv64/0.1.0` | 三寄存器、imm12、整数域 |

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
- 包的 `enabled_extensions` 是**该包的扩展需求**，不是 bundle 的完整目标
  （H2-D4、第一轮 P1-3）。三个 H2 包的格式都是 `fmp-def/0.1`，所以本轮额外
  要求需求与 spec 选择完全相等（`h2-exact-target`）；这是过渡检查，不是未来
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
5. 断言包的 `definition_format` 和完整 `target_identity` 与 legacy 文档对应值
   canonical 相等。目标由包自述，但迁移包必须证明自述没有改变来源语义；不一致
   是 `legacy-target-mismatch`（退出码 1），在合并文档交给 `read` 之前拒绝。

没有 `legacy_source` 的包跳过 1–3 和 5；`verify --package` 检查清单、路径、
导出、`read` 和自述目标，机器输出由包自己的 case 证明。H2 至少用一个合成包
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
- 负例必须声明 `scope`。`scope:"plan"` 可针对错误的 `expected_digest`、布局
  或目标，但不计覆盖；`scope:"form"` 必须绑定同 form/instruction 的正例
  `baseline_case_id`，只改一个 `mutates` 操作数指针，且基线/用例 canonical
  差分必须恰好等于该指针（`case-baseline-invalid`/`case-mutation-mismatch`）。
  `expect_error.diagnostics` 必须与观察到的完整 `(code, path)` 集合相等
  （`case-diagnostics-mismatch`）；`materialize` 的 `Internal`/`HostFailure`
  是 `case-materialize-fault`。form 负例的 path 必须在 `/instructions/0`
  范围内（`case-error-scope`），plan 负例不限。
- 每个导出 form 至少一个正例和一个 `scope:"form"` 的非法邻域（立即数越界、
  错误寄存器宽度、错误 target type、非法 modifier 等，由 `bind` 或
  `materialize` 拒绝）。没有用例文件是 `missing-cases`，没有 form 邻域负例是
  `uncovered-form`。
- 每个用例的 `evidence` 必须是 `oracle` 或 `manual-derivation`。没有证据清单
  的开发包直接核对 case 自带的 `sha256` 与原始文件字节；清单存在时以清单为准；
  可发布包还要求 `files` 列出 `tests/cases.json` 本身、`NOTICE`、每个用例证据、
  至少一条 `sources`、完整的 `oracle.status` 和 skip 理由（H2-D2、`--release`）。
  哈希覆盖原始字节，CRLF/LF 或空白改变也是改变。
- 修改 `tests/cases.json` 但不更新 evidence manifest：`evidence-mismatch`；
  更新 manifest 后：`evidence_digest`/`release_digest` 改变，
  `source_package_digest`/`definition_digest` 不变。这是第二轮 P1-1 的验收测试。
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
| 包结构已验证 | `verify --package` 通过清单、资产、用例与证据检查 | 声明的依赖已经解析 |
| 依赖闭包已验证 | 每个依赖都按 ID、版本和摘要匹配显式闭包 | H2 的包有依赖 |
| 包级机器码测试通过 | `package_conformance` 与声明期望和完整诊断集一致 | 独立 oracle 已运行 |
| 证据文件可追溯 | 文件存在且摘要一致 | 记录的 oracle 结果真实 |
| 独立 oracle 已复验 | 本机实际重跑外部工具并核对 | H2 对新包做到这一项 |

前五项不推出最后一项。H2 只做前五项加声明的用例执行；报告不得写成「本机重算」。

H2 不提交第二个 x86 真实包；`HE-T16` 的 A+B/B+A 顺序性质用临时测试包证明，
真实 A/B 工作流留给 H5。

## 5. 测试计划

### 5.1 构建器

| 测试（拟名） | 断言 | 对应 |
|---|---|---|
| `the_same_inputs_build_to_the_same_bundle_digest` | 两次构建、两个临时目录、不同创建顺序 → 同一 `bundle_digest` 和同一 sealed 字节 | `HE-T05` |
| `reversing_package_order_does_not_change_the_bundle` | spec 中包顺序 A,B 与 B,A → 同一闭包、同一摘要 | `HE-T16`（H2 部分） |
| `an_unselected_package_does_not_change_an_old_bundle` | 包根新增一个未列出的包（即使其清单损坏）→ 旧 spec 的 lock/bundle 不变；构建器从未打开它 | `HE-AC-05`（构建期部分） |
| `a_dependency_outside_the_spec_is_refused` | 依赖指向列表外的 `(package_id, version)` → 确定性拒绝，不扫描目录补齐 | `H2-D5`、`HE-T08` |
| `the_spec_lists_every_package_in_the_closure` | 删掉一个被依赖的列表项 → 拒绝；列表项顺序不影响结果 | `H2-D5` |
| `a_dependency_must_match_its_exact_digest` | 改依赖内容保留版本 → 摘要不匹配，退出 1 | `HE-T08` |
| `a_dependency_cycle_is_refused` | A→B→A → 确定性拒绝，不递归溢出 | `HE-T08` |
| `the_same_dependency_reached_twice_is_loaded_once` | 菱形闭包 → 共享包在 spec 中只列一次，两条依赖边都校验通过，归属表无重复 | `HE-AC-04` |
| `two_packages_exporting_the_same_form_conflict` | 两包同一 `form_id`，内容相同也失败 | `HE-T07`、`HE-AC-09` |
| `a_package_path_cannot_escape_its_root` | `../`、绝对路径、符号链接逃逸 → 拒绝 | `H2-D3` |
| `the_manifest_is_closed` | 未知键、必需键缺失、重复键 → 拒绝；可选键缺失 → 接受 | `INV-07` |
| `an_empty_forms_list_is_refused` | `exports.forms: []` → `empty-package`，在合并文档交给 `read` 前拒绝；类型/profile-only 包不走 H2 | `ADR-0128` §1、第四轮 P2-3 |
| `an_unknown_case_format_is_refused` | `cases_format: "monasm-cases/0.2"` 或其他值 → `case-format-unsupported`；`0.1` 只接受单指令、有操作数的 `fmp/0.1` 计划 | `ADR-0128` §9.2、第四轮 P2-1 |
| `an_unknown_capability_is_refused` | `requires_capabilities` 出现白名单外字符串 → `unsupported-capability`，退出 1 | `H2-D2`、`HE-T09`（H2 构建期部分） |
| `a_non_empty_reserved_asset_is_refused` | `exports.types`/`profiles` 非空 → `unsupported-asset`，不静默忽略 | `H2-D2`、`H2-D6` |
| `two_versions_of_one_package_id_conflict` | 同一 `package_id` 两个版本、导出不相交 → `version-conflict` | `H2-D5` |
| `a_package_without_legacy_source_is_verified_from_its_own_target` | 合成包无 `legacy_source` → 按自述目标、`read` 和用例通过，不需要 spec | `H2-D2`、`H2-D4`、§4.1 |
| `a_file_form_id_must_match_its_export` | 交换两个 form 文件 → 归属不匹配，拒绝 | `H2-D2` |
| `the_target_profile_must_match_the_spec` | 包的 `target_profile` 与 spec 不一致 → 拒绝 | `H2-D4` |
| `the_standalone_identity_is_derived_from_the_package` | 复制包到不同目录、换 cwd、无 spec → 同一 `monasm.standalone.*`/`standalone+*` 和同一独立 `definition_digest` | `H2-D5`、§2.4、第一轮 P1-1 |
| `a_standalone_identity_cannot_be_written_into_a_spec` | spec 的 `namespace`/`version` 使用保留前缀 → `reserved-identity`，退出 1 | `H2-D5`、§2.4 |
| `a_form_family_must_match_the_package_target` | `isa_family: aarch64` 的包导出 `x86:*` → `form-family-mismatch`，在 `read` 之前拒绝 | `H2-D4`、第二轮 P1-3 |
| `the_family_rule_is_equality_not_a_package_whitelist` | 合成包声明 `isa_family: loongarch` 并导出 `loongarch:*` → 通过包层家族检查，随后只被现有 `definition::read` 的家族集合拒绝；错误来自 reader，不是包格式白名单 | `H2-D4`、第二轮 P1-3 |
| `a_package_requirement_is_a_subset_of_the_bundle_target` | `fmp-def/0.2` 合成包需求 `["rv64i"]`、spec 选择 `["rv64i","rv64c"]` → 接受；缺少 `rv64i` → 拒绝 | `H2-D4`、第一轮 P1-3 |
| `fmp_def_0_1_keeps_the_transitional_exact_target` | `fmp-def/0.1` 包需求与 spec 选择不等（即使是子集）→ `h2-exact-target`，退出 1 | `H2-D4`、第一轮 P1-3 |
| `the_case_file_is_required_and_covers_every_form` | 无 `tests/cases.json` → `missing-cases`；form 无正例或无 `scope:"form"` 负例 → `uncovered-form` | `H2-D2`、§4.3、第二轮 P1-2 |
| `a_case_must_bind_its_declared_form_to_the_plan` | case 声明 form B，计划只含 form A、空计划或多于一条 instruction、`instruction_id` 不一致 → `case-form-mismatch`，不进入执行 | `H2-D2`、`ADR-0128` §9.1、第二轮 P1-2 |
| `a_case_negative_must_target_the_declared_instruction` | 负例 `path` 是根级或 `/sections/...`（例如错误 `format_version`）→ `case-error-scope`；`scope:"form"` 的 `mutates` 指向 `expected_digest`、多改一个字段或没有实际改动 → `case-mutation-mismatch`；两者都不计为该 form 的覆盖 | `H2-D2`、`ADR-0128` §9.1、第三轮 P1-3 |
| `a_case_evidence_must_be_listed_and_hashed` | 有证据清单时，用例证据未列入或哈希不符 → `case-evidence-mismatch`，退出 1 | `H2-D2`、第二轮 P1-2 |
| `a_development_package_verifies_without_an_evidence_manifest` | 有 forms/cases、无 `evidence/manifest.json` → 开发 `verify --package` 通过、不产生 `evidence_digest`；同一包 `--release` → `evidence-incomplete`；清单存在但漏列 case 证据 → `case-evidence-mismatch` | `ADR-0128` §7.1、第四轮 P1-2 |
| `an_evidence_hash_covers_raw_file_bytes` | 把 `NOTICE`/case 证据从 LF 改成 CRLF 或改缩进、不更新清单 → `evidence-mismatch`；同步更新清单 → `release_digest` 变化 | `ADR-0128` §7.0/§7.1、第四轮 P2-4 |
| `the_case_file_is_part_of_the_release_digest` | 改 `tests/cases.json` 不更新清单 → `evidence-mismatch`；更新清单 → `evidence_digest`/`release_digest` 变，`definition_digest` 不变 | `H2-D8`、§7.1、第二轮 P1-1 |
| `the_release_mode_requires_complete_evidence` | 缺 `tests/cases.json` 条目、`NOTICE`、`sources`、`oracle.status` 或 skip 理由 → `evidence-incomplete`，退出 1 | `H2-D2`、`ADR-0128` §7.1、第二轮 P2-1 |
| `a_deep_json_document_is_refused_before_recursion` | ≤1 MiB、数万层嵌套 → 深度扫描在 `json::parse` 前拒绝，不栈溢出 | `H2-D11`、第一轮 P2 |
| `case_and_evidence_inputs_have_their_own_budget` | `tests/cases.json` 超过 16 MiB、证据清单/spec/lock 超过 1 MiB、forms 超过 1024、assets 超过 2048、cases/证据文件超过 4096、证据总量超过 16 MiB、单包资产累计超过 16 MiB、闭包 cases/证据总数超限；未选中包也受限 | `H2-D11`、第三轮 P2-1/P2-2 |
| `the_asset_budget_is_counted_while_reading` | 2048 个各 1 MiB 的文件或读时增长的文件 → 累计 reader 在 16 MiB 处拒绝，不只信 `stat` | `H2-D11`、`ADR-0128` §12.1、第三轮 P2-1 |
| `the_legacy_source_path_components_are_strict` | `legacy_source.isa`/`version` 含 `../`、`/`、盘符或 scheme → 路径形成前拒绝 | `H2-D3`、第一轮 P2 |
| `a_deleted_package_path_is_not_skipped` | 删除未发布包的 `package.json`/目录/重命名 → 由 base 树解析；删除已发布版本目录 → `published-package-modified`；无法映射是 `unmapped-package-path` | `H2-D5`、§5.3、第三轮 P1-1 |
| `only_executable_inputs_enter_the_source_digest` | 改 README/NOTICE → 源摘要不变；改 form 行 → 变 | `H2-D8` |
| `evidence_changes_do_not_move_the_definition_digest` | 改 README/NOTICE 并更新 evidence manifest → `evidence_digest`/`release_digest` 变，`definition_digest` 不变 | `H2-D8` |
| `an_evidence_entry_must_stay_inside_the_package_and_match_its_hash` | evidence manifest 列 `../` 或错误 sha256 → `evidence-mismatch`，退出 1 | `H2-D8` |
| `release_digest_tracks_the_release_not_the_builder` | 同 bundle 不同证据 → release 摘要不同；builder 版本变化 → release 摘要不变 | `H2-D8` |
| `the_legacy_snapshot_is_readable_by_load_dir` | 生成 `bundles/legacy/<bundle>/definition.json` → `Registry::load_dir` 可读；sealed bundle 放入定义目录被拒绝 | `H2-D9`、`H2-D12` |
| `changing_the_legacy_source_changes_the_source_digest` | `legacy_source` 从 `0.1.0` 改成 `0.78.0` → 源摘要变化；行未改时行相等测试失败 | `H2-D8`、`HE-AC-11` |
| `the_builder_identity_is_not_part_of_the_definition_digest` | 两个 builder 版本 → 同 definition/bundle 摘要，lock 的 builder 不同；`verify --check` 不把 builder 差异算作失败 | `HE-T19` |
| `the_generated_definition_is_read_by_fmp_model` | 坏 form 行 → `fmp_model::definition::read` 拒绝，构建器包装该拒绝 | `H2-D12` |
| `the_output_is_canonical_json` | lock/sealed 无空白、键排序、无尾随换行；与 Python canonical 一致 | `H2-D7` |
| `the_spec_lock_and_sealed_shapes_are_closed` | 三者的未知键/重复键被拒；`builder.build` 缺省时键省略而不是 `null`；lock 去掉 `builder` 后比较，sealed 逐字节比较 | `ADR-0128` §8.2、第四轮 P2-2 |
| `the_bundle_and_release_vectors_match` | `ADR-0128` §8.2 的 metadata 在 Rust 与 Python 中都得到 `b6d92574…`/`4e3d44a8…`；改域分隔或把嵌套摘要写成原始字节 → 不匹配 | 第四轮 P2-2/P2-3 |
| `resource_limits_are_enforced` | 超文件数/大小/路径/依赖深度/闭包总字节/资产总数/嵌套深度/单包累计资产字节 → 拒绝 | `H2-D11` |
| `the_published_version_directory_is_immutable` | 旧 spec 锁 `0.1.0`；作者新增 `0.2.0/` 并只改自有路径 → 旧 spec `verify --all --check` 仍绿，新包 `--package --release` 通过；原地改 `0.1.0` → `published-package-modified` | 第三轮 P1-1、§5.3 |
| `a_package_update_does_not_edit_an_old_spec` | 只新增版本目录、不动 spec/lock；旧 lock 字节不变 | 第三轮 P1-1、`HE-AC-05` |
| `a_legacy_package_target_must_match_its_source` | 复制 x86 行不变、把 `execution_mode` 改成 `"32"` 或 `address_width` 改成 32 → `legacy-target-mismatch`，在 `read` 前拒绝 | 第三轮 P1-2 |
| `the_digest_preimage_vector_matches` | H2-D8 向量在 Rust 与 Python 中都得到 `1afee65c…`；把嵌套摘要改成原始 32 字节 → 不匹配 | 第三轮 P2-3 |
| `level_zero_and_level_one_projections_are_exact` | Level 0 声明 `symbols` → `case-expect-shape`；Level 1 `include_symbol_table:false` 缺 `symbols` → 接受，写 `symbols: []` → 拒绝；`fingerprint`/`materializer_version` 永不在投影 | 第三轮 P2-4 |
| `a_dependent_package_is_structure_verified_but_closure_unverified` | 非空 `dependencies` 且无闭包：开发 `verify --package` 退出 0 并打印 `dependency_closure: unverified`；`--release` 退出 1（`dependency-unverified`）；`--release --closure <lock>` 且摘要匹配后通过 | 第三轮 P2-5、第四轮 P1-3 |
| `a_handwritten_closure_digest_is_not_trusted` | `--closure` 的 lock 里写一个不存在的 `path` 或错误 `source_package_digest` → `dependency-mismatch`，不报告 `verified`；重读实际包后通过 | `ADR-0128` §8、第四轮 P1-3 |

### 5.2 包级

| 测试（拟名） | 断言 | 对应 |
|---|---|---|
| `every_package_form_equals_the_pinned_legacy_row` | 三个包逐 form canonical JSON 相等，比较对象是钉住版本 | `HE-AC-03`、`HE-AC-11` |
| `a_form_row_is_compared_against_its_pinned_version_not_the_newest_file` | 把钉住版本换成最新版本 → x86 行被判定不等；构建器不自动改用最新 | `H2-D8`、`HE-AC-11` |
| `the_package_export_set_is_exact` | 导出集合 = 清单声明集合；没有隐藏 form | `HE-AC-03` |
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
```

它按 `bundles/specs/*.json` 显式重建，不按目录扫描决定选择。比较范围是
sealed bundle 全字节、lock 除 `builder` 外的字节；`builder` 只做形状检查和
打印，理由与 `ADR-0126` 的 payload/envelope 分层相同。

普通扩展还需要独立门禁，且必须同时证明结构和机器码。作者的默认路径不要求先
改全局 spec，也不因包声明了依赖就被卡住：

```text
cargo run -p fmp-definition -- verify --package <changed-package-path>
cargo test -p fmp-definition --test package_conformance
# 无依赖的包还跑完整的发布证据检查；有依赖时加 --closure <lock>
cargo run -p fmp-definition -- verify --package --release <changed-package-path>
```

`verify --package` 用 `monasm-standalone/0.1` 独立身份，校验清单、路径/版本目录
一致、导出、`read`、自述目标、legacy 目标一致性、用例 schema/覆盖/排序、
`scope`/`baseline_case_id`/`mutates` 与计划差分、单指令 `form_id` 绑定、完整
诊断数组形状与错误范围、证据引用与哈希、累计资产预算；开发模式没有证据清单时
直接核对 case 自带哈希，有清单时以清单为准。它不执行 `bind`/`materialize`。
`--release` 额外要求完整证据；非空 `dependencies` 还要求 `--closure <lock>`，
否则 `dependency-unverified`（退出码 1）。作者可以在自己的 PR 里带一个精确的
本地 lock 跑 `--release`，但只有被发布 spec 选中时，`verify --all --check` 才用
spec 闭包重读所有依赖并做完整 release 校验。`package_conformance` 执行每个包的
`tests/cases.json`：替换独立身份 → `plan::read` → `bind` → `materialize`，比较
§4.2.1 的精确投影，并断言负例的完整 `(code, path)` 集合；`Internal`/`HostFailure`
不算通过。这些检查一起才能让「opcode 改错但 JSON 合法」「声明 form B、实际执行
form A」或「用 `expected_digest` 冒充 form 边界」的包失败。

CI 从 PR diff 提取 `packages/**` 下的所有变更路径，逐个映射版本目录：

- 修改/新增文件：在 **head** 树找最近的含 `package.json` 的祖先；其目录名
  必须等于清单 `version`（`path-version-mismatch`）。若该版本已被任一 spec
  选中，任何修改是 `published-package-modified`，退出 1。
- 删除文件/目录：在 **base** 树找版本目录；删除已发布版本目录内任何文件是
  `published-package-modified`。删除未发布包时，同一 PR 必须更新/删除引用它的
  spec，`verify --all --check` 是「没有活引用」的证明。
- 重命名/移动：旧根和新根都检查；移动已发布版本目录是
  `published-package-modified`；新增版本必须用同级新目录。移动未发布包会改变
  spec 的 `path`，移动跨 target 目录还必须继续满足 form 家族一致性。
- 无法映射到任何版本目录的 `packages/**` 变更（例如直接放在 `packages/` 下的
  散落文件，或 base 树也找不到根）是 `unmapped-package-path`，退出 1，绝不
  静默跳过。

这条路径不要求包已被任何 spec 选中，也不改中心 `bundles/specs/`。只改
`forms/*.json` 而不改清单也会触发检查。变更路径列表只决定跑哪些包，不决定
构建器选择什么。`verify --all` 覆盖发布组合，`verify --package` 覆盖作者单包；
无依赖的变更包还直接跑 `--release`，有依赖的包则由作者本地 closure 或被 spec
选中后的 `--all --check` 完成闭包重读。两者都列为 H2 退出门槛，不推迟到 H5。
H2 不新增 per-package job matrix；单命令加 diff 提取足够，完整 matrix 属于
`ADR-0130`。

## 6. 提交拆分

H2 是一个阶段，但按 `ADR-0125` §13.1 拆成两个可回归提交（同一 PR）：

| 提交 | 内容 | 必过 |
|---|---|---|
| H2a | `ADR-0128` 评审通过后接受 + 本文状态更新 + `fmp-definition` crate（manifest、spec、build、digest、error、CLI）+ `monasm-standalone/0.1` 独立身份 + **完整的单包发布证据与摘要机制**（`tests/cases.json` 入清单、`NOTICE`、`sources`、`oracle.status`/skip、`evidence_digest`/`release_digest`、跨语言摘要向量、用例/证据/spec/lock 预算与单包累计资产预算）+ **版本目录不可变/已发布快照门禁** + **legacy 目标一致性** + **`scope:"form"` 基线变异与完整诊断集** + **Level 0/1 精确投影** + **`structure`/`dependency_closure` 分离** + `verify --package --release` 与变更路径门禁（含删除/重命名）+ x86 `mov-register` 包（`0.1.0/`）及其 `tests/cases.json`/`evidence` + 无 `legacy_source` 的合成包契约测试 + 错误 opcode 与错误 form 声明反例 + 构建器单测 + X86-P1 字节等价 + `bundles/` 的 x86 spec/lock/sealed/legacy snapshot + `gates.yml` 的 verify 两步与 conformance | fmt、workspace test（含 `package_conformance`）、`check_ids`、`check_definition`、baseline、whitespace |
| H2b | aarch64 `add-immediate`（`0.1.0/`）+ rv64 `integer-alu`（`0.1.0/`）+ 三 ISA conformance harness + 这两个包的 cases/evidence/NOTICE 资产 + 跨 ISA/跨包测试 + 全部 lock/sealed/legacy snapshot + `research/he1/H2-report.md` + `STATUS.md` 的 H2 记录 | 同上 + oracle |

H2a 必须先全绿再开 H2b：先证明一个包的构建、摘要、完整发布证据和字节等价，
再证明跨 ISA 与独立包。H2a 的 `--release` 必须已经具备完整的来源、`NOTICE`、
oracle 状态和用例证据校验；H2b 不回头补齐 H2a 的信任边界，只增加 AArch64/RV64
资产和跨包测试。H2a 不引入 H2b 才需要的多包 harness；H2b 不修改 H1 的身份代码。

`ADR-0128` 目前在 PR #4 中为 `proposed`；评审合并后才写 `accepted`，H2a 也从
那里开始实现。`ADR-0130` 不在 H2 内，除非 H2b 决定增加 per-package job
matrix。若增加，先写 `ADR-0130`，再改 workflow。

## 7. 风险与回滚

| 风险 | 处置 |
|---|---|
| 构建器变成第二套定义权威 | 构建器只做清单/闭包/归属/合并/摘要；form 结构一律交给 `fmp_model::definition::read` |
| canonical 实现漂移 | 复用 `fmp_model::canonical`；与 Python `check_definition.py` 的 canonical 对照测试 |
| 包顺序、spec 顺序或目录顺序影响摘要 | spec 显式列出完整闭包与 `path`；合并后按 `form_id` 排序；从不扫描 `packages/`；临时目录反向重建测试 |
| 把 form 排序误当程序布局排序 | 文档与测试分开「包集合规范化」和「指令/节/fixup 顺序」；后者不由构建器触碰 |
| 归属冲突被 last-wins 吞掉 | 构建期唯一归属表；相同内容也失败；`HE-T07` |
| 路径逃逸/符号链接 | 打开前 canonicalize + 包根前缀检查；Windows reparse point 拒绝 |
| 独立身份随目录/cwd 漂移 | 固定 `monasm-standalone/0.1` 函数；复制到不同目录/换 cwd 的摘要相等测试；保留前缀禁止写入 spec |
| 新包没有机器码证据也能通过 | 每个导出 form 强制正例+负例；`package_conformance` 执行；错误 opcode 反例；`--release` 检查证据完整性 |
| 用例声明 form B、计划实际执行 A | 计划恰好一条 instruction，`instruction_id`/`form_id` 必须等于 case 字段；不一致 `case-form-mismatch`；正例比较实际执行的 form |
| 负例被无关错误满足 | 只有 `scope:"form"` 计入覆盖；它必须绑定同 form 的正例、只改一个操作数指针，并匹配完整 `(code, path)` 集合；`expected_digest` 只能作为 `scope:"plan"` |
| 已发布包被原地改写，旧 spec 无法重建 | 版本目录是发布快照；旧目录禁止修改/删除；新版本用同级新目录；CI 先判 `published-package-modified` 再谈 spec 更新 |
| 迁移包行相同但执行目标变了 | 有 `legacy_source` 时同时比较 `definition_format` 和完整 `target_identity`；不一致是 `legacy-target-mismatch` |
| Rust 与 Python 对同一摘要字节不一致 | 冻结域分隔、`sha256:` 文本规则和固定向量；H2a 两种语言都必须通过 |
| 缺失键被 harness 归一化成空数组 | Level 0/1 投影键集固定；缺 `symbols` 与 `symbols: []` 不等价；由 `case-expect-shape` 拒绝 |
| 单包验证声称依赖已证明 | 分别报告 `structure` 和 `dependency_closure`；无显式闭包时非空依赖是 `unverified`，`--release` 退出 1 |
| 改测试集不改变发布身份 | `tests/cases.json` 列入证据清单；未更新清单是 `evidence-mismatch`，更新后 `release_digest` 改变而 `definition_digest` 不变 |
| 不同扩展集合的包无法组合 | 包 `enabled_extensions` 是需求、spec 是选择；H2 用 `h2-exact-target` 过渡，H3 解除并在 H5 前生效 |
| form 家族与 target 张冠李戴 | 规则是 `family(form_id) == isa_family` 字符串相等，不是包格式 ISA 白名单；跨 ISA 注入反例；在 `read` 之前拒绝 |
| 新增 ISA 被迫改包格式 | 包格式不列家族；H3 的第四种 reader 家族只要自述相等就通过；构建器不追加 ISA 名单 |
| 包输入预算只覆盖闭包 | `tests/cases.json` ≤ 16 MiB，证据清单/spec/lock 各 ≤ 1 MiB；forms ≤ 1024、assets ≤ 2048、cases/证据文件 ≤ 4096；单包 manifest+资产累计 ≤ 16 MiB，按实际读取累加；未选中包也受限 |
| 删除/重命名包逃过路径门禁 | 删除在 base 树解析包根；删除 `package.json`/包目录必须同步改 spec；无法映射是 `unmapped-package-path` |
| 深 JSON 先解析后测深度 | 迭代扫描在 `json::parse` 之前执行；≤1 MiB 数万层反例不得栈溢出 |
| 证据完整性只是名义存在 | `--release` 要求 `tests/cases.json`、`NOTICE`、`sources`、`oracle.status`、skip 理由；证据清单进入 `evidence_digest` |
| H2a 的发布校验不完整 | H2a 就交付单包完整证据与摘要机制；H2b 只增加 ISA 资产和跨包测试，不补信任边界 |
| 包文件改动漏进 legacy | `definitions/` 只读；`payload_root`/`definitions_root` 复跑；PR diff 检查 |
| lock/sealed 提交后过期 | CI `verify --all --check` 重建；sealed 全字节、lock 除 `builder` 外比较 |
| 把 H2 做成 H3/H4 | §9 明确排除；`bind` 签名、`fmp/0.2`、profile、深层 JSON 不动 |
| 普通扩展仍要改中心表 | 包测试由 `verify --package` + PR 变更路径驱动；`STATUS.md` 计数不手工加；`check_definition.py` 不扩展 |
| 未发布的新包没有门禁 | `verify --package` 不依赖 spec；CI 提取变更 `packages/**` 路径逐个跑 |
| 未知 capability 进入已验证快照 | build/verify 拒绝白名单外的 `requires_capabilities`；运行时协商仍属 H3 |
| 不同定义格式被隐式混用 | 闭包要求所有包 `definition_format` 一致；混合即拒绝，不转换 |
| 证据改动改变执行身份 | 证据只进 `evidence_digest`/`release_digest`，不进 `definition_digest` |
| 旧定义快照无法被旧入口读取 | 额外输出 `bundles/legacy/<bundle>/definition.json`；sealed 不是定义文档 |

回滚：H2 只新增 crate、包和 bundle；`bind`/`materialize`/`Definition` 不变。
撤回 H2 提交即可回到 H1 状态，不需要迁移持久状态。`packages/` 和 `bundles/`
不是运行期发现路径，删掉也不影响 legacy 构建。

## 8. 明确不在 H2 内

- `fmp/0.2` 计划格式、命名空间化 ISA 身份、零操作数 form（H3）。
- 运行期 bundle reader、运行期能力协商、未选中包损坏隔离（H3）；H2 只在
  构建期拒绝未知能力字符串。
- `fmp-def/0.1` 与 `0.2` 的隐式转换或自动迁移（H3 的显式转换）。
- `type`/`profile` 资产的执行或输出；非空声明在 H2 被拒绝（H4）。H2 只冻结
  外层身份、排序、摘要输入和拒绝语义，不冻结其内部语义。
- `bind` 接受 `VerifiedBundle`、`fmp-validate → fmp-definition` 依赖（H3）。
- 解除 `h2-exact-target` 的 H3 计划侧目标兼容；H2 只声明过渡限制和退出门槛。
- 对新增包实际重跑或联网调用外部 oracle；H2 只校验证据记录、来源、哈希和
  用例执行，fixtures 的 `rerun.py` 仍只覆盖 legacy 语料（H3/H4 可扩展）。
- fixup profile、非零 addend、Hi/Lo 配对、范围/字段所有权语义（H4）。
- 深层 JSON、重复键、超大输入的完整鲁棒性与模糊测试（H4）。
- 真实同 ISA A/B 包、三个并行工作流、`HE-AC-01`/`02`/`07`/`12` 的完整验收（H5）。
- 迁移全部 104 份定义或 619 个负例；不批量重命名 form。
- 新增指令覆盖；`unsupported-capability` 的运行时路径（H3/H4）。

## 9. 待审决策

| # | 问题 | 建议 | 代价/备选 |
|---|---|---|---|
| O1 | `exports.forms` 用 `{id, path}` 还是裸字符串 | **`{id, path}`**：文件内容与声明逐项绑定 | 裸字符串更短，但交换文件只能靠文件名猜归属 |
| O2 | Bundle spec 目录叫 `bundles/specs/` 还是设计草案的 `bundles/profiles/` | **`specs/`**：避免与 H4 fixup profile 混淆；写进 `ADR-0128` | 沿用 `profiles/` 更贴设计原文，但读者会误以为是 fixup profile |
| O3 | H2 的类型叫 `VerifiedBundle` 还是 `BuiltBundle` | **`VerifiedBundle`**，但文档限定为 H2 的包/闭包/归属验证；运行期能力验证仍属 H3 | `BuiltBundle` 更保守，但与 H1 D1 的命名不一致 |
| O4 | 包级 harness 放哪里 | **`fmp-definition/tests/` + dev-dependencies**，不新增产品 crate | 独立 `fmp-conformance` crate 边界更干净，但 H2 会增加一个 workspace 成员 |
| O5 | 开发工具入口 | **`fmp-definition build|verify|digest` 独立 binary**，不改 `fmp` CLI | 加到 `fmp` 子命令更集中，但会扩大 CLI 兼容面 |
| O6 | 包用例格式 | **完整 `fmp/0.1` 文档 + `$standalone` 哨兵**；计划恰好一条 instruction，其 `instruction_id`/`form_id` 必须绑定 case；负例分 `scope:"plan"`/`scope:"form"`，form 负例绑定正例基线、只改一个操作数指针，并匹配完整 `(code, path)` 集合 | 独立 DTO 更短，但会把关键映射留给实现者各自解释；允许任意负例会让错误的 `expected_digest` 冒充操作数边界测试 |
| O7 | lock/sealed 是否提交 | **提交**，CI `--check` 重建；它们是发布产物，不是手写计数 | 只在测试里构建更轻，但发布 bundle 无法审计 |
| O8 | 三个包/forms 是否按 §4 表 | **按表**；已测量：x86 与 rv64 钉 `0.1.0`（前者行漂移，后者目标集合），aarch64 钉 `0.20.0` | 选更多 form 会增加等价面，不增加平台证明力 |
| O9 | `exports.types`/`profiles` 现在预留还是等新格式版本 | **现在预留**：键、`{id, path}` 形状、排序和摘要都定义；非空在 H2 以 `unsupported-asset` 拒绝 | 版本化延后更少代码，但会同时承诺封闭格式和无缝扩展 |
| O10 | H2 如何处理未知 `requires_capabilities` | **构建期拒绝**，只承认 `field-placement/v1`、`integer-domain/v1` | 只记录更宽松，但未知能力包会进入已验证快照 |
| O11 | 新包没有 `legacy_source` 时如何验证 | **包自述 `target_identity`/`definition_format` + 独立身份 + `read` + 包用例**；用一个合成包证明不依赖历史定义 | 强制新包也写 legacy 来源会永久绑定旧目录 |
| O12 | `verify --package` 的 Definition namespace/version 从哪来 | **`monasm-standalone/0.1` 固定函数**：`monasm.standalone.<package_id>` / `standalone+<source digest>`；保留前缀禁止进入 spec | 从 spec 借用会碰撞；从目录推导会随 cwd 漂移 |
| O13 | 包级机器码测试是否强制 | **强制**：每个 form 正例+负例、证据引用、`package_conformance` 执行、`--release` 检查证据完整性 | 只靠 `read` 会放过合法结构里的错误 opcode |
| O14 | 包 target 与 bundle target 的关系 | **包声明需求、spec 声明选择**；子集校验；`fmp-def/0.1` 用 `h2-exact-target` 过渡，H3 解除 | 逐字段相等会把新增扩展族变成对既有包的强制改版 |
| O15 | form 家族与 target 的一致性 | **通用相等规则** `family(form_id) == target_identity.isa_family`；包格式不列 ISA；第四种家族由 H3 的 reader 支持，不需要改包协议 | 三 ISA 对应表实际全是字符串相等，会迫使 H3 再改一次公共格式 |
| O16 | 证据文件是必需还是可选 | **开发包可选、可发布包必需**；`--release`/spec 选中时要求 `tests/cases.json`、`NOTICE`、`sources`、`oracle.status`、skip 理由和用例证据；`tests/cases.json` 本身被哈希 | 永远可选或只哈希用例证据会让 `release_digest` 不代表完整审核证据 |
| O17 | 已发布包如何继续演进 | **版本目录是不可变快照**：`packages/<target>/<package>/<version>/`；更新创建同级新目录，旧 spec/lock 原样重建；发布者另行选择新版本 | 原地覆盖会迫使作者改旧 spec；按摘要命名路径让作者无法预知路径且难以审查 |
| O18 | `legacy_source` 迁移等价性 | **行相等 + `definition_format`/完整 `target_identity` 相等**；不一致是 `legacy-target-mismatch` | 只比行会放过 `execution_mode`/`address_width` 被改、但行逐字节相同的包 |
| O19 | 每个 form 的负例覆盖 | **`scope:"form"` + 正例基线 + 单操作数变异 + 完整诊断集**；`scope:"plan"` 不计覆盖 | 任意负例可被 `expected_digest` 或根级错误满足，不能证明 form 边界 |
| O20 | 摘要预映像的字节规则 | **canonical record + 域分隔 + 嵌套 `sha256:` 文本 + 跨语言固定向量** | 原始 32 字节/大写 hex 会让 Rust 与 Python 得到不同摘要 |
| O21 | 机器输出投影 | **Level 0/1 各自封闭键集**；Level 0 无 `symbols`；Level 1 仅在 `include_symbol_table` 时含 `symbols` | 共用并集投影会把缺失键和空数组混为一谈 |
| O22 | 单包验证能否证明依赖 | **分开报告 `structure` 与 `dependency_closure`**；无显式闭包时非空依赖是 `unverified`，`--release` 退出 1 | 只检查清单形状会把“声明了依赖”当成“依赖已解析” |

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
| case/证据/spec/lock 的单文件、数量与总量预算，含读取时累计的单包资产预算 | 尚未实现 | **未验证** — H2a |
| 版本目录不可变、`published-package-modified`、`path-version-mismatch` | 尚未实现 | **未验证** — H2a |
| `legacy_source` 的目标一致性 | 尚未实现 | **未验证** — H2a |
| `scope:"form"` 基线变异、完整诊断集、Level 0/1 精确投影 | 尚未实现 | **未验证** — H2a |
| `structure`/`dependency_closure` 分离 | 尚未实现 | **未验证** — H2a |
| 证据完整性、`evidence_digest` 与 release 摘要分层 | 尚未实现 | **未验证** — H2a（机制）；H2b 只增加资产 |
| 解析前 JSON 深度拒绝 | 尚未实现；H0 探针只证明现有递归解析器会栈溢出 | **未验证** — H2a 加迭代预算 |
| 深层 JSON 鲁棒性 | H0 探针已测栈溢出；H2 不改 `fmp` 解析器 | **未验证/不在 H2** — H4 |
| 完整的 per-package CI matrix | 未实现；H2 只做单命令 | **未实现** — `ADR-0130`/H5 |

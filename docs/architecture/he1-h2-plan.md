# H2 实施计划：目标包作者层与确定性定义构建

- 状态：**待审提案**（2026-11-14）。规范决策见
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
packages/<target>/<package>/
  package.json
  forms/*.json
  tests/cases.json
  evidence/sources.json
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

## 3. 契约决定（待 `ADR-0128` 固化）

以下决定编号 `H2-D1`–`H2-D12` 只在本计划内引用；规范文本已写进
`docs/adr/0128-package-and-bundle-contract.md`，本节保留实施细节。

### H2-D1 目录与显式输入

- 叶包路径：`packages/<target>/<package>/`，`target` 是目录名（`x86_64`、
  `aarch64`、`rv64`），不是 form ID 前缀。
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
- `exports.forms` 用 `{id, path}` 而不是裸字符串：文件内容里的 `form_id` 必须
  等于声明的 `id`；交换两个文件不会静默改变归属。
- `exports.forms` 必须按 `id` 严格升序，重复 `id` 拒绝；这样清单只有一种写法，
  重排不是「另一个合法清单」。
- `exports.types` / `exports.profiles`：可选的 `{id, path}` 列表，文件和
  `exports.forms` 一样按 `id` 严格排序，每个文件只放一个 type/profile 对象，
  其 `type_id`/`profile_id` 必须等于声明的 `id`。它们已进入封闭键集和源摘要，
  但 H2 不执行也不输出这些资产，非空列表以 `unsupported-asset` 拒绝。缺省与
  空列表都表示零资产，但它们是不同的清单、得到不同的源摘要；lock 钉住实际
  发布的那一种写法。
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
- `evidence/manifest.json` 可选，形如
  `{"evidence_format":"monasm-evidence/0.1","files":[{"path":"NOTICE","sha256":"..."}]}`，
  按 `path` 排序，是封闭对象：未知/重复键拒绝，每项必须恰好有 `path` 和
  `sha256`。它只覆盖 README/NOTICE/oracle/用例证据；不进入源摘要或定义摘要，
  只进入 lock 的 `evidence_digest` 和 `release_digest`；列出的文件必须存在、
  位于包内且哈希匹配，否则 `evidence-mismatch`（退出码 1）。
- 每个 `forms/*.json` 只放一个 form 对象；迁移包里它就是 legacy 定义里的
  对应行，新包里它由包自己的用例和 oracle 证明。这样归属、摘要和差异都可以
  逐行审查。

### H2-D3 路径边界

- 所有清单路径必须是包内规范化相对路径，使用 `/`。
- spec 的 `packages[].path` 相对于 `--root`；解析后仍必须位于 `--root` 之下。
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
      "path": "packages/x86_64/mov-register",
      "source_package_digest": "sha256:..."
    }
  ]
}
```

- `packages` **就是完整闭包**，不是「根集合」。构建器只读取这里列出的
  `path`，从不扫描 `packages/` 目录；依赖边只用于校验，不用来发现新包。
- `target.identity` 与 `definition_format` 必须与**每个包自己声明的**
  `target_identity`、`definition_format` 逐字段相等；它们不再从包钉住的 legacy
  定义推导。`fmp-def/0.1` 与 `fmp-def/0.2` 的 form 行不是同一种对象：0.2 的
  x86 行多出 REX 位放置和 `requires_extensions`，而 0.1 的 reader 会因未知键
  拒绝 0.2 行；反之 0.1 行放进 0.2 文档会缺必需键。构建器必须让 spec、包自述
  和行三者互相一致；混合格式的闭包直接拒绝，不做隐式转换，显式版本化转换属于
  H3。
- `target.profile_id` 必须与每个包的 `target_profile` 一致，否则构建失败。
- H2 不引入 `target profile` 的中央 Rust 表。目标事实由包清单和 spec 数据共同
  提供，这正是 H3「新目标不改公共白名单」的前置条件。
- 没有 `legacy_source` 的新包不需要先写进任何 spec：`verify --package` 用包
  自述的目标、`read` 合并文档和包自己的用例完成校验。这是普通扩展作者的独立
  测试路径，也是 H2 证明作者协议不永久依赖历史定义的方式。
- `fmp-def/0.1` 按集合相等比较 `enabled_extensions`，`fmp-def/0.2` 把表集合
  当上限。H2 只复用这两条既有规则，不改变任何一条。

### H2-D5 依赖闭包：spec 列全，构建器不扫描

- `BundleSpec.packages` 列出闭包内的每个包（ID、version、path、digest）。
  构建器只打开这些 path；`packages/` 目录里多一个或少一个文件都不影响构建。
- 每个包清单的 `dependencies` 是校验边：每个 `{package_id, version,
  source_package_digest}` 必须精确对应 spec 列表中的一项，且 digest 必须等于
  该包的实际 `source_package_digest`。依赖不能引入列表外的包。
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
- `verify --package <path>` 不读 spec，只按包清单检查单包契约；它和
  `verify --all` 是两条门禁：前者覆盖尚未进入发布 bundle 的新包，后者覆盖
  发布组合。CI 的变更路径列表只决定跑哪些 `--package`，不决定构建器选择什么。

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

| 摘要 | 输入 | 不包含 | 反例（缺它会怎样） |
|---|---|---|---|
| `source_package_digest` | canonical manifest（不含自身摘要）+ 每个声明资产（form/type/profile）的 canonical 摘要，按路径排序，带资产种类域分隔 | README、NOTICE、evidence manifest、测试、作者路径 | 只哈希 manifest：换掉 form 的 template 而清单不变，包摘要不动 |
| `evidence_digest` | `monasm-evidence/0.1` 域分隔 + canonical `evidence/manifest.json`；文件不存在时省略 | 清单未列出的 README/NOTICE 文字、oracle 日志内容、作者路径 | 直接哈希 README：改一个错字就改变执行身份，规则却没变 |
| `definition_digest` | `fmp_model::definition::read` 对合并文档算出的 canonical 摘要 | builder 版本、构建时间、主机 | 只哈希包集合：两个不同 form 行得到同一 bundle 身份 |
| `bundle_digest` | `monasm-bundle/0.1` 域分隔 + canonical bundle 元数据（`bundle_id`、`definition_format`、`namespace`、`version`、`target`、排序后的 package 身份、`definition_digest`） | bundle 自身的 `bundle_digest` 字段、builder 版本 | 把自身字段算进去：自引用，永远算不出固定点 |
| `release_digest` | `monasm-release/0.1` 域分隔 + canonical `{bundle_id, bundle_digest, definition_digest, packages:[{package_id, version, source_package_digest, evidence_digest?}]}`，按包身份排序 | 定义行本身、builder、sealed 字节 | 同一 bundle 的两份发布证据无法区分 |
| `builder` | `{name, version, build: Option<String>}`，只进 lock/收据 | 不进入 definition_digest | 把构建版本算进定义摘要：换一个 builder 版本就误报定义漂移（`HE-T19`） |

域分隔使用与算法名相同的字面量，例如 `sha256("monasm-package/0.1\0" ++ …)`；
算法名改动必须同时改域分隔，不能只改一处。`legacy_source` 是清单键，存在时
进入 `source_package_digest`；`evidence/`、`README`、`NOTICE` 不进源摘要或
定义摘要。`evidence_digest` 只在证据清单存在时生成，并且只进 lock 的
`release_digest`；执行规则身份与审计证据身份因此分开，发布时仍可通过 lock
追踪二者。

### H2-D9 spec、lock、sealed bundle

- `bundles/specs/<bundle>.json`：发布者写的显式选择（`monasm-bundle-spec/0.1`）。
- `bundles/locks/<bundle>.lock.json`：构建器生成的完整 bundle 元数据
  （`bundle_id`、`definition_format`、`namespace`、`version`、`target`、
  `bundle_digest`、`definition_digest`、`release_digest`）、每个包的 `path`、
  `source_package_digest`、可选 `evidence_digest`，以及 `builder`。
- `bundles/sealed/<bundle>.bundle.json`：扁平化的 `monasm-bundle/0.1`，内含
  `bundle_format`、`bundle_id`、canonical definition 文档、`bundle_digest`、
  `definition_digest` 和排序后的来源列表；不含 builder 收据、`release_digest`
  或作者路径。
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
| 确定性拒绝 | 清单形状（必需/可选键）、路径越界、依赖缺失/摘要错/环、同一 package ID 双版本、归属冲突、未知 capability、非空 reserved asset、闭包聚合上限、定义被 `read` 拒绝 | 1 |
| 宿主/IO/内部 | 文件读失败、锁文件不可写、内部不变量破坏 | 2 |
| 成功 | 构建或校验通过 | 0 |

`BuildError` 的变体名包括 `unsupported-capability`、`unsupported-asset`、
`version-conflict`、`aggregate-limit`、`legacy-row-mismatch`、
`evidence-mismatch`；它们不是 `fmp/0.1` 诊断码。

`fmp` CLI 的 0/1/2 语义不变。H2 不把包构建错误送进 `bind` 的诊断数组。

### H2-D11 资源上限

H2 只加构建器自己的有界输入，不声称解决深层 JSON：

- 单个 manifest ≤ 1 MiB；
- 单个 form/type/profile 文件 ≤ 1 MiB；
- 每个包导出 forms ≤ 4096；每个包声明资产 ≤ 4096；
- 闭包内包数 ≤ 1024；闭包总包字节 ≤ 64 MiB；
- 闭包内声明资产总数 ≤ 65 536；
- 单条路径 ≤ 1024 字节；依赖深度 ≤ 64；
- manifest/form/type/profile/spec/lock 的 JSON 嵌套深度 ≤ 64。

超限是确定性拒绝（退出码 1）。深度上限是构建器自己的解析预算，不声称
`fmp` 对深层 JSON 鲁棒；深层文档造成的解析器栈溢出仍是 H4。H2 的包输入是
开发者控制的输入，不把 `HE-T13` 算作完成。

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
| x86_64 | `packages/x86_64/mov-register/` | `x86:mov/rm-r64/legacy`、`x86:mov/r64-rm/legacy` | `X86-P1` | `x86_64/0.1.0` | 两个方向、REX/legacy 放置、寄存器槽位 |
| aarch64 | `packages/aarch64/add-immediate/` | `aarch64:add/x64-x64-x64-lsl0`、`aarch64:add/x64-imm12-lsl0`、`aarch64:add/x64-imm12-lsl12` | `A64-P1`、`A64-P2`（两个版本） | `aarch64/0.20.0` | 寄存器三元、imm12、`sh` 由 form ID 固定 |
| rv64 | `packages/rv64/integer-alu/` | `riscv:add/rd-rs1-rs2`、`riscv:addi/rd-rs1-imm12` | `RV-P1`、`RV-P2` | `rv64/0.1.0` | 三寄存器、imm12、整数域 |

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
4. 断言包导出的 form 集合恰好等于声明的集合，不多不少。

没有 `legacy_source` 的包跳过 1–3；`verify --package` 检查清单、路径、导出、
`read` 和自述目标，机器输出由包自己的 case 证明。H2 至少用一个合成包（沿用
现有 ISA family，但 form ID 不在 legacy 目录中）验证这条路径，不把「没有历史
定义」当成「无法校验」。

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
5. 与 legacy 产物比较机器输出投影：
   `format_version`、`level`、`bytes_hex`/`sections`、`symbols`、`fixups`。

**不比较** `fingerprint` 和 `materializer_version`：

- `fingerprint` 的输入是 `plan.legacy_document`，其中包含计划声明的
  `definition_identity`。换 bundle 身份必然改变它；这是 `ADR-0127` D12 已经
  记录的 legacy 行为，不是机器输出漂移。
- `materializer_version` 是构建收据，不是机器输出。

因此 H2 的等价投影是「机器输出」，不是 `payload/0.1`。`payload_digest` 包含
`fingerprint`，也不能作为这里的比较键。报告必须把这条写清楚，避免把
「payload 不同」误报成「字节不同」。

反向测试：同一派生计划把 digest 改回错误值，`bind` 必须在
`/definition_identity/digest` 返回 `E-DEF-001`；包路径不能绕过 H1 的身份检查。

### 4.3 独立测试（两个包可以分别验证）

- x86 包和 rv64 包各自在临时目录构建，不读取对方的包。
- 每个包的 `tests/cases.json` 声明：form ID、case ID、计划事实、期望字节、
  oracle 或手工证据、已知未验证项。
- 每个导出 form 至少一个正例；至少一个非法邻域（立即数越界、错误寄存器宽度、
  错误 target type）由 `bind` 拒绝。
- 包级 harness 只按清单数据分派，不按 ISA 名称写执行分支；`HE-T14` 的
  「同一 harness」在 H2 只证明 harness 没有 ISA 分支，不证明三个真实工作流。

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
| `an_unknown_capability_is_refused` | `requires_capabilities` 出现白名单外字符串 → `unsupported-capability`，退出 1 | `H2-D2`、`HE-T09`（H2 构建期部分） |
| `a_non_empty_reserved_asset_is_refused` | `exports.types`/`profiles` 非空 → `unsupported-asset`，不静默忽略 | `H2-D2`、`H2-D6` |
| `two_versions_of_one_package_id_conflict` | 同一 `package_id` 两个版本、导出不相交 → `version-conflict` | `H2-D5` |
| `a_package_without_legacy_source_is_verified_from_its_own_target` | 合成包无 `legacy_source` → 按自述目标、`read` 和用例通过，不需要 spec | `H2-D2`、`H2-D4`、§4.1 |
| `a_file_form_id_must_match_its_export` | 交换两个 form 文件 → 归属不匹配，拒绝 | `H2-D2` |
| `the_target_profile_must_match_the_spec` | 包的 `target_profile` 与 spec 不一致 → 拒绝 | `H2-D4` |
| `only_executable_inputs_enter_the_source_digest` | 改 README/NOTICE → 源摘要不变；改 form 行 → 变 | `H2-D8` |
| `evidence_changes_do_not_move_the_definition_digest` | 改 README/NOTICE 并更新 evidence manifest → `evidence_digest`/`release_digest` 变，`definition_digest` 不变 | `H2-D8` |
| `an_evidence_entry_must_stay_inside_the_package_and_match_its_hash` | evidence manifest 列 `../` 或错误 sha256 → `evidence-mismatch`，退出 1 | `H2-D8` |
| `release_digest_tracks_the_release_not_the_builder` | 同 bundle 不同证据 → release 摘要不同；builder 版本变化 → release 摘要不变 | `H2-D8` |
| `the_legacy_snapshot_is_readable_by_load_dir` | 生成 `bundles/legacy/<bundle>/definition.json` → `Registry::load_dir` 可读；sealed bundle 放入定义目录被拒绝 | `H2-D9`、`H2-D12` |
| `changing_the_legacy_source_changes_the_source_digest` | `legacy_source` 从 `0.1.0` 改成 `0.78.0` → 源摘要变化；行未改时行相等测试失败 | `H2-D8`、`HE-AC-11` |
| `the_builder_identity_is_not_part_of_the_definition_digest` | 两个 builder 版本 → 同 definition/bundle 摘要，lock 的 builder 不同；`verify --check` 不把 builder 差异算作失败 | `HE-T19` |
| `the_generated_definition_is_read_by_fmp_model` | 坏 form 行 → `fmp_model::definition::read` 拒绝，构建器包装该拒绝 | `H2-D12` |
| `the_output_is_canonical_json` | lock/sealed 无空白、键排序、无尾随换行；与 Python canonical 一致 | `H2-D7` |
| `resource_limits_are_enforced` | 超文件数/大小/路径/依赖深度/闭包总字节/资产总数/嵌套深度 → 拒绝 | `H2-D11` |

### 5.2 包级

| 测试（拟名） | 断言 | 对应 |
|---|---|---|
| `every_package_form_equals_the_pinned_legacy_row` | 三个包逐 form canonical JSON 相等，比较对象是钉住版本 | `HE-AC-03`、`HE-AC-11` |
| `a_form_row_is_compared_against_its_pinned_version_not_the_newest_file` | 把钉住版本换成最新版本 → x86 行被判定不等；构建器不自动改用最新 | `H2-D8`、`HE-AC-11` |
| `the_package_export_set_is_exact` | 导出集合 = 清单声明集合；没有隐藏 form | `HE-AC-03` |
| `the_x86_package_reproduces_legacy_machine_output` | X86-P1 的机器输出投影相等 | `HE-T18`（H2 部分） |
| `the_aarch64_package_reproduces_legacy_machine_output` | A64-P1、A64-P2 的机器输出投影相等 | `HE-T18`（H2 部分） |
| `the_rv64_package_reproduces_legacy_machine_output` | RV-P1、RV-P2 的机器输出投影相等 | `HE-T18`（H2 部分） |
| `the_only_difference_is_the_definition_identity` | 除 `fingerprint`/`definition_identity` 外无字段差异；错误 digest 被 `bind` 拒绝 | `HE-T18`、`HE-AC-06` |
| `packages_build_independently` | x86 与 rv64 各自构建，不读对方目录 | `HE-AC-08`（H2 部分） |
| `a_package_without_a_spec_is_still_checked` | 新包不写进任何 `bundles/specs/*.json` → `verify --package` 仍给出确定性通过/失败 | `H2-D5`、§5.3 |
| `a_synthetic_package_without_legacy_source_is_accepted` | 沿用现有 ISA family、form ID 不在 legacy 目录 → 清单/目标/`read` 通过，证明协议不依赖历史定义 | §4.1 |
| `the_three_isa_harness_has_no_isa_branch` | harness 只读清单/用例数据；源码审查 + 测试覆盖三种包 | `HE-T14`（H2 部分） |
| `a_package_change_does_not_touch_legacy_roots` | `definitions/`、`fixtures/`、`payload_root` 不变 | `HE-AC-10`（H1 已证，H2 复跑） |

### 5.3 门禁

H2 每个提交至少通过：

- `cargo fmt --all -- --check`；
- `cargo test --workspace`（含新增的 `fmp-definition` 测试）；
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

普通扩展还需要独立门禁：

```text
cargo run -p fmp-definition -- verify --package <changed-package-path>
```

CI 从 PR diff 提取 `packages/**` 下的所有变更路径，映射到最近的含
`package.json` 的包根，逐个运行 `verify --package`；这条路径不要求包已被任何
spec 选中，也不改中心 `bundles/specs/`。只改 `forms/*.json` 而不改清单也会
触发检查。变更路径列表只决定跑哪些包，不决定构建器选择什么。
`verify --all` 覆盖发布组合，`verify --package` 覆盖作者单包；两者都列为 H2
退出门槛，不推迟到 H5。H2 不新增 per-package job matrix；单命令加 diff 提取
足够，完整 matrix 属于 `ADR-0130`。

## 6. 提交拆分

H2 是一个阶段，但按 `ADR-0125` §13.1 拆成两个可回归提交（同一 PR）：

| 提交 | 内容 | 必过 |
|---|---|---|
| H2a | `ADR-0128` 评审通过后接受 + 本文状态更新 + `fmp-definition` crate（manifest、spec、build、digest、error、CLI）+ `verify --package` 与变更路径门禁 + x86 `mov-register` 包 + 无 `legacy_source` 的合成包契约测试 + 构建器单测 + X86-P1 字节等价 + `bundles/` 的 x86 spec/lock/sealed/legacy snapshot + `gates.yml` 的 verify 两步 | fmt、workspace test、`check_ids`、`check_definition`、baseline、whitespace |
| H2b | aarch64 `add-immediate` + rv64 `integer-alu` + 三 ISA conformance harness + 包级 cases/evidence/NOTICE + `evidence/manifest.json` 与 release 摘要 + 全部 lock/sealed/legacy snapshot + `research/he1/H2-report.md` + `STATUS.md` 的 H2 记录 | 同上 + oracle |

H2a 必须先全绿再开 H2b：先证明一个包的构建、摘要和字节等价，再证明跨 ISA
与独立包。H2a 不引入 H2b 才需要的多包 harness；H2b 不修改 H1 的身份代码。

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
- `type`/`profile` 资产的执行或输出；非空声明在 H2 被拒绝（H4）。
- `bind` 接受 `VerifiedBundle`、`fmp-validate → fmp-definition` 依赖（H3）。
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
| O6 | 包用例格式 | **legacy fixture 引用 + 包内 `fmp-plan` 计划事实** 两种；H2 等价用前者，新包用后者 | 只做 fixture 引用会把包绑死在 legacy 语料上 |
| O7 | lock/sealed 是否提交 | **提交**，CI `--check` 重建；它们是发布产物，不是手写计数 | 只在测试里构建更轻，但发布 bundle 无法审计 |
| O8 | 三个包/forms 是否按 §4 表 | **按表**；已测量：x86 与 rv64 钉 `0.1.0`（前者行漂移，后者目标集合），aarch64 钉 `0.20.0` | 选更多 form 会增加等价面，不增加平台证明力 |
| O9 | `exports.types`/`profiles` 现在预留还是等新格式版本 | **现在预留**：键、`{id, path}` 形状、排序和摘要都定义；非空在 H2 以 `unsupported-asset` 拒绝 | 版本化延后更少代码，但会同时承诺封闭格式和无缝扩展 |
| O10 | H2 如何处理未知 `requires_capabilities` | **构建期拒绝**，只承认 `field-placement/v1`、`integer-domain/v1` | 只记录更宽松，但未知能力包会进入已验证快照 |
| O11 | 新包没有 `legacy_source` 时如何验证 | **包自述 `target_identity`/`definition_format` + `read` + 包用例**；用一个合成包证明不依赖历史定义 | 强制新包也写 legacy 来源会永久绑定旧目录 |

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
| `fmp-plan` 可用于包用例 | `fmp-plan/src/lib.rs` 有 `PlanBuilder` | 高（已读签名） |
| 构建器确定性、摘要分层、行相等、字节相等 | 尚未实现 | **未验证** — H2a/H2b 落地时测量 |
| `verify --package`、变更路径提取、未知能力/保留资产/双版本/聚合上限 | 尚未实现 | **未验证** — H2a |
| 证据摘要与 release 摘要分层 | 尚未实现 | **未验证** — H2a/H2b |
| 深层 JSON 鲁棒性 | H0 探针已测栈溢出；H2 不改 | **未验证/不在 H2** — H4 |
| 完整的 per-package CI matrix | 未实现；H2 只做单命令 | **未实现** — `ADR-0130`/H5 |

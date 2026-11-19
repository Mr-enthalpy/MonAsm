# H2 plan revision log (twelfth through twenty-sixth round notes)

> Historical evidence only. This file is not a contract, is never a build input,
> and must not be read as current normative text. The current plan is
> `docs/architecture/he1-h2-plan.md`; current decisions live in its §3 and in
> `docs/adr/0128-package-and-bundle-contract.md`. These notes were moved out of
> the plan opening by the twenty-fifth revision; the twenty-fifth and twenty-sixth
> round notes are added below.

Where a note conflicts with the current plan or ADR, the current document wins.
The twenty-sixth revision in particular moves the legacy bridge into the
`compat` module, renames the bundle type to `CheckedBundle`, requires the
published-directory audit to reject unreferenced non-regular entries, reconciles
the evidence and risk labels with the phase split, and separates build success
from artifact consistency.

## Round notes

  第二十六轮固定：H2 到 H1 的桥移出 bundle 类型，放进
  `fmp_definition::compat::as_legacy_definition`；`CheckedBundle` 只承诺结构与
  闭包检查，不承诺已发布、来源或 V-P，类型不再叫 `VerifiedBundle`。兼容函数是
  长期适配器，生命周期等于它所适配的 H1 `bind`，H3 另加 bundle 入口且不得由它
  组合；没有反向构造，`fmp-validate`/`fmp-materialize` 不依赖它。已发布目录的
  审计必须枚举每个目录项：未声明的符号链接、reparse point、FIFO、socket 或
  设备节点一律 `not-a-regular-file`（退出 1），不能因为普通文件集合未变而跳过。
  证据表与风险表按 `ADR-0128` §8.5 机械核对，硬化读取、发布登记、变更路径门禁
  与全历史审计不再标成 H2a。`--check` 只证明 `ArtifactsConsistent(T)`，不证明
  `BuildSucceeded(r)`：legacy 写失败后的缺失快照是合法的一致状态。
  第二十五轮固定：`empty-form-domain` 只适用于必须编码数值、没有 fixup/符号
  路径的槽位；`operand_value` 槽位可经 fixup 的 `Payload::Empty` 或 target 角色的
  `Payload::Symbol` 满足，构建器不得多拒绝；`an_empty_numeric_domain_with_a_fixup_path_is_not_rejected`
  与 `a_degenerate_legal_domain_needs_no_invented_positive` 分别守住两侧。
  2026-11-19 的 `protected:false`、空 ruleset 与 403 记为缺失证据；作者层 PR
  触碰率与发布 PR 串行成本是两个规模指标，不合并成一条结论。
  第二十四轮固定：H3 的子集目标规则拆成两层——归属包的声明覆盖
  `E_package(owner(form(i))) ⊆ E_plan` 对每条选中指令**无条件**生效；逐 form 需求
  只在版本化契约证明完整时作为**附加合取项**，永远不能替代保守覆盖。V-P 首次启用
  时，第一个发布候选重新验证并登记当时 HEAD 选中的**全部** spec（不只是 x86 切片）。
  规范摘要不再保留已被取代的 sealed 伴随规则，变更路径示例分开「合并前预防」与
  「合并后检测」。
  第二十三轮固定（取代第二十一、二十二轮关于 sealed 形状与 N1 时序的结论）：
  H2 分两个验收结论——**作者层 V-A** 与**发布通道 V-P**（`ADR-0128` §8.5）。
  V-A 只证明包能独立定义、校验、构建并产生相同机器事实，不依赖外部门禁；
  V-P 才承担不可信路径读取、不可变发布记录、合并竞态与全历史审计。V-A 可在
  V-P 前置条件尚未取到时推进，但任何产物在 V-P 通过前都不是「已发布、不可变或
  可信」。`monasm-bundle/0.1` 因从未发布而只冻结一次：恰好九个键，含 bundle 级
  `target`、逐包 `enabled_extensions` 覆盖与逐 form 的 `form_owners`，其
  `bundle_digest` 可由 sealed 文件独立重算，H3 消费这些事实而不引入第二个
  bundle 版本。发布登记项增加 `snapshot_digest`（覆盖整个版本目录的普通文件），
  使 `verify --published --check` 不必依赖变更路径门禁才能发现 `README`/
  `NOTICE`/用例/证据的改动；剩余信任边界（首值来源、历史重写）写在 ADR §8.4。
  单文件注册表与 O(N) 全历史审计是**明确的规模边界**，不是性能脚注。边界正例按
  `D_form` 基数取值（0 拒绝、1、2、≥3），空合法域是 `empty-form-domain`。
  N1 三平台 PoC 仍是独立的先决交付物，但只先于**硬化读取器**（V-P 的第一项），
  不先于作者层的可信树读取。
  第二十二轮固定（sealed 键集与 N5 时序部分已由第二十三轮取代）：包作者并行
  开发与并行发布是两种能力：H2 只给前者打基础，并保证发布在串行化下正确，
  不保证无协调并行发布。`builder` 是信息性来源记录，改动它可以不使
  `--all --check` 失败，因此它不证明构建来源。N5 不能以绿色 CI 关闭门禁，必须
  记录实际生效的 merge 机制并执行 stale-CI 反例，不能用合并后审计替代——该
  节点现在属于 V-P，不再阻塞 V-A。
  第二十一轮固定（sealed 形状部分已由第二十三轮取代）：单文件
  `bundles/published.json` 保留全量历史审计，但以约 1,000 个已发布版本的
  实测成本（时间/内存/读取字节，各三次）和明确的优化阈值为准，不把全局登记
  当作已证明的可扩展性；该测量属于 V-P。
  第二十轮固定（其中「`monasm-bundle/0.1` 没有归属映射」已由第二十三轮取代，
  逐 form 需求语义由第二十四轮收紧）：H3 的子集目标必须逐指令无条件检查归属包
  覆盖 `E_package(owner(form(i))) ⊆ E_plan`，逐 form 需求只在版本化契约证明其
  完整时作为附加合取项，不能替代保守覆盖；证据来自冻结的 bundle 归属/覆盖映射；
  `form_owners` 与逐包 `enabled_extensions` 现已进入
  `monasm-bundle/0.1` 并在 `bundle_digest` 内，只加 `fmp/0.2` 不放宽；无归属
  证明的 legacy form 默认拒绝，不按空集推定。发布门禁的键改为
  `(B_checked, C_checked, mode)`：基线提交 SHA、
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

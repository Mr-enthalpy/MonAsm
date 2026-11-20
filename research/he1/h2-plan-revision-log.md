# H2 plan revision log (twelfth through thirty-first round notes)

> Historical evidence only. This file is not a contract, is never a build input,
> and must not be read as current normative text. The current plan is
> `docs/architecture/he1-h2-plan.md`; current decisions live in its §3 and in
> `docs/adr/0128-package-and-bundle-contract.md`. These notes were moved out of
> the plan opening by the twenty-fifth revision; the twenty-fifth through
> thirty-first round notes are added below.

Where a note conflicts with the current plan or ADR, the current document wins.
The twenty-ninth revision makes `target_profile`/`profile_id` descriptive
labels that never decide composition, defines affected-set and full conformance
modes with the `Σ C_i` scaling boundary, and scopes the compat adapter to the API
layer. The thirty-first revision adds `C(T)` (artifact closure with no orphan derived
artifact), `H(T)` (an existing registry audited over every registered version),
pre-merge `Q(B,T,e)`, and post-merge `P(B,T,e,M)`. The thirtieth revision replaced
`P(T)` with `P(B,T,e,M)`, kept `R(T)` tree-only, separated the audit's three
claims, and ordered publication as N4b/N5a/N5b.

## Round notes

  第三十一轮固定：发布门禁写成可分别测试的谓词：`C(T) = A(T) ∧ NoOrphan(T)`
  覆盖每个选中 spec 的 lock/sealed 配对并拒绝无 spec 的孤儿派生产物；
  `H(T) = RegistryExists ∧ RegistryWellFormed ∧ HistoryAudit` 要求登记表存在、
  格式合法，并对全部登记版本（含已退役、当前无 spec 引用的版本）重算
  `snapshot_digest` 与来源；没有登记表的开发树 `R(T)` 真但 `H(T)` 假，因此不再
  满足发布门禁。合并前候选就绪是
  `Q(B,T,e) = C(T) ∧ R(T) ∧ H(T) ∧ PreservesPublished(B,T)`，合并后才有
  `P(B,T,e,M) = Q(B,T,e) ∧ AuthorizedMerge(B,T,e,M)`；报告不得把 `Q` 写成 `P`。
  新增三个反例：无 registry 的开发树不是发布就绪、当前 spec 全绿但退役版本被改
  导致 `H` 假、当前 spec 全绿但孤儿 sealed 使 `C` 假。V-P 结论不得用 CI 全绿
  代替 N1b PoC、平台合并机制记录与 stale-CI 反例；H2c 增加第四个规模指标
  `T_ordinary_PR,total(N_packages, N_published)`，分列 conformance、spec 验证与
  全历史审计的贡献，把「不改中央文件」与「等待不随全局规模增长」分开证明，不要求
  H2 立即实现增量审计。
  第三十轮固定：`monasm-bundle/0.1` 的九键 sealed 已携带并由 `bundle_digest`
  绑定 `form_owners` 与 `packages[].enabled_extensions`；H3 只新增计划兼容规则
  与验证入口，不再新增 sealed 格式或 companion source。发布审计拆成三个互不
  替代的命题：`snapshot_digest` 重证当前目录字节与条目集一致；变更路径门禁在
  合并前禁止改已发布版本；受保护合并机制证明落地操作经过授权，审计本身不证明
  来源可信或历史未被重写。发布谓词改为
  `P(B,T,e,M) = A(T) ∧ R(T) ∧ PreservesPublished(B,T) ∧ AuthorizedMerge(B,T,e,M)`；
  `R(T)` 只依赖树（无登记表时为真），删除 base 登记属于 `PreservesPublished`
  失败而不是 `R` 依赖过去。`build` 成功只推出本次 bundle 的 `A_β(T_r)`，全树
  `A(T_r)` 由 `verify --all --check` 另行证明。发布顺序拆成 N4b（格式/审计代码/
  合成测试，不提交真实 registry）、N5a（建立并验证受保护合并机制，不首次发布）、
  N5b（经该通道首次发布全部 HEAD spec）；修改发布门禁的 PR 不能用自己的绿色 CI
  为自己授权。平台保护证据的责任归 H2b N5a，失败只停 V-P，不否定已通过的 V-A。
  第二十九轮固定：`target_profile` 与 `target.profile_id` 都是描述性名义标签，
  仍进入各自清单/摘要，但构建器不比较二者；组合只由 `definition_format` 与六键
  `target.identity` 决定，`two_packages_with_equal_target_identity_and_distinct_profile_labels_can_compose`
  固定「identity 相同、标签不同也能组合」。若要让标签成为需要事先协调的全局承诺，
  必须版本化并明确写出。conformance 分两种模式：普通 package-only PR 跑变更包加
  显式 `dependencies` 可达的受影响集；读取器/验证器/物化器/路径层/harness 变更、
  发布门禁与定期任务跑全量，成本 `Σ C_i` 写成规模边界，H2c 增记作者 PR 的
  conformance 耗时。`compat::as_legacy_definition` 表述为 `fmp-definition` 提供的
  唯一具类型 H1 适配 API，不是系统级排他性（`bundle_json()` 加
  `definition::read` 可绕过，但无 bundle 证据）。
  第二十八轮固定：`BuildSucceeded(r, β)` 只推出 `A_β(T_r)`（该 bundle 的工件
  配对），不推出 `A(T_r)`（全树合取）——另一个 spec 的 lock 过期时构建仍成功，
  `a_single_bundle_build_does_not_prove_the_whole_tree` 固定该方向。`R(T)` 拆成
  `R_packages ∧ R_identities`，只读登记表已有字段；`release_digest` 在 lock 里由
  `A_β` 重算，登记表没有也不新增该字段。「仅证据变化、`bundle_digest` 不变」只
  存在于未发布候选；已发布目录改证据必须换版本，`bundle_digest` 随之改变。快照
  目录的每个条目（含未被引用的普通文件）都受 §1.3 词法、设备名与折叠唯一性约束，
  `an_unreferenced_case_fold_collision_in_a_published_directory_is_rejected` 固定
  该规则。合并模式 `mode(M)` 取自平台合并记录并保存事件标识，不由提交对象反推。
  第二十七轮固定：`BuildSucceeded(r)` 只推出 `A(T_r)`（工件配对），不推出
  `R(T_r)`（登记完整）或 `P(T_r)`（发布就绪）；已有登记表时，新 spec 在追加行
  之前 `--all --check` 报 `published-registry-incomplete`，
  `a_successful_build_does_not_complete_the_registry` 固定该中间状态。ADR 的
  `accepted` 改为 PR #4 合并后的独立 docs-only H2-0 接受变更，H2a 不携带也不
  依赖自己的启动前提。发布结论还要记录门禁逻辑来源：workflow、变更路径 mapper
  与审计脚本来自受保护控制面或独立审批，否则写明信任假设；head 改过的门禁不能
  为同一 PR 授权。H3 的 bundle 入口只保证经它执行的计划，旧 `bind` 仍是公开的
  legacy 能力，字节相同不等于证明强度相同。
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

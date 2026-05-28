# DocFlow Lite 需求规格说明书

## 1. 文档目的

本文档定义 DocFlow Lite 的产品目标、业务边界、核心流程、领域对象、功能需求和验收标准。

DocFlow Lite 是一个个人化的文档智能处理平台，用于把 PDF、Excel、图片、文本等非结构化或半结构化文档转换成稳定的结构化 JSON，并把结果交付给下游系统。

系统必须是独立实现：使用自己的产品名称、代码、数据模型、页面结构和视觉资产。不得复制参考平台源码、品牌素材、内部标识或专有文案。

## 2. 需求理解

这个产品的核心不是“上传一个文件然后让模型抽字段”这么简单，而是一个多层级、多轮反馈的文档理解平台。

正确的业务抽象应是：

1. Tenant 是最上层业务容器。
2. Tenant 下有多个 Workspace。
3. 每个 Workspace 代表一种文档类型、一个目标 Schema 和一套抽取规则。
4. Workspace 初始化时，用户先定义 Expected Output，再进入独立的 Samples 页面维护样本表。
5. Samples 页面以表格展示每个上传文件，每个样本都可以抽取、纠正和确认。
6. 用户基于已确认样本行生成 Prompt Version；内部会把当前样本批次发布为只读版本。
7. 已发布样本批次不可再新增、删除或修改样本；如需迭代，必须复制出新的草稿批次。
8. 大模型根据“冻结样本版本 + 期望 JSON + 用户定义的 Schema + 纠正结果”总结如何抽取数据。
9. 用户继续上传验证文档，系统输出 JSON。
10. 用户可以纠正输出。
11. 系统把纠正结果纳入新的样本草稿版本，继续优化 Prompt、字段规则和抽取策略。
12. 多轮迭代后，当输出足够稳定，Workspace 才可以激活。
13. 激活后，Workspace 用于正式文档抽取和集成交付。

因此，系统必须围绕“租户管理、Schema 工作区、样本学习、Prompt 版本、抽取任务、集成流程”进行架构，而不是把所有逻辑堆在路由函数或单个页面组件里。

## 3. 基于 cdas Workspace 的实操观察

对 `cdas` Workspace 实际操作后，确认参考流程的关键机制如下：

1. Workspace 归属于 Tenant。
2. Workspace 详情页左侧导航包含 Configuration、Extracted Result、API Access 等区域。
3. Configuration 下包含 Initialization 和 Integration。
4. Initialization 不是一个普通表单，而是一个四阶段流程：Expected Output、Validation、Sample、Prompts Editing。
5. Expected Output 阶段直接定义模型应该返回的 JSON 或 JSON Array 结构，不再暴露 Header Group 和 Line Items 概念。
6. 字段类型至少包含 string、number、boolean、date、json、jsonArray。
7. 字段有 Required 开关。
8. Validation 阶段不是上传文件，而是对字段定义校验规则，例如 Regex Pattern 和 Ignored 开关。
9. Sample 阶段才是样本文档列表，提供 Upload、Extract、Analyze 操作。
10. 样本文档列表状态包含 To Review。
11. 样本文档详情页是人工校正页面，左侧按 Schema 分组展示抽取字段，右侧展示原始文档预览。
12. 用户可以直接修改字段值。
13. 字段被修改后才允许添加 note。
14. 样本详情页提供 Reject 和 Confirm。
15. Confirm 后样本才应进入可分析或可接受状态。
16. Analyze 需要选中样本文档后才能执行。
17. Prompts Editing 依赖前面样本分析结果，没有完成分析前不能有效进入。
18. Integration 页面默认只有 Start 节点。
19. Start 节点展示系统变量：sys.workspaceId、sys.extractionId、sys.documentId。
20. Start 节点支持 Custom Parameters，类型包含 String 和 Dict。
21. Start 节点有 Duplicated Document Processing 全局开关。
22. Extracted Result 页面只展示正式处理任务；Workspace 未激活时提示需要先完成 Initialization 激活。
23. API Access 页面展示 API Server、WorkspaceId、API Key、同步抽取接口、异步抽取接口和查询结果接口。

这些观察说明：我们自己的实现需要同时支持两种输入路径：

1. 简洁配置路径：先人工定义期望输出结构，再通过样本抽取和字段级纠正优化 Prompt。
2. 增强式路径：用户直接给出“样本文档 + 期望 JSON”，系统自动推导 Schema 草案和 Prompt 草案。

增强式路径不能破坏主流程，而应作为 Expected Output / Sample 阶段的高级入口。

## 4. 产品目标

DocFlow Lite 需要实现一套完整闭环：

1. 创建 Tenant。
2. 在 Tenant 下创建 Workspace。
3. 一个 Workspace 对应一个文档 Schema。
4. 用户先定义期望输出字段和校验规则，再到 Samples 页面上传样本文档。
5. Samples 页面必须以表格呈现每个上传文件，支持查看模型输出、人工纠正、Confirm、Remove。
6. Confirm 后的样本可以生成可维护、可版本化、可激活的 Prompt Version。
7. 激活 Workspace。
8. 使用激活后的 Workspace 处理正式文档。
9. 配置文件入口、调度、字段映射和目标系统。
10. 查看抽取任务、状态、错误和下载结果。

默认模型提供方为本地 Ollama，但系统必须支持切换模型提供方。

## 5. 层级模型

### 5.1 Tenant

Tenant 是顶层业务隔离单元。

Tenant 负责承载：

1. Tenant 基础信息。
2. Tenant 级模型设置。
3. Tenant 下的 Workspace 列表。
4. Tenant 级变量和默认配置。
5. 后续可扩展的成员、角色、计费和监控能力。

当前阶段不实现权限控制，但必须保留 Tenant 这个领域对象，因为它决定 Workspace 的归属边界。

### 5.2 Workspace

Workspace 是一个文档类型的工作区。

一个 Workspace 应该代表：

1. 一个文档场景。
2. 一个目标 Schema。
3. 一组训练样本。
4. 一组样本批次版本（内部实体为 Training Example Set Version；前端显示为 Sample batch）。
5. 一组 Prompt Version（内部实体为 Prompt Profile）。
6. 一套正式抽取任务。
7. 一套可选集成流程。

例如，一个 Tenant 可以有多个 Workspace：

1. 采购订单 Workspace。
2. 发票 Workspace。
3. 交付单 Workspace。
4. 自定义业务文档 Workspace。

每个 Workspace 的 Schema、样本、Prompt、集成配置相互独立。

### 5.3 Schema

Schema 是 Workspace 的核心输出契约。

Schema 描述系统最终要输出的结构，包括：

1. 根输出类型：JSON object 或 JSON array。
2. 字段名称。
3. 字段类型：string、number、boolean、date、json、jsonArray。
4. 是否必填。
5. 字段说明。
6. 嵌套 JSON 或 JSON Array 子字段。
7. 字段级校验规则，包括 Regex、最小/最大值、最小/最大/固定长度、禁止中文和硬性 Pattern。
8. 字段级忽略规则。

Schema 必须支持版本化。每次用户明显修改目标 JSON 或字段结构时，应形成新的 Schema Version。

### 5.4 Training Example

Training Example 是初始化学习闭环中的样本。

一个 Training Example 至少包含：

1. 原始文档。
2. 文档解析后的文本或表格内容。
3. 用户提供的期望输出 JSON。
4. 模型实际输出 JSON。
5. 用户纠正后的 JSON。
6. 模型使用的 Prompt 版本。
7. 校验状态。
8. 人工确认状态。
9. 字段级 note。

Training Example 是模型总结抽取规则和 Prompt 的核心依据。

### 5.5 Sample Batch（Training Example Set Version）

Sample Batch 是一组样本的版本化集合；内部领域实体名为 Training Example Set Version，前端对业务用户显示为 Sample batch。

一个 Sample Batch 至少包含：

1. version。
2. status：draft 或 published（内部枚举仍为 draft/frozen）。
3. 关联的 Training Example 列表。
4. 关联的 Prompt Version（内部实体为 Prompt Profile）。
5. 创建和更新时间。

规则：

1. draft 批次允许新增样本、删除样本、纠正样本和重新确认。
2. published 批次不可再变更样本，是生成 Prompt Version 的稳定输入。
3. published 批次可以复制成新的 draft 批次，用户在新批次上新增、删除或修改样本。
4. 每次从 draft 批次生成 Prompt Version 时，都应发布该批次并生成新的 Prompt Profile 版本。
5. Prompt Profile 必须能追溯到它使用的 Sample Batch。

### 5.6 Prompt Profile

Prompt Profile 是某个 Workspace 在某个 Schema Version 下的抽取策略。

Prompt Profile 至少包含：

1. system prompt。
2. extraction instruction。
3. expected JSON structure。
4. published Sample Batch。
5. few-shot examples。
6. field-level rules。
7. output validation rules。
8. model provider 和 model name。
9. version。

Prompt Profile 必须可编辑、可保存、可重新生成、可激活。

## 6. 当前范围

### 6.1 必须实现

1. Tenant 管理。
2. Workspace 管理。
3. Workspace 初始化。
4. Schema 定义和版本。
5. 文档解析。
6. Samples 独立页面。
7. 一个 Sample Batch 内上传多个样本文档，页面以表格展示每个上传文件。
8. 每个样本可抽取、纠正、Confirm / Reject。
9. Sample Batch 发布、复制为新草稿、删除样本和新增样本。
10. 期望 JSON 输入。
11. 模型总结抽取规则。
12. 模型抽取验证。
13. 用户纠正 JSON。
14. 样本学习闭环。
15. Prompt 生成、编辑、版本化。
16. Workspace 激活。
17. 正式文档抽取。
18. 抽取结果列表和详情。
19. 模型设置和模型切换。
20. 集成流程配置。
21. 变量引用。
22. API Access 说明。
23. 字段级 Regex 校验。
24. 字段级硬约束校验，包括金额范围、料号长度、禁止中文和业务 Pattern。
25. 字段级 note。
26. 样本 Reject / Confirm。
27. 同步抽取 API。
28. 异步抽取 API。
29. 抽取结果查询 API。
30. 管理员观测台，用于查看请求输入、输出、中间结果、耗时和错误链路。
31. 可复现的处理 Trace，用于调试、性能优化和模型效果回放。
32. 文档级上下文输入，用于在单次 PDF、Excel、图片或文本抽取时补充业务解释。
33. 字段硬约束失败后的模型修复循环：把原文、上次输出和校验错误重新交给模型修正；二次失败进入 correction_required。
34. 文档归一化层：对于 PDF，系统必须先截图前几页并把图片直接输入 Document CLS 识别文档类型（Invoice / Contract / Paper/Doc），随后按类型路由到不同归一化流程；对于 Excel、图片和文本，继续走统一归一化入口。所有流程都必须保留来源 hash、warning、trace 和可追溯 metadata。

### 6.2 当前暂不实现

1. 复杂权限系统。
2. 企业身份认证。
3. 多租户权限隔离。
4. 计费。
5. 生产级任务队列。
6. 真实邮件服务器拉取。
7. 真实共享盘监听。
8. 生产级对象存储。
9. 审计报表。

## 7. 用户角色

当前阶段只有一个默认角色：Tenant Owner。

Tenant Owner 可以：

1. 创建和切换 Tenant。
2. 创建 Workspace。
3. 定义 Schema。
4. 上传样本文档。
5. 输入期望 JSON。
6. 触发模型分析。
7. 纠正模型输出。
8. 生成和编辑 Prompt。
9. 激活 Workspace。
10. 配置集成流程。
11. 查看抽取结果。
12. 修改模型设置。
13. 查看管理员观测台。
14. 按请求、任务、Workspace、Prompt Profile 和模型调用检索处理轨迹。
15. 复现某一次处理请求，比较不同 Prompt Profile 或模型配置下的输出差异。

## 8. 核心业务流程

### 8.1 Tenant 创建和切换流程

1. 用户进入 Tenant Center。
2. 用户查看 Tenant 列表。
3. 用户创建 Tenant 或选择已有 Tenant。
4. 系统进入该 Tenant 的 Workspace 首页。
5. 后续所有 Workspace、Schema、样本和集成都归属于当前 Tenant。

### 8.2 Workspace 创建流程

1. 用户在当前 Tenant 下点击 Create Workspace。
2. 用户输入 Workspace 名称。
3. 用户可以手工输入业务描述，也可以先留空。
4. 系统创建 Workspace，并默认使用自定义业务 Schema，不要求用户选择预置 Schema Type。
5. Workspace 默认状态为 Inactive。
6. 系统进入 Workspace 初始化页面。
7. 用户可上传 PDF、Excel、文本或截图等背景资料，系统提取可用文本并调用模型总结 Workspace 初始业务描述。
8. 在正式抽取或 Prompt 分析前，Workspace 必须具备业务描述；该描述进入模型上下文。

### 8.3 Schema 初始化学习流程

1. 用户进入 Workspace Initialization。
2. 用户在 Expected Output 阶段选择根输出类型：JSON object 或 JSON array。
3. 用户配置字段名、字段类型、Required，并可为字段增加嵌套 JSON 或 JSON Array 子字段。
4. 用户也可以上传或粘贴期望 JSON，由系统推导 Schema 草案。
5. 用户在 Validation 阶段为字段配置 Regex Pattern、Ignored 和可选硬约束。
6. 用户进入独立的 Samples 页面。
7. 系统默认提供一个 draft Sample Batch。
8. 用户在 draft 批次内上传多个样本文档；每个上传文件在表格中形成一行，并可为本次上传输入额外上下文说明。
9. 系统先执行文档预检；若为 PDF，先截图前几页并将图片输入 Document CLS（候选类型：Invoice、Contract、Paper/Doc）后按类型路由归一化；非 PDF 走标准归一化。
10. 系统按路由后的归一化结果（如 KV 结构、Markdown chunks 或 reading chunks）、当前 Schema 与合并后的业务上下文执行初始抽取。
11. 系统对模型输出执行 Schema 与字段硬约束校验。
12. 如果校验失败，系统把原文、原始提示词、上次输出和校验错误重新交给模型修复；二次仍失败则进入 correction_required。
13. 用户进入样本详情页查看原始文档预览和字段级抽取结果。
14. 用户直接修改字段值或输入完整期望 JSON。
15. 用户可以对修改后的字段添加 note。
16. 用户 Reject 或 Confirm 每个样本。
17. Confirm 后样本进入当前 draft 版本的可冻结集合。
18. 用户从当前 Sample Batch 生成 Prompt Version。
19. 系统基于当前批次中的 confirmed samples、Schema、文档内容、模型输出、用户纠正值和 note 生成 Prompt Profile。
20. 已发布批次不可再新增、删除或修改样本。
21. 用户可复制已发布批次生成新的 draft 批次，再新增、删除或修改样本，生成后得到新的 Prompt Version。
22. 用户进入 Workspace 二级菜单中的 Prompt Versions 页面，查看、对比、编辑和保存 Prompt Profile。
23. 用户在 Prompt Versions 页面选择某个版本并激活；激活版本成为该 Workspace 正式抽取和 API 调用使用的版本。
24. 用户用新的 Prompt Profile 对样本文档或验证文档再次抽取。
25. 重复 clone、修改样本、冻结和验证，直到输出稳定。
26. Workspace 进入 Active 状态。

### 8.4 正式文档处理流程

1. 用户在 Active Workspace 上传正式文档，或通过 API 创建任务。
2. 用户可为本次文档输入上下文信息，例如来源系统、业务场景、金额范围、供应商提示或特殊术语。
3. 系统把 Workspace 业务描述和本次文档上下文合并为模型上下文。
4. 系统执行文档归一化；PDF 场景先做 Document CLS 再分流：Invoice 走 KV Pipeline，Contract 走 Markdown+LLM，Paper/Doc 走 Reading Pipeline。
5. 系统使用当前 Active Prompt Profile 与分流后的输入上下文执行抽取（Invoice 输出结构化 JSON；Contract 输出 Summary/QA；Paper/Doc 进入 RAG 读写链路）。
6. 系统校验输出 JSON 是否符合 Schema 和字段硬约束。
7. 校验失败时系统触发一次模型修复；修复后仍失败则任务进入 correction_required 或 Incomplete。
8. 校验通过则任务变为 Completed。
9. 模型或解析失败则任务变为 Processing Error。
10. 下游同步失败则任务变为 Sync Error。
11. 用户在 Extracted Result 页面查看、下载或重新处理结果。

### 8.5 集成配置流程

1. 用户进入 Integration 页面。
2. 用户查看 Start 节点中的系统变量和自定义变量。
3. 用户配置 File Entrance。
4. 用户配置 Job Scheduler。
5. 用户配置 Mapping。
6. 用户配置 Destination。
7. 用户点击 Activate。
8. 系统执行结构化激活校验。
9. 校验通过后集成变为 Active。
10. 校验失败时返回所有 issue，不激活。

### 8.6 管理员观测和复现流程

1. 管理员进入 Admin Observability 页面。
2. 管理员按时间、Workspace、请求 ID、任务 ID、文件名、状态、模型 provider、模型名称或 Prompt Profile 过滤请求。
3. 管理员打开某一次请求详情。
4. 系统展示该请求的完整处理链路，包括上传输入、预检结果、解析结果、chunk 列表、ContextPackage、模型调用、模型原始输出、合并结果、校验结果、最终响应和错误信息。
5. 系统展示每个阶段的开始时间、结束时间、耗时、状态、输入摘要、输出摘要和关联对象 ID。
6. 管理员可以查看模型调用的 system prompt、业务上下文、SchemaVersion、PromptProfile、few-shot examples、候选 chunk、token 预算和 token 使用估算。
7. 管理员可以基于已保存 Trace 复现请求，保持原始输入、PromptProfile、SchemaVersion、模型配置和 ContextPackage 不变。
8. 管理员可以复制请求生成对比运行，例如切换 Prompt Profile、模型名称、chunk 策略或上下文预算，并查看输出 JSON、耗时、token 估算和错误差异。
9. 复现和对比运行必须生成新的 Trace，不能覆盖原始请求 Trace。

## 9. 功能需求

### FR-001 Tenant 首页

系统应提供 Tenant 列表和 Tenant 切换入口。当前阶段可以默认创建一个本地 Tenant，但前端和后端模型都必须支持多个 Tenant。

### FR-002 Tenant 创建

系统应允许创建 Tenant。Tenant 名称必填，描述可选。

### FR-003 Workspace 首页

系统应展示当前 Tenant 下的 Workspace 卡片。卡片展示名称、描述、文档类型、状态、创建时间和更新时间。

### FR-004 Workspace 搜索和过滤

系统应支持按名称、描述和 Active 状态过滤 Workspace。

### FR-005 Workspace 创建

用户应能在当前 Tenant 下创建 Workspace。Workspace 名称必填，业务描述可手工填写或由背景文件自动总结；业务描述必须在模型处理前存在，并进入模型上下文和 Prompt Profile。创建时不要求选择 Schema Type。

### FR-006 Workspace 等于 Schema 容器

每个 Workspace 必须对应一个主要 Schema。这个 Schema 是正式抽取输出 JSON 的契约。

### FR-007 Expected Output 定义

用户应能通过表单或 JSON 输入定义期望输出结构。系统只暴露业务可理解的输出类型：根节点为 JSON object 或 JSON array；字段类型为 string、number、boolean、date、json、jsonArray。

json 字段表示嵌套对象，jsonArray 字段表示对象数组。系统不应再要求用户理解 Header Group、Line Items、字段组或表格明细等概念。

Schema 表单模式必须支持字段类型、Required 开关、Regex Pattern、Ignored 开关和递归嵌套字段。

每个字段还应支持类型匹配的可选硬约束：number 字段支持 min/max，string/date 字段支持 Regex Pattern、minLength/maxLength/exactLength/pattern。硬约束不是提示词建议，而是模型输出后的强制校验条件。

### FR-008 期望 JSON 输入

用户上传样本文档后，必须能输入该文档的期望输出 JSON。系统应校验 JSON 格式。

### FR-009 文档归一化

系统应支持 PDF、Excel、CSV、TXT、JSON、图片等文件归一化。归一化能力必须通过 DocumentNormalizer 接口扩展，不允许业务逻辑直接依赖某一个 parser。抽取文档、Training Example 和 Workspace 背景文件必须进入同一归一化入口，不允许背景文件绕过归一化层直接抽 raw text。

系统必须提供 Workspace-aware Normalizer Registry。Registry 选择 normalizer 时至少能读取 workspace id、schema type、业务描述、处理目的（抽取、背景总结、样本训练等）、文件名和 MIME type；不同 Workspace 可以配置或扩展不同 parser / normalizer / OCR 策略。

PDF 必须执行“先分类、再分流”策略，流程如下：

```text
             ┌──────────────────┐
PDF ─────→   │ 前几页截图(PageShots) │
             └────────┬─────────┘
                      │
               ┌──────▼───────┐
               │ Document CLS │
               └──────┬───────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
   Invoice         Contract        Paper/Doc
      │               │               │
   KV Pipeline    Markdown+LLM    Reading Pipeline
      │               │               │
    JSON          Summary/QA         RAG
```

Document CLS 的输入为 PDF 前几页截图（图片），并在 prompt 中显式告知候选类型：Invoice、Contract、Paper/Doc。分类结果由代码决定后续归一化策略，不由前端人工选择。

归一化输出必须至少包含：

1. canonical Markdown，作为 LLM 的主要文档输入。
2. block metadata，包括 block type、页码或 sheet 范围、坐标或来源范围。
3. table metadata，包括表格 Markdown、行列结构、合并单元格和置信信息。
4. assets metadata，包括原始文件 hash、页图或截图引用。
5. parser trace，包括 normalizer 名称、版本、耗时、warning 和 confidence。

Marker 可以作为 PDF 到 Markdown 的首个 adapter，但系统必须保留 adapter 抽象，支持后续替换为 OCR、Excel 或自研 parser。对于 born-digital PDF，系统应优先使用嵌入文本和布局信息；只有扫描件、图片型页面或低质量页面才进入 rasterize/OCR 路径。

### FR-010 样本文档上传

用户应能在独立的 Samples 页面上传多个样本文档。每个样本文档形成一个 Training Example，在页面表格中成为一行，并加入当前 draft Sample Batch。

如果当前 Sample Batch 已发布，系统必须拒绝新增样本，并提示用户先复制为新的 draft 批次。

### FR-011 模型规则总结

系统应把已发布 Sample Batch 中的 confirmed samples、样本文档内容、目标 Schema、期望 JSON 和用户纠正结果提供给模型，让模型总结抽取策略并生成 Prompt Profile。

### FR-012 抽取验证

用户应能选择样本或验证文档，用当前 Prompt Profile 执行抽取，查看模型输出 JSON。

### FR-013 人工纠正

用户应能修改模型输出。系统必须支持字段级纠正和完整 JSON 纠正两种方式。保存时系统必须校验 JSON 格式和 Schema 兼容性。

### FR-014 反馈闭环

用户纠正后的字段值、完整 JSON 和 note 应保存为 Training Example 的 corrected_output 与 correction_notes，并可作为下一轮 Prompt 生成的输入。

### FR-014A Sample Batch 版本化

系统必须支持 Sample Batch 版本化；内部实体可以继续命名为 Training Example Set Version，但前端必须用业务可理解的 Sample batch / Draft / Published：

1. Draft 批次允许新增样本、删除样本、纠正样本和确认样本。
2. Published 批次是只读版本，不能新增、删除或修改样本。
3. 用户可以从 Draft 批次生成 Prompt Version；该动作发布当前批次并生成新的 Prompt Profile。
4. 用户可以把 Published 批次复制成新的 Draft 批次。
5. 新 Draft 批次可以新增样本、删除样本、修改样本纠正结果，再生成新的 Prompt Profile。
6. Prompt Profile 必须记录其来源 Sample Batch，保证效果可追溯。

### FR-015 Prompt Profile 版本化

每次模型分析生成的 Prompt Profile 必须有版本号、状态和创建时间。系统必须提供独立的 Prompt Versions 页面，让用户查看历史版本、选择某个版本作为当前使用版本、激活该版本，并对比两个版本的提示词、样本数、字段数、模型配置和抽取效果。

某个版本的使用规则：

1. published Sample Batch 生成 Prompt Profile version。
2. 用户在 Prompt Versions 页面点击 Use / Activate。
3. 该版本写入 Workspace 的 active_prompt_profile_id。
4. 后续正式抽取、同步 API、异步 API 和验证抽取默认使用该 active version。
5. 切换版本必须记录 Trace，便于复现当时使用的是哪个 Prompt Profile。

### FR-016 Workspace 激活

只有满足以下条件，Workspace 才能激活：

1. 已定义 Schema。
2. 至少存在一个 published Sample Batch。
3. published Sample Batch 内至少存在一个 confirmed Training Example。
4. 至少存在一个 Prompt Profile。
5. 有一个 Prompt Profile 被标记为 Active。
6. 最近一次验证没有阻断级错误。

### FR-017 模型设置

系统应支持配置模型提供方、base URL、model name 和 options。默认提供方为本地 Ollama。

### FR-018 模型 Provider 扩展

模型调用必须通过 ModelProvider 接口完成。业务服务不得直接依赖某个具体模型实现。

### FR-019 Extracted Result 列表

系统应展示正式抽取任务列表，支持任务名搜索、时间范围过滤、状态过滤和分页。

### FR-020 Extracted Result 状态

任务状态至少包含 Ready、Extracting、Completed、Incomplete、Processing Error、Sync Error、Failed。

### FR-021 Extracted Result 详情

用户应能查看任务原文、解析内容、抽取 JSON、错误信息、使用的 Prompt Profile 和模型信息。

### FR-022 结果下载

用户应能导出选中任务的 JSON 结果。

### FR-023 Integration 工作流

系统应以 Start -> File Entrance -> Job Scheduler -> Mapping -> Destination -> Activate 的流程表达集成配置。

### FR-024 File Entrance

系统应建模 Manual Upload、API、Mailbox、Shared Folder 等入口类型。当前阶段可以先实现配置保存和手动触发。

### FR-025 Job Scheduler

系统应支持 Manual、One Time、Recurring。非 Manual 模式必须配置开始时间。

### FR-026 Mapping

系统应支持源 Schema、目标 JSON、字段映射、Transformation 和输出预览。Mapping 必须是结构化对象，不允许只保存不可解析文本。

### FR-027 Variable Reference

系统应支持系统变量和用户变量。变量引用必须可解析、可校验、可限制作用域。

### FR-028 Destination

系统应支持目标 URL、HTTP Method、Headers、认证方式、超时配置。OAuth2 模式必须配置必要字段。

### FR-029 Integration 激活校验

系统必须通过 Validator 对象执行集成激活校验。校验失败返回 issue 对象列表，每个 issue 包含 code、path、message、severity。

### FR-030 API Access

系统应提供 API Access 页面，展示当前 Workspace 的 API 调用方式，包括上传文档和查询结果。

API Access 至少需要覆盖：

1. 同步抽取接口。
2. 异步抽取接口。
3. 抽取结果查询接口。
4. API Key 使用说明。
5. Workspace ID 使用说明。

### FR-031 大文件上传预检

系统必须在文档进入抽取前执行预检，识别文件大小、页数、MIME 类型、扩展名、哈希、是否可能需要 OCR、是否超过同步处理阈值。

预检结果必须结构化保存，不能只返回一段不可解析文本。

### FR-032 大文件异步处理

大 PDF、大 Excel 或其他超过同步阈值的文件必须进入异步任务流程。同步 API 只能处理小文件或已解析缓存命中的文件。

异步任务应能展示处理阶段，例如 uploaded、preflighted、parsed、chunked、indexed、extracting、merging、validated、completed、failed。

### FR-033 文档分块

系统必须把 normalized Markdown 和 block metadata 拆成可追踪的 DocumentChunk。每个 chunk 至少包含页码或 sheet 范围、Markdown 内容、表格内容摘要、token 估算、来源坐标和 chunk 类型。

后续模型调用必须引用 chunk id，方便审计、调试和用户纠正。

### FR-034 上下文预算控制

系统不得把完整大文档直接塞进模型上下文。

每次模型调用前必须由 TokenBudgeter 计算上下文预算，至少预留以下空间：

1. system prompt。
2. Schema 输出契约。
3. 字段规则。
4. few-shot examples。
5. 候选文档 chunk。
6. 模型输出 JSON。

如果预算不足，系统必须通过裁剪示例、减少候选 chunk、字段分组抽取或分阶段抽取解决，而不是静默截断。

### FR-035 上下文装配

系统必须通过 ContextAssembler 生成 ContextPackage。ContextPackage 应记录本次模型调用使用的 PromptProfile、SchemaVersion、chunk 列表、字段范围、token 预算、模型 provider 和模型名称。

ContextPackage 必须可持久化或可复现，便于复盘模型为什么输出某个结果。

### FR-036 分阶段抽取

对于大文档，系统必须支持分阶段抽取：

1. 粗定位候选 chunk。
2. 按期望输出结构中的字段路径分组抽取。
3. 对多 chunk 结果进行合并。
4. 对合并后的 JSON 执行 Schema 校验。
5. 对冲突字段生成 issue，必要时进入人工纠正。

### FR-037 抽取合并和冲突处理

系统必须通过 ExtractionMerger 合并多个 chunk 的抽取结果。合并过程必须保留来源 chunk、置信信息、冲突字段和最终选择原因。

冲突不能被静默覆盖，必须进入 validation_result 或 correction_required 状态。

### FR-038 大文件处理可观测性

用户应能在样本详情或任务详情中看到大文件处理轨迹，包括解析页数、chunk 数量、模型调用次数、每次调用使用的 chunk、失败阶段和错误信息。

### FR-039 文档级上下文

用户上传样本或正式文档时，可以为本次文件输入文档级上下文。该上下文用于补充 Workspace 业务描述，进入本次模型调用，但不直接覆盖 Workspace 描述。

文档级上下文至少应支持：

1. 文档来源和业务场景说明。
2. 特殊术语、供应商、客户或产品提示。
3. 已知金额范围、日期范围、料号格式等业务线索。
4. 用户对解析歧义的说明。

### FR-040 字段硬约束和模型修复

系统必须在模型输出后执行字段硬约束校验。校验失败时，系统应构造修复请求，把原始文档上下文、原始提示词、上次模型输出和结构化 validation errors 一起交给模型重新生成 JSON。

修复循环要求：

1. 默认最多自动修复一次，避免无限模型调用。
2. 修复后仍失败时，结果状态必须明确为 correction_required 或 Incomplete。
3. 校验错误必须写入 Trace，供管理员观测台和人工纠正页面查看。
4. 修复请求必须要求模型只返回 JSON，不能返回 markdown 或解释文本。

### FR-041 大文件策略配置

Workspace 应支持处理策略配置，例如同步文件大小阈值、最大页数、chunk 大小、chunk overlap、候选 chunk 数量、每次模型调用最大 token 预算、是否启用分阶段抽取。

### FR-042 管理员观测台

系统必须提供 Admin Observability 页面，供管理员从请求和任务维度查看平台运行过程。该页面不是普通日志列表，而是面向调试和优化的可视化 Trace Explorer。

管理员观测台至少需要支持：

1. 按时间范围、Workspace、请求 ID、任务 ID、文件名、状态、模型 provider、模型名称、Prompt Profile 和 Schema Version 过滤。
2. 展示请求总览，包括入口类型、触发用户、Workspace、文件、最终状态、总耗时、模型调用次数、token 估算和错误摘要。
3. 展示阶段化 Timeline，包括 upload、preflight、parse、chunk、context assembly、model invocation、merge、validation、persist、response、sync 等阶段。
4. 每个阶段展示开始时间、结束时间、耗时、状态、输入摘要、输出摘要、错误信息和关联对象 ID。
5. 对耗时明显偏高、上下文预算接近上限、模型输出无法解析、字段冲突、校验失败等情况给出可视化标记。
6. 支持从 Trace 跳转到 Workspace、Prompt Profile、Schema Version、Extraction Result、Training Example 和原始文件。

### FR-043 请求输入输出和中间结果可视化

系统必须保存并可视化每次处理请求的关键输入、输出和中间结果，方便定位模型效果、解析质量、上下文裁剪和合并策略问题。

每次请求至少需要可视化：

1. 原始请求输入：文件名、MIME、大小、hash、入口来源、API 参数、模型配置快照。
2. 预检输出：页数、sheet 数、处理模式、拒绝或异步原因。
3. 归一化输出：Markdown preview、block 列表、表格摘要、图片或 OCR 状态、normalizer 名称/版本、耗时、confidence 和 parser warning。
4. 分块输出：chunk id、来源页码或 sheet 范围、token 估算、chunk 类型和内容预览。
5. ContextPackage：PromptProfile、SchemaVersion、业务描述、字段范围、few-shot examples、候选 chunk、预算分配。
6. 模型调用：provider、model、system prompt、user prompt、输入 token 估算、输出 token 估算、耗时、原始响应、解析后的 JSON、错误信息。
7. 合并和校验：字段来源、冲突字段、最终选择原因、Schema 校验结果。
8. 最终响应：返回给前端或 API 调用方的 JSON、状态码和错误详情。

敏感字段需要按配置脱敏，但脱敏不能破坏 Trace 结构和复现能力。

### FR-044 请求复现和对比运行

系统必须支持基于历史 Trace 复现请求。复现功能用于调试、Prompt 优化、模型切换评估和性能优化。

复现能力至少包括：

1. 使用历史请求的原始文件、SchemaVersion、PromptProfile、业务描述、ContextPackage、模型 provider、模型名称和处理策略重新运行。
2. 支持生成对比运行，允许管理员只改一个变量，例如 PromptProfile、模型名称、chunk 策略或上下文预算。
3. 对比展示原始运行和复现运行的最终 JSON、字段差异、错误差异、阶段耗时差异、模型调用次数和 token 估算差异。
4. 每次复现运行必须生成独立 Trace，保留 parent_trace_id，不能覆盖原始 Trace。
5. 如果模型 provider 不可用或模型版本不存在，系统必须明确显示不可复现原因。

## 10. 非功能需求

### NFR-001 技术栈

前端使用 TypeScript。后端使用 Python。系统必须可本地运行。

### NFR-002 模块化

后端必须分层：Router、Application Service、Domain Model、Repository、Provider、Validator、Adapter。

前端必须拆分页面、组件、状态管理、API Client 和领域类型，不能把所有逻辑写在单个 App 文件里。

### NFR-003 可扩展性

以下能力必须可扩展：

1. ModelProvider。
2. DocumentParser。
3. SchemaLearningStrategy。
4. PromptGenerator。
5. FileEntranceConnector。
6. DestinationAdapter。
7. ActivationValidationRule。

### NFR-004 错误处理

系统必须返回明确错误。禁止静默失败。禁止用宽泛 catch 后返回成功状态。

### NFR-005 数据持久化

本地版本使用 SQLite。上传文件可以保存在本地目录，但路径必须可配置。

后端业务代码必须使用 SQLAlchemy ORM 访问数据库。除迁移脚本或一次性维护脚本外，禁止在业务模块中直接写 `SELECT`、`INSERT`、`UPDATE`、`DELETE`、`CREATE TABLE`、`ALTER TABLE` 等 SQL 字符串，也禁止使用 `exec_driver_sql` 绕过 ORM。

### NFR-006 品牌独立

代码、页面、文档和配置不得包含参考平台所属组织的品牌名、内部标识或受保护素材。

### NFR-007 可测试性

以下逻辑必须可以单元测试：

1. Workspace 激活校验。
2. 集成激活校验。
3. Schema 校验。
4. JSON 校正校验。
5. 变量解析。
6. ModelProvider 选择。
7. DocumentParser 选择。
8. 字段硬约束校验。
9. 校验失败后的模型修复循环。

### NFR-008 大文件稳定性

系统必须能稳定处理大 PDF 和大 Excel。大文件处理必须可中断、可恢复、可重试，不能因为一次模型调用失败导致已完成的解析和分块全部丢失。

### NFR-009 模型上下文安全

所有模型调用必须经过 ContextPackage，不允许业务服务直接拼接任意长字符串调用模型。

上下文超预算必须返回明确错误或进入可解释的降级策略，禁止静默截断。

### NFR-010 成本和性能控制

系统必须记录每次模型调用的输入 token 估算、输出 token 估算、耗时、provider、model name 和关联任务。即使本地 Ollama 没有真实费用，也要保留后续接入云模型时的成本计量能力。

### NFR-011 大文件可测试性

大文件预检、分块、上下文预算、ContextPackage 生成、分阶段抽取计划、结果合并和冲突处理都必须可以单元测试。

### NFR-012 流程可观测性

所有进入文档处理、Prompt 生成、模型调用、结果合并、校验和集成同步的请求都必须生成结构化 Trace。Trace 必须能串联前端请求、后端任务、数据库记录、文件资产、ContextPackage、模型调用和最终响应。

Trace 数据必须满足：

1. 每个请求有唯一 trace_id。
2. 每个阶段有独立 span_id、parent_span_id、status、started_at、ended_at、duration_ms。
3. 每个阶段记录输入摘要和输出摘要，必要时引用完整 payload 的存储位置。
4. 每个模型调用记录 provider、model、prompt 版本、输入 token 估算、输出 token 估算、耗时和错误信息。
5. Trace 可被 API 查询，也可被管理员页面可视化。
6. Trace 不得依赖临时内存，服务重启后仍可查看历史请求。

### NFR-013 流程可复现性

系统必须把影响处理结果的关键版本和配置快照固化到 Trace 中，包括原始文件 hash、SchemaVersion、PromptProfile、业务描述、模型 provider、模型名称、处理策略、ContextPackage、候选 chunk 和合并策略。

复现运行必须做到：

1. 默认使用原始 Trace 的配置快照，而不是当前最新配置。
2. 明确记录任何人为覆盖的变量。
3. 产生新的 Trace，并保留与原始 Trace 的关联。
4. 允许导出复现包，用于离线分析或回归测试。
5. 对无法复现的原因给出结构化说明。

## 11. 验收标准

1. 用户可以创建 Tenant。
2. 用户可以在 Tenant 下创建 Workspace。
3. 一个 Workspace 可以定义一个目标 Schema。
4. 用户可以上传样本文档并输入期望 JSON。
5. 系统可以基于样本文档和期望 JSON 生成 Prompt Profile。
6. 用户可以用 Prompt Profile 测试新文档输出。
7. 用户可以纠正输出 JSON。
8. 纠正结果可以进入下一轮 Prompt 生成。
9. Workspace 满足条件后可以激活。
10. Active Workspace 可以处理正式文档。
11. 用户可以查看 Extracted Result。
12. 用户可以配置模型并切换模型。
13. 用户可以配置集成流程并执行激活校验。
14. 代码结构体现 Tenant、Workspace、Schema、Training Example、Prompt Profile 等领域对象。
15. 业务规则不堆在路由函数或 UI 事件函数中。
16. 用户可以在字段级纠正抽取结果。
17. 用户可以 Reject 或 Confirm 样本。
18. 用户可以看到 Start 节点系统变量和自定义变量。
19. 用户可以看到 API Access 的同步抽取、异步抽取和结果查询说明。
20. 大文件不会被完整塞进模型上下文。
21. 大文件会经过预检、解析、分块、上下文装配、分阶段抽取、合并和校验。
22. 超过同步阈值的文件会自动进入异步任务。
23. 用户可以看到大文件处理轨迹和失败阶段。
24. 每次模型调用都能追溯到 ContextPackage 和来源 chunk。
25. 上下文超预算时系统返回明确 issue 或执行可解释降级策略。
26. 多 chunk 合并冲突不会被静默覆盖。
27. 管理员可以在 Admin Observability 页面查看每个请求的输入、输出、中间结果、阶段耗时、模型调用和错误链路。
28. 管理员可以基于历史 Trace 复现一次请求。
29. 管理员可以对比原始运行和复现运行的输出 JSON、字段差异、耗时差异、token 估算差异和错误差异。
30. 每次复现运行都会生成新的 Trace，并保留与原始 Trace 的关联。
31. 用户上传文档时可以输入文档级上下文，并能在 Trace 中看到该上下文如何进入模型调用。
32. 字段硬约束失败会触发一次模型修复；修复失败会明确进入 correction_required 或 Incomplete，而不是静默当作成功。
33. 后端业务代码不包含直接 SQL，数据访问通过 SQLAlchemy ORM 完成。

# DocFlow Lite 页面与功能地图

## 1. 页面总览

| 页面 | 路由建议 | 核心功能 | 扩展点 |
| --- | --- | --- | --- |
| Tenant Center | `/tenants` | Tenant 列表、创建、切换 | TenantPolicy、TenantTemplate |
| Workspace Home | `/tenants/:tenantId/workspaces` | Workspace 卡片、搜索、过滤、创建 | WorkspaceTemplate、WorkspaceFilter |
| Workspace Shell | `/workspaces/:workspaceId/*` | 当前 Workspace 信息、侧边导航、状态 | NavigationContribution |
| Initialization - Expected Output | `/workspaces/:workspaceId/initialization/output` | JSON object / JSON array、字段定义、嵌套 JSON、JSON 推导 Schema | SchemaImporter、SchemaTemplate |
| Initialization - Validation | `/workspaces/:workspaceId/initialization/validation` | Regex Pattern、Ignored、number min/max、string/date 长度、Pattern 硬约束 | FieldValidationRule、FieldConstraint |
| Samples | `/workspaces/:workspaceId/samples` | 样本批次、表格化样本行、多个样本上传、文档级上下文、纠正、Confirm、生成 Prompt Version、复制为新草稿 | TrainingExampleSetVersion、DocumentParser、SampleSource、DocumentContext |
| Analysis Detail | `/workspaces/:workspaceId/analysis/:exampleId` | 文档预览、字段级纠正、note、Reject、Confirm | CorrectionPolicy、CorrectionRenderer |
| Prompt Versions | `/workspaces/:workspaceId/prompt-versions` | Prompt Profile 版本查看、选择使用、激活、对比效果 | PromptGenerator、PromptValidator、PromptVersionActivation |
| Integration | `/workspaces/:workspaceId/integration` | Workflow Canvas、节点配置、激活 | WorkflowNodeContribution |
| Extracted Result | `/workspaces/:workspaceId/extracted-result` | 任务状态卡片、搜索、过滤、表格、详情、下载 | ResultColumnContribution、ExportAdapter |
| API Access | `/workspaces/:workspaceId/api-access` | API Server、WorkspaceId、API Key、接口文档 | ApiAuthStrategy、EndpointDescriptor |
| Admin Observability | `/admin/observability` | 请求 Trace、阶段 Timeline、输入输出、中间结果、耗时、复现和对比运行 | TraceCollector、ReplayStrategy、TraceDiff |
| Model Settings | `/settings/models` | Provider、base URL、model name、模型列表 | ModelProvider |
| Processing Settings | `/workspaces/:workspaceId/settings/processing` | 大文件策略、chunk 策略、上下文预算、异步阈值 | LargeDocumentPolicy、ChunkingStrategy、ContextAssemblyStrategy |

## 2. Initialization 页面功能拆分

| 子页面 | 组件 | 功能 | 后端用例 |
| --- | --- | --- | --- |
| Expected Output | OutputSchemaDesigner | 创建 JSON object / JSON array、基础字段和嵌套字段 | `SchemaService.createSchemaVersion` |
| Expected Output | JsonSchemaImporter | 从期望 JSON 推导 Schema 草案 | `SchemaService.inferSchemaFromExpectedJson` |
| Validation | FieldValidationDesigner | 配置 Regex / Ignored | `SchemaService.updateFieldValidationRules` |
| Validation | FieldConstraintEditor | 配置 number min/max、string/date minLength/maxLength/exactLength、Pattern | `SchemaService.updateFieldConstraints` |
| Samples | SampleBatchSelector | 展示可编辑 Draft 批次和已发布批次、来源 Prompt Version、样本数量 | `TrainingExampleSetService.listVersions` |
| Samples | TrainingExampleUploader | 在当前 Draft 批次中上传多个样本文档 | `TrainingExampleService.createExample` |
| Samples | DocumentContextInput | 输入本次文档的业务背景、来源、金额范围、料号规则或特殊术语 | `ExtractionService.mergeDocumentContext` |
| Samples | NormalizedMarkdownPreview | 展示样本文档归一化后的 Markdown、block、table、OCR warning 和 normalizer 版本 | `DocumentNormalizationService.normalize` |
| Samples | LargeFilePreflightPanel | 展示文件大小、页数、同步/异步判断 | `DocumentIngestionService.preflight` |
| Samples | SampleTable | 表格展示当前批次的每个上传文件、状态、更新时间和 Review/Remove 操作 | `TrainingExampleSetService.listVersionExamples` |
| Samples | RemoveExampleAction | 从 Draft 批次删除样本，不影响已发布历史批次 | `TrainingExampleSetService.removeExample` |
| Samples | GeneratePromptVersionAction | 从已确认样本生成可激活的 Prompt Version | `TrainingExampleSetService.freezeVersion` |
| Samples | CopyBatchAction | 从已发布批次复制出新的 Draft 批次继续增删改样本 | `TrainingExampleSetService.cloneVersion` |
| Samples | ChunkPreviewPanel | 预览 DocumentChunk 和来源页码 | `DocumentChunkingService.listChunks` |
| Analysis Detail | DocumentPreview | 展示 PDF/Excel/CSV/TXT 解析结果 | `TrainingExampleService.getExampleDetail` |
| Analysis Detail | ContextBudgetInspector | 查看 ContextPackage、token 预算和使用的 chunk | `ContextEngineeringService.getContextTrace` |
| Analysis Detail | FieldCorrectionPanel | 字段级纠正 | `CorrectionService.saveFieldCorrection` |
| Analysis Detail | CorrectionNoteEditor | 字段 note | `CorrectionService.addNote` |
| Analysis Detail | CorrectionDecisionBar | Reject / Confirm | `CorrectionService.decide` |
| Prompt Versions | PromptProfileEditor | 编辑 Prompt | `PromptProfileService.updateProfile` |
| Prompt Versions | PromptVersionHistory | 查看版本来源、状态、样本数量和模型配置 | `PromptProfileService.listProfiles` |
| Prompt Versions | PromptVersionActivation | 选择某个版本作为当前 Workspace 的 active Prompt Profile | `PromptProfileService.activateProfile` |
| Prompt Versions | PromptVersionComparison | 对比两个版本的提示词、样本数、字段数、模型配置和抽取效果 | `PromptProfileService.compareProfiles` |
| Prompt Versions | WorkspaceActivationPanel | 激活 Workspace | `WorkspaceService.activateWorkspace` |

## 3. Integration 页面功能拆分

| 节点 | 配置内容 | 校验规则 | 扩展点 |
| --- | --- | --- | --- |
| Start | 系统变量、自定义 String/Dict、重复文档处理 | 变量名唯一、类型合法 | VariableType、GlobalSettingContribution |
| File Entrance | Manual/API/Mailbox/Shared Folder | source type 必填，各 source 配置合法 | FileEntranceConnector |
| Job Scheduler | Manual/One Time/Recurring、时区、开始时间、频率 | 非 Manual 必须有开始时间 | SchedulerStrategy |
| Mapping | Source Schema、Target JSON、Direct Mapping、Transformation | target schema 必填、变量引用合法 | MappingTransformer、VariableResolver |
| Destination | URL、Method、Headers、Auth、Timeout | URL 必填、OAuth2 字段完整 | DestinationAdapter、AuthStrategy |
| Activate | 激活校验和状态切换 | Workspace active、节点配置完整 | ActivationValidationRule |

## 4. Extracted Result 页面功能拆分

| 区域 | 功能 | 数据源 |
| --- | --- | --- |
| Search Bar | 按 Task Name 搜索 | ExtractionTask |
| Period Filter | 按创建时间过滤 | ExtractionTask.created_at |
| Status Cards | Total、Ready、Extracting、Completed、Incomplete、Processing Error、Sync Error、Failed | ExtractionTask.status |
| Result Table | Status、Task Name、Source、Create At、Modified At、Action | ExtractionTask |
| Detail Drawer | 原文、解析内容、抽取 JSON、错误、模型、PromptProfile | ExtractionTask + DocumentAsset + PromptProfile |
| Processing Trace | 预检、归一化、Markdown preview、分块、上下文装配、模型调用、合并轨迹 | DocumentAsset + NormalizedDocument + DocumentChunk + ContextPackage + ModelInvocation |
| Chunk Source Viewer | 字段值来源 chunk、页码、sheet、表格区域 | DocumentChunk + ExtractionMergeResult |
| Download | 导出选中结果 JSON | ExportAdapter |

## 5. API Access 页面功能拆分

| 区域 | 功能 | 后端用例 |
| --- | --- | --- |
| API Server | 展示 base URL | `ApiAccessService.getDescriptor` |
| WorkspaceId | 展示当前 Workspace ID | `ApiAccessService.getDescriptor` |
| API Key | 创建、隐藏、轮换、禁用 | `ApiAccessService.rotateApiKey` |
| Sync Extract | `POST /external/api/extract` | `ExtractionService.extractSync` |
| Async Extract | `POST /external/api/extract/async` | `ExtractionService.createAsyncTask` |
| Result Query | `GET /external/api/extract/result` | `ExtractionService.getTaskResult` |

## 6. 大文件与上下文控制页面能力

| 页面区域 | 用户能看到/配置什么 | 后端用例 |
| --- | --- | --- |
| Upload Preflight | 文件大小、页数、hash、处理模式、是否必须异步 | `DocumentIngestionService.preflight` |
| Processing Settings | 同步阈值、最大页数、chunk 大小、overlap、候选 chunk 数量、token 预算 | `WorkspaceProcessingPolicyService.updatePolicy` |
| Chunk Preview | chunk 内容、页码或 sheet 范围、token 估算、语义提示 | `DocumentChunkingService.listChunks` |
| Context Trace | ContextPackage、PromptProfile、chunk ids、字段范围、预算分配 | `ContextEngineeringService.getContextTrace` |
| Invocation Trace | provider、model、耗时、token 估算、错误信息 | `ModelInvocationService.listInvocations` |
| Merge Trace | 多 chunk 输出、字段来源、冲突字段、最终选择原因 | `ExtractionMergeService.getMergeTrace` |

## 7. Admin Observability 页面功能拆分

| 区域 | 功能 | 后端用例 |
| --- | --- | --- |
| Trace Filter | 按时间、Workspace、请求 ID、任务 ID、状态、文件名、模型、Prompt Profile 过滤 | `TraceQueryService.searchTraces` |
| Request Summary | 展示入口类型、总耗时、最终状态、模型调用次数、token 估算、错误摘要 | `TraceQueryService.getTraceSummary` |
| Stage Timeline | 可视化 upload、preflight、parse、chunk、context assembly、model invocation、merge、validation、persist、response、sync 阶段 | `TraceQueryService.getTraceSpans` |
| Input Viewer | 展示请求参数、文件 metadata、模型配置快照、处理策略快照 | `TracePayloadService.getInputPayload` |
| Intermediate Viewer | 展示预检结果、normalized Markdown、block/table metadata、OCR/parser warning、chunk 列表、ContextPackage、模型原始响应、合并结果、校验结果 | `TracePayloadService.getIntermediatePayloads` |
| Output Viewer | 展示最终响应 JSON、状态码、错误详情和下游同步结果 | `TracePayloadService.getOutputPayload` |
| Duration Breakdown | 展示阶段耗时、慢阶段标记、模型耗时占比、解析耗时占比 | `TraceMetricService.getDurationBreakdown` |
| Replay Console | 基于历史 Trace 复现请求，默认锁定原始配置快照 | `TraceReplayService.replay` |
| Compare Run | 只修改 Prompt Profile、模型、chunk 策略或上下文预算后生成对比运行 | `TraceReplayService.compare` |
| Diff Viewer | 对比原始运行和复现运行的 JSON、字段差异、耗时差异、token 差异和错误差异 | `TraceDiffService.diffRuns` |

## 8. 字段硬约束与修复页面能力

| 页面区域 | 用户能看到/配置什么 | 后端用例 |
| --- | --- | --- |
| Constraint Editor | 字段级 number min/max、string/date minLength/maxLength/exactLength、Pattern | `OutputValidationService.updateConstraints` |
| Extraction Review | 校验失败字段、错误原因、修复前输出、修复后输出 | `OutputValidationService.validateOutput` |
| Repair Trace | 自动修复 prompt、上次输出、validation errors、修复耗时和二次校验结果 | `ExtractionRepairService.repairOnce` |
| Correction Required | 修复仍失败时进入人工纠正，保留错误链路 | `CorrectionService.openCorrectionSession` |

## 9. 测试覆盖目标

前后端测试覆盖率目标均为 100%。

### 后端必须覆盖

1. TenantService。
2. WorkspaceService。
3. SchemaService。
4. TrainingExampleService。
5. CorrectionService。
6. PromptProfileService。
7. ExtractionService。
8. IntegrationService。
9. ApiAccessService。
10. 所有 Validator。
11. 所有 Registry 选择逻辑。
12. 所有内置 Parser / Provider / Adapter。
13. LargeDocumentPolicy。
14. DocumentNormalizer 与 Workspace-aware Normalizer Registry。
15. MarkdownChunkingStrategy。
16. TokenBudgeter。
17. ContextAssemblyStrategy。
18. RetrievalStrategy。
19. ExtractionMergeStrategy。
20. 大文件任务状态机。
21. TraceCollector。
22. TraceQueryService。
23. TracePayloadService。
24. TraceReplayService。
25. TraceDiffService。

### 前端必须覆盖

1. 每个页面的渲染。
2. 每个表单的输入和校验。
3. 每个 API Client 方法。
4. 每个状态切换按钮。
5. 每个错误提示分支。
6. 每个页面路由。
7. 每个重要组件的事件回调。
8. 大文件预检展示。
9. chunk 预览和 Context Trace。
10. 模型调用轨迹和合并冲突展示。
11. Admin Observability Trace 过滤、Timeline、输入输出、中间结果、耗时拆解。
12. 请求复现和对比运行的交互、错误提示和差异展示。

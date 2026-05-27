# DocFlow Lite 模块设计

## 1. 架构原则

DocFlow Lite 必须按领域建模，而不是按页面临时拼功能。

核心原则：

1. Tenant 是顶层业务边界。
2. Workspace 隶属于 Tenant。
3. 一个 Workspace 代表一个文档 Schema 和一套抽取能力。
4. 初始化不是一次性动作，而是“样本文档 + 期望 JSON + 模型总结 + 用户纠正”的闭环。
5. Prompt 必须版本化。
6. 字段硬约束必须在模型输出后由系统强制校验，不能只依赖提示词。
7. 抽取、解析、模型调用、集成连接都必须通过接口扩展。
8. Router 不写业务规则。
9. 前端页面不直接拼复杂领域逻辑。
10. 后端业务代码必须 ORM-only，禁止直接 SQL。
11. LLM 不直接消费原始文件或不可追踪纯文本，必须消费 DocumentNormalizer 产出的 canonical Markdown chunks。

## 2. cdas 实操映射

根据 `cdas` Workspace 的实际交互，参考平台的页面与领域模型映射如下：

| 页面/区域 | 真实行为 | 我们的领域模型 |
| --- | --- | --- |
| Tenant Center | 切换顶层业务容器 | Tenant |
| Workspace Home | 当前 Tenant 下的 Workspace 列表 | Workspace |
| Expected Output | JSON object / JSON array、字段类型、Required、嵌套字段 | SchemaDefinition、SchemaField |
| Validation | Regex Pattern、Ignored、number min/max、string/date length、Pattern | FieldValidationRule、FieldConstraint |
| Samples | 独立页面，表格化展示每个上传文件、文档级上下文、Extract、纠正、Confirm、生成 Prompt Version、复制为新草稿 | TrainingExample、TrainingExampleSetVersion、DocumentContext |
| Analysis Detail | 原文预览、字段级纠正、note、Reject、Confirm | CorrectionSession |
| Prompts Editing | 分析后编辑 Prompt | PromptProfile |
| Integration Start | 系统变量、自定义变量、重复文档处理开关 | VariableDefinition、IntegrationStartConfig |
| Extracted Result | 正式任务列表、状态统计、下载 | ExtractionTask |
| API Access | API Server、WorkspaceId、API Key、同步/异步/查询接口 | ApiAccessDescriptor |

重要结论：

1. 初始化流程里，Schema 定义和字段校验是两个独立步骤。
2. 样本文档被抽取后，不是直接编辑一段 JSON，而是优先做字段级纠正。
3. 字段级纠正需要支持 note，因为 note 会成为下一轮模型分析的业务反馈。
4. 字段硬约束用于模型输出后的系统校验；失败后触发模型修复，仍失败才进入人工纠正。
5. Confirm / Reject 是样本质量门禁。
6. Prompt 生成必须基于已发布的 Sample Batch（内部 frozen TrainingExampleSetVersion），而不是当前可变样本列表。
7. 已发布样本批次不可修改，只能复制成新的 draft 后继续新增、删除或更正样本。
8. Start 节点的变量系统是集成流程的根上下文。
9. API Access 是正式能力的一部分，不是普通帮助文档。

## 3. 后端分层

### 3.1 Router 层

Router 只负责：

1. HTTP 入参解析。
2. 调用 Application Service。
3. 把业务结果转换成 HTTP 响应。
4. 把业务异常转换成明确错误响应。

Router 禁止：

1. 写复杂 if/else 业务规则。
2. 直接访问数据库。
3. 直接调用模型。
4. 直接操作文件解析细节。

### 3.2 Application Service 层

Application Service 负责业务用例编排。

主要服务：

1. TenantService。
2. WorkspaceService。
3. SchemaService。
4. InitializationService。
5. TrainingExampleService。
6. PromptProfileService。
7. ExtractionService。
8. ModelSettingsService。
9. IntegrationService。
10. VariableService。
11. ApiAccessService。
12. CorrectionService。
13. DocumentIngestionService。
14. DocumentNormalizationService。
15. DocumentChunkingService。
16. ContextEngineeringService。
17. ExtractionPlanningService。
18. ExtractionMergeService。
19. OutputValidationService。
20. ExtractionRepairService。
21. TrainingExampleSetService。

### 3.3 Domain 层

Domain 层定义业务对象和值对象。

主要对象：

1. Tenant。
2. Workspace。
3. SchemaDefinition。
4. SchemaVersion。
5. ExpectedOutputSchema。
6. SchemaField。
7. DocumentAsset。
8. NormalizedDocument。
9. TrainingExample。
10. PromptProfile。
11. ExtractionTask。
12. IntegrationWorkflow。
13. MappingDefinition。
14. VariableDefinition。
15. ActivationValidationIssue。
16. FieldValidationRule。
17. FieldConstraint。
18. DocumentContext。
19. TrainingExampleSetVersion。
20. CorrectionSession。
21. CorrectionNote。
22. ApiAccessDescriptor。
23. DocumentChunk。
24. DocumentSegment。
25. ContextPackage。
26. ExtractionPlan。
27. ExtractionPass。
28. ModelInvocation。

### 3.4 Repository 层

Repository 负责数据访问。

主要 Repository：

1. TenantRepository。
2. WorkspaceRepository。
3. SchemaRepository。
4. TrainingExampleRepository。
5. PromptProfileRepository。
6. ExtractionTaskRepository。
7. IntegrationWorkflowRepository。
8. ModelSettingsRepository。
9. CorrectionSessionRepository。
10. ApiKeyRepository。

Repository 只处理持久化，不写业务决策。

ORM-only 约束：

1. 后端业务代码必须通过 SQLAlchemy ORM 的 Session、mapped record、relationship 和 `select()` 表达式访问数据。
2. Repository / Service / Router 中禁止直接写 SQL 字符串，包括 `SELECT`、`INSERT`、`UPDATE`、`DELETE`、`CREATE TABLE`、`ALTER TABLE`。
3. 禁止使用 `exec_driver_sql`、裸 connection 或手写 DDL 绕过 ORM。
4. 表结构创建和默认数据初始化应通过 SQLAlchemy metadata 与 ORM record 完成；正式迁移脚本可作为唯一例外。
5. 查询结果必须转换为领域模型或 API schema，不能把数据库 row/dict 直接泄露到上层。

### 3.5 Provider / Adapter 层

Provider 和 Adapter 负责外部能力适配。

主要接口：

1. ModelProvider。
2. DocumentNormalizer。
3. DocumentParser。
4. PromptGenerator。
5. SchemaLearningStrategy。
6. FileEntranceConnector。
7. DestinationAdapter。
8. ChunkingStrategy。
9. MarkdownChunkingStrategy。
10. TokenCounter。
11. ContextAssemblyStrategy。
12. RetrievalStrategy。
13. ExtractionMergeStrategy。
14. LargeDocumentPolicy。
15. OutputValidator。
16. ExtractionRepairStrategy。

每个接口都通过 Registry 管理具体实现，避免业务代码写死实现类。DocumentNormalizer Registry 必须接收 WorkspaceProcessingContext，并基于 workspace、schema type、业务描述、处理目的、文件名和 MIME type 选择具体 normalizer；背景文件、训练样本和正式抽取必须复用同一 registry。

## 4. 前端模块

### 4.1 Tenant 模块

负责：

1. Tenant 列表。
2. Tenant 创建。
3. Tenant 切换。
4. 当前 Tenant 上下文。

### 4.2 Workspace Home 模块

负责：

1. 当前 Tenant 下的 Workspace 卡片。
2. 搜索。
3. 状态过滤。
4. 创建 Workspace。
5. 创建时要求填写业务描述，并把该描述作为后续模型上下文的一部分。

### 4.3 Workspace Shell 模块

负责：

1. 当前 Workspace 信息展示。
2. Workspace 侧边导航。
3. Initialization 页面入口。
4. Samples 页面入口。
5. Prompt Versions 页面入口，用于选择、激活和对比某个 Prompt Profile 版本。
6. Integration 页面入口。
7. Extracted Result 页面入口。
8. API Access 页面入口。

### 4.4 Initialization 模块

负责初始化闭环。

子模块：

1. SchemaDesigner。
2. FieldValidationDesigner。
3. FieldConstraintEditor。
4. ExpectedJsonEditor。

### 4.5 Samples 模块

负责样本上传、表格化 review 和样本批次版本管理。

子模块：

1. SampleBatchSelector。
2. TrainingExampleUploader。
3. DocumentContextInput。
4. SampleTable。
5. FieldCorrectionPanel。
6. CorrectionNoteEditor。
7. CorrectionDecisionBar。
8. GeneratePromptVersionAction。
9. CopyBatchAction。
10. PromptProfileGenerationStatus。

### 4.5A Prompt Versions 模块

负责 Prompt Profile 版本的业务使用入口。

子模块：

1. PromptVersionHistory。
2. PromptVersionActivation。
3. PromptVersionComparison。
4. PromptProfilePreview。
5. PromptEffectComparison。

用户通过该模块选择某个 Prompt Profile version 并激活。激活后的版本写入 Workspace active_prompt_profile_id，后续正式抽取、验证抽取和 API 调用默认使用该版本。

### 4.6 Extracted Result 模块

负责：

1. 正式抽取任务列表。
2. 状态统计。
3. 任务搜索。
4. 时间过滤。
5. 任务详情。
6. 结果下载。

### 4.7 Integration 模块

负责：

1. 工作流节点展示。
2. Start 节点变量展示。
3. File Entrance 配置。
4. Job Scheduler 配置。
5. Mapping 配置。
6. Destination 配置。
7. 激活校验结果展示。

### 4.8 API Access 模块

负责：

1. 展示 API Server。
2. 展示 Workspace ID。
3. 管理 API Key。
4. 展示同步抽取接口。
5. 展示异步抽取接口。
6. 展示结果查询接口。

### 4.9 Model Settings 模块

负责：

1. 模型 Provider 选择。
2. base URL 配置。
3. model name 配置。
4. 本地模型列表加载。
5. Mock Provider 切换。

## 5. 核心领域对象

### 5.1 Tenant

Tenant 是顶层业务容器。

字段：

1. id。
2. name。
3. description。
4. status。
5. created_at。
6. updated_at。

### 5.2 Workspace

Workspace 是一个文档 Schema 的工作区。

字段：

1. id。
2. tenant_id。
3. name。
4. description。
5. document_type。
6. status。
7. active_schema_version_id。
8. active_prompt_profile_id。
9. created_at。
10. updated_at。

状态：

1. draft。
2. initializing。
3. ready_for_activation。
4. active。
5. inactive。
6. archived。

### 5.3 SchemaDefinition

SchemaDefinition 表示目标输出结构。

字段：

1. id。
2. workspace_id。
3. version。
4. output_type。
5. children。
6. json_schema。
7. status。
8. created_at。

SchemaDefinition 面向业务用户只表达 Expected Output：根节点是 JSON object 或 JSON array，字段可以递归嵌套，不暴露 Header Group、Line Items 或表格明细等内部概念。

### 5.4 FieldValidationRule

FieldValidationRule 表示字段级校验规则。

字段：

1. id。
2. schema_field_id。
3. regex_pattern。
4. ignored。
5. constraints。
6. valid_status。

constraints 按字段类型生效：number 支持 min/max；string/date 支持 minLength、maxLength、exactLength、pattern；Regex Pattern 与这些硬约束在同一组校验 UI 中配置。该规则是模型输出后的硬校验，不能只作为 prompt 建议。

### 5.5 TrainingExample

TrainingExample 表示一组“文档 + 期望 JSON + 模型输出 + 用户纠正”的训练样本。

字段：

1. id。
2. workspace_id。
3. schema_version_id。
4. document_asset_id。
5. parsed_document_id。
6. expected_output。
7. model_output。
8. corrected_output。
9. status。
10. prompt_profile_id。
11. error_message。
12. created_at。
13. updated_at。
14. correction_notes。
15. document_context。

状态：

1. uploaded。
2. parsed。
3. expected_output_ready。
4. extracted。
5. correction_required。
6. corrected。
7. accepted。
8. rejected。

### 5.6 Sample Batch / TrainingExampleSetVersion

Sample Batch 表示一组样本的可版本化集合；TrainingExampleSetVersion 是内部领域实体名，前端展示为 Draft / Published sample batch。

字段：

1. id。
2. workspace_id。
3. version。
4. name。
5. status：draft 或 frozen（前端显示为 Draft / Published）。
6. training_example_ids。
7. prompt_profile_id。
8. created_at。
9. updated_at。

规则：

1. draft 可新增、删除、纠正和确认样本。
2. frozen/published 只读，不允许新增、删除或修改样本。
3. frozen/published 可复制成新的 draft。
4. PromptProfile 必须记录来源 published batch。

### 5.7 CorrectionSession

CorrectionSession 表示一次人工校正过程。

字段：

1. id。
2. training_example_id。
3. field_values。
4. corrected_output。
5. notes。
6. decision。
7. decided_at。

decision 可取：

1. pending。
2. confirmed。
3. rejected。

### 5.8 PromptProfile

PromptProfile 表示可执行的抽取策略。

字段：

1. id。
2. workspace_id。
3. schema_version_id。
4. version。
5. system_prompt。
6. extraction_instruction。
7. output_contract。
8. few_shot_examples。
9. field_rules。
10. validation_rules。
11. model_provider。
12. model_name。
13. status。
14. created_at。

状态：

1. draft。
2. validating。
3. active。
4. retired。

### 5.9 ExtractionTask

ExtractionTask 表示正式文档处理任务。

字段：

1. id。
2. tenant_id。
3. workspace_id。
4. task_name。
5. source。
6. status。
7. document_asset_id。
8. parsed_document_id。
9. prompt_profile_id。
10. extracted_output。
11. corrected_output。
12. validation_result。
13. sync_result。
14. error_message。
15. created_at。
16. updated_at。

状态：

1. ready。
2. extracting。
3. completed。
4. incomplete。
5. processing_error。
6. sync_error。
7. failed。

### 5.10 ApiAccessDescriptor

ApiAccessDescriptor 表示 Workspace 对外 API 的描述。

字段：

1. workspace_id。
2. api_server。
3. authentication_scheme。
4. api_key_status。
5. endpoints。

endpoints 至少包含：

1. sync_extract。
2. async_extract。
3. get_extract_result。

### 5.11 DocumentAsset

DocumentAsset 表示上传或通过 API 进入系统的原始文件。

字段：

1. id。
2. workspace_id。
3. original_filename。
4. mime_type。
5. size_bytes。
6. sha256。
7. storage_path。
8. page_count。
9. sheet_count。
10. preflight_status。
11. processing_mode。
12. created_at。

processing_mode 可取：

1. sync_allowed。
2. async_required。
3. rejected_by_policy。

### 5.12 NormalizedDocument / DocumentSegment / DocumentChunk

NormalizedDocument 是进入 LLM 前的统一文档表示，不能直接等同于一整段文本，也不能只保存 Markdown 字符串。

字段：

1. id。
2. workspace_id。
3. source_sha256。
4. file_name。
5. mime_type。
6. normalizer。
7. normalizer_version。
8. markdown。
9. blocks。
10. tables。
11. assets。
12. trace。
13. created_at。

canonical Markdown 是 LLM 的主要输入；blocks、tables、assets 和 trace 用于页面预览、可观测性、复现、字段来源解释和 parser 替换。

WorkspaceProcessingContext 是归一化选择的输入，包含 workspace_id、schema_type、workspace_description 和 purpose。DocumentNormalizationService 先构建该 context，再交给 DocumentNormalizerRegistry 选择实现，因此不同 Workspace 可以接入不同 PDF parser、OCR 策略、Excel normalizer 或业务专用 adapter。

PDF 归一化策略：

1. born-digital PDF 优先走嵌入文本和布局路径，避免无意义 rasterize/OCR。
2. 扫描件、图片型页面、空文本页面或低 confidence 页面进入 rasterize/OCR/table recognition 路径。
3. Marker 可以作为 `MarkerPdfNormalizer` 的实现，但必须封装在 `DocumentNormalizer` adapter 后面。
4. 任何 normalizer 都必须返回同一个 NormalizedDocument contract。

NormalizedDocument 包含多个 DocumentSegment。DocumentSegment 可以表示：

1. PDF 页面 Markdown。
2. Excel sheet Markdown。
3. 表格区域 Markdown 和结构化 table metadata。
4. 图片 OCR 文本。
5. JSON 节点。
6. 邮件正文或附件。

DocumentChunk 是模型可消费的最小上下文单元，来源于 normalized Markdown 和 block metadata。

字段：

1. id。
2. normalized_document_id。
3. chunk_index。
4. chunk_type。
5. source_range。
6. content。
7. table_markdown。
8. token_count。
9. semantic_hints。
10. checksum。

### 5.13 ContextPackage

ContextPackage 表示一次模型调用真正拿到的上下文。

字段：

1. id。
2. workspace_id。
3. schema_version_id。
4. prompt_profile_id。
5. extraction_task_id 或 training_example_id。
6. target_fields。
7. chunk_ids。
8. token_budget。
9. estimated_input_tokens。
10. reserved_output_tokens。
11. assembly_strategy。
12. model_provider。
13. model_name。
14. workspace_description。
15. document_context。
16. created_at。

ContextPackage 用于审计、调试和复现模型输出。业务服务不得绕过 ContextPackage 直接拼长文本调用模型。

### 5.14 ExtractionPlan / ExtractionPass / ModelInvocation

ExtractionPlan 表示一次抽取的执行计划。

计划至少包含：

1. small_document_single_pass。
2. large_document_staged。
3. field_group_extraction。
4. nested_json_array_extraction。

ExtractionPass 表示计划中的一个模型调用步骤，例如字段组抽取、嵌套 JSON Array 抽取或冲突复核。

ModelInvocation 记录每一次模型调用：

1. context_package_id。
2. provider。
3. model_name。
4. estimated_input_tokens。
5. estimated_output_tokens。
6. duration_ms。
7. status。
8. error_message。

## 6. 初始化闭环设计

初始化不是单个接口，而是一组可重复执行的用例。

### 6.1 第一步：建立 Schema

输入：

1. 用户手动定义字段。
2. 用户上传目标 JSON 示例。
3. 用户从期望输出 JSON 推导 Schema。

输出：

1. SchemaDefinition。
2. SchemaVersion。

### 6.2 第二步：配置字段校验

输入：

1. SchemaDefinition。
2. 字段级 Regex Pattern。
3. 字段级 Ignored 开关。
4. 字段级硬约束，例如 number min/max、string/date 长度和 pattern。

输出：

1. FieldValidationRule。
2. FieldConstraint。

### 6.3 第三步：建立 Training Example

输入：

1. 样本文档。
2. 期望输出 JSON。
3. 可选文档级上下文。

处理：

1. DocumentParser 解析文档。
2. ContextEngineeringService 合并 Workspace 描述和文档级上下文。
3. ExpectedJsonValidator 校验期望 JSON。
4. SchemaCompatibilityValidator 校验期望 JSON 是否匹配 Schema。

输出：

1. TrainingExample。

### 6.4 第四步：模型总结抽取策略

输入：

1. SchemaDefinition。
2. TrainingExample 列表。
3. 当前模型配置。

处理：

1. SchemaLearningStrategy 组装上下文。
2. ModelProvider 调用模型。
3. PromptGenerator 生成 PromptProfile。
4. PromptProfileValidator 校验输出完整性。

输出：

1. 新版本 PromptProfile。

### 6.5 第五步：验证抽取结果

输入：

1. 验证文档。
2. PromptProfile。
3. 可选文档级上下文。

处理：

1. 解析文档。
2. 合并 Workspace 描述和文档级上下文。
3. 调用模型抽取。
4. OutputValidationService 校验输出 JSON、字段类型、Required、Regex 和硬约束。
5. 若校验失败，ExtractionRepairService 使用原文、原 prompt、上次输出和 validation errors 触发一次模型修复。
6. 修复后再次校验，仍失败则进入 correction_required。

输出：

1. model_output。
2. validation_result。
3. correction_required 状态。

### 6.6 第六步：人工纠正

输入：

1. model_output。
2. 用户纠正后的字段值。
3. 用户纠正后的 corrected_output。
4. 字段级 note。

处理：

1. JSON 格式校验。
2. Schema 兼容校验。
3. 差异记录。

输出：

1. corrected_output。
2. CorrectionSession。
3. confirmed 或 rejected 的 TrainingExample。

### 6.7 第七步：再次学习

用户可以把纠正后的 Training Example 加入下一轮模型分析，生成新的 PromptProfile 版本。

这个循环可以重复，直到 Workspace 达到激活条件。

## 7. 扩展点设计

### 7.1 ModelProvider

接口职责：

1. 获取模型列表。
2. 执行 Prompt 生成。
3. 执行文档抽取。

内置实现：

1. OllamaProvider。
2. MockProvider。

后续可扩展：

1. OpenAICompatibleProvider。
2. AzureOpenAIProvider。
3. LocalLlmProvider。

### 7.2 DocumentParser

接口职责：

1. 判断是否支持文件类型。
2. 把原始文件解析为统一 ParsedDocument。

内置实现：

1. PdfParser。
2. ExcelParser。
3. CsvParser。
4. TextParser。
5. JsonParser。

后续可扩展：

1. ImageOcrParser。
2. EmailAttachmentParser。
3. ArchiveParser。

### 7.3 SchemaLearningStrategy

接口职责：

1. 根据样本构造模型上下文。
2. 控制 Prompt 生成策略。
3. 处理多轮纠正结果。

内置实现：

1. FewShotLearningStrategy。
2. CorrectionFeedbackStrategy。

### 7.4 FileEntranceConnector

接口职责：

1. 从文件入口创建 ExtractionTask。
2. 标准化来源信息。

内置实现：

1. ManualUploadConnector。
2. ApiUploadConnector。

配置建模预留：

1. MailboxConnector。
2. SharedFolderConnector。

### 7.5 DestinationAdapter

接口职责：

1. 把 ExtractionTask 输出发送到目标系统。
2. 返回同步结果。

内置实现：

1. HttpDestinationAdapter。
2. MockDestinationAdapter。

### 7.6 LargeDocumentPolicy

接口职责：

1. 判断文件是否允许同步处理。
2. 判断是否必须进入异步任务。
3. 判断是否超过 Workspace 的处理限制。
4. 返回结构化 preflight issue。

内置实现：

1. DefaultLargeDocumentPolicy。

### 7.7 ChunkingStrategy

接口职责：

1. 把 ParsedDocument 切分成 DocumentChunk。
2. 控制 chunk 大小和 overlap。
3. 保留页码、sheet、表格区域等来源信息。

内置实现：

1. PageAwarePdfChunkingStrategy。
2. SheetAwareExcelChunkingStrategy。
3. PlainTextChunkingStrategy。

### 7.8 TokenCounter

接口职责：

1. 估算文本 token。
2. 根据模型上下文窗口返回预算上限。
3. 为不同 provider 保留 tokenizer 差异的扩展点。

内置实现：

1. ApproximateTokenCounter。

### 7.9 ContextAssemblyStrategy

接口职责：

1. 根据 Workspace 业务描述、Schema、PromptProfile、字段范围和候选 chunk 组装 ContextPackage。
2. 控制 system prompt、few-shot examples、字段规则和 chunk 内容的预算占比。
3. 当预算不足时返回明确 issue 或执行可解释降级。

内置实现：

1. BalancedContextAssemblyStrategy。
2. FieldFocusedContextAssemblyStrategy。

### 7.10 RetrievalStrategy

接口职责：

1. 从 DocumentChunk 中选择和目标字段最相关的候选 chunk。
2. 支持关键词、字段别名、页码范围和后续向量检索扩展。

内置实现：

1. KeywordRetrievalStrategy。
2. SchemaHintRetrievalStrategy。

### 7.11 ExtractionMergeStrategy

接口职责：

1. 合并多个 ExtractionPass 的输出。
2. 保留字段来源 chunk。
3. 标记冲突字段。
4. 生成 correction_required 所需 issue。

内置实现：

1. SourceAwareMergeStrategy。

### 7.12 OutputValidator

接口职责：

1. 校验根输出类型是 JSON object 还是 JSON array。
2. 校验字段类型、Required、Regex Pattern 和 Ignored。
3. 校验字段硬约束，包括 number min/max、string/date minLength/maxLength/exactLength 和 pattern。
4. 返回结构化 issue，供前端展示、Trace 记录和模型修复使用。

内置实现：

1. ExpectedOutputValidator。

### 7.13 ExtractionRepairStrategy

接口职责：

1. 根据原 prompt、原始文档上下文、上次模型输出和 validation errors 生成修复 prompt。
2. 限制自动修复次数，避免无限循环。
3. 修复后再次调用 OutputValidator。
4. 将修复前后输出、错误和耗时写入 Trace。

内置实现：

1. SinglePassJsonRepairStrategy。

## 8. 校验设计

校验规则必须对象化。

主要 Validator：

1. WorkspaceActivationValidator。
2. TrainingExampleValidator。
3. ExpectedJsonValidator。
4. SchemaCompatibilityValidator。
5. PromptProfileValidator。
6. IntegrationActivationValidator。
7. MappingExpressionValidator。
8. VariableReferenceValidator。
9. FieldValidationRuleValidator。
10. CorrectionDecisionValidator。
11. LargeDocumentPolicyValidator。
12. ContextBudgetValidator。
13. ContextPackageValidator。
14. ExtractionMergeValidator。
15. ExpectedOutputValidator。
16. FieldConstraintValidator。
17. ExtractionRepairValidator。

校验输出统一为 ValidationResult。

ValidationResult 包含：

1. valid。
2. issues。

ValidationIssue 包含：

1. code。
2. path。
3. message。
4. severity。

## 9. 大文件与上下文工程设计

### 9.1 核心原则

大文件处理的核心原则是：**不能把完整文档直接交给模型**。

系统必须把原始文件、解析结果、chunk、上下文包、模型调用和最终输出拆开建模。这样才能处理大 PDF、大 Excel、长合同、扫描件和后续云模型成本控制。

### 9.2 处理管线

大文件处理管线如下：

1. Upload：保存原始文件，创建 DocumentAsset，记录 size、mime、hash。
2. Preflight：LargeDocumentPolicy 判断同步、异步或拒绝。
3. Parse：DocumentParser 把文件解析成 ParsedDocument。
4. Normalize：把页面、表格、sheet、OCR 文本统一成 DocumentSegment。
5. Chunk：ChunkingStrategy 生成 DocumentChunk。
6. Index：建立本地关键词索引，预留后续向量索引能力。
7. Plan：ExtractionPlanningService 选择单次抽取或分阶段抽取。
8. Assemble：ContextEngineeringService 合并 Workspace 描述、文档级上下文，并通过 TokenBudgeter 和 ContextAssemblyStrategy 生成 ContextPackage。
9. Invoke：ModelProvider 只接收 ContextPackage 产出的 prompt。
10. Merge：ExtractionMergeService 合并多次模型输出。
11. Validate：OutputValidator、SchemaCompatibilityValidator 和 FieldValidationRuleValidator 校验结果。
12. Repair：硬约束失败时 ExtractionRepairStrategy 自动修复一次。
13. Correct：修复后仍失败、冲突或不完整字段进入人工纠正。

### 9.3 上下文预算

ContextEngineeringService 必须为每次调用计算预算。

预算模型：

1. 模型上下文窗口总量。
2. system prompt 保留量。
3. Schema 输出契约保留量。
4. 字段规则保留量。
5. few-shot example 保留量。
6. 候选 chunk 可用量。
7. 输出 JSON 保留量。

如果候选内容超预算，系统按以下顺序处理：

1. 减少 few-shot example 数量。
2. 只抽取当前字段路径范围。
3. 减少候选 chunk。
4. 改成多轮 ExtractionPass。
5. 返回 context_budget_exceeded issue。

禁止静默截断。

### 9.4 分阶段抽取

小文件可以执行 single-pass extraction。

大文件必须支持 staged extraction：

1. RetrievalStrategy 找候选 chunk。
2. 按期望输出结构中的字段路径抽取。
3. JSON Array 字段按对象数组抽取。
4. 跨页表格通过 SourceAwareMergeStrategy 合并。
5. 冲突字段进入 validation_result。
6. 用户纠正后，纠正信息进入下一轮学习。

### 9.5 可恢复性

解析、分块、索引和模型调用必须是可恢复阶段。

失败后重试时：

1. 已保存的 DocumentAsset 不重复上传。
2. 已完成的 ParsedDocument 不重复解析。
3. 未变化的 DocumentChunk 不重复生成。
4. 已成功的 ExtractionPass 不重复调用模型。
5. 只重跑失败阶段或受影响阶段。

### 9.6 可观测性

任务详情和样本详情必须展示：

1. 文件大小和页数。
2. chunk 数量。
3. 使用的 ChunkingStrategy。
4. 使用的 ContextAssemblyStrategy。
5. 每次 ModelInvocation 的 provider、model、耗时和 token 估算。
6. ContextPackage 关联的 chunk。
7. 合并冲突和校验 issue。

### 9.7 反模式

以下实现禁止出现：

1. 直接读取完整 PDF 文本拼到 prompt。
2. 用字符串切片静默截断 prompt。
3. 在 Router 中判断大文件处理分支。
4. 忽略 chunk 来源信息。
5. 多 chunk 输出冲突时直接用最后一次结果覆盖。
6. 大文件同步接口长时间阻塞。

## 10. 后端建议目录结构

```text
backend/app/
  api/
    routers/
      tenants.py
      workspaces.py
      initialization.py
      corrections.py
      extraction_tasks.py
      integration.py
      api_access.py
      model_settings.py
  application/
    document_ingestion_service.py
    document_chunking_service.py
    context_engineering_service.py
    extraction_planning_service.py
    extraction_merge_service.py
    tenant_service.py
    workspace_service.py
    initialization_service.py
    prompt_profile_service.py
    correction_service.py
    extraction_service.py
    integration_service.py
    api_access_service.py
  domain/
    tenants.py
    workspaces.py
    schemas.py
    documents.py
    training_examples.py
    corrections.py
    context_packages.py
    document_chunks.py
    extraction_plans.py
    prompt_profiles.py
    extraction_tasks.py
    integrations.py
    validation.py
  infrastructure/
    database.py
    repositories/
    chunking/
    context/
    parsers/
    model_providers/
    destinations/
  config.py
  main.py
```

## 11. 前端建议目录结构

```text
frontend/src/
  app/
    App.tsx
    routes.tsx
  api/
    httpClient.ts
    tenantApi.ts
    workspaceApi.ts
    initializationApi.ts
    extractionApi.ts
    integrationApi.ts
    modelSettingsApi.ts
  features/
    tenants/
    workspace-home/
    workspace-shell/
    initialization/
    extracted-result/
    integration/
    api-access/
    model-settings/
    processing-settings/
  domain/
    tenant.ts
    workspace.ts
    schema.ts
    trainingExample.ts
    correction.ts
    contextPackage.ts
    documentChunk.ts
    promptProfile.ts
    extractionTask.ts
    integration.ts
  shared/
    components/
    hooks/
    utils/
```

## 12. 需要优先重构的点

1. 增加 Tenant 领域对象和 API。
2. Workspace 增加 tenant_id。
3. 把初始化从简单 Schema 编辑改成 Training Example 学习闭环。
4. 增加 PromptProfile 版本模型。
5. 增加 DocumentParser Registry。
6. 增加 ModelProvider Registry。
7. 把后端 main.py 拆分为 routers、services、repositories。
8. 把前端 App.tsx 拆分为 feature modules。
9. 增加 WorkspaceActivationValidator。
10. 增加 TrainingExampleValidator。
11. 增加 FieldValidationRule。
12. 增加 CorrectionSession。
13. 增加 API Access 模块。
14. 增加 DocumentAsset 预检和处理模式。
15. 增加 ParsedDocument、DocumentSegment、DocumentChunk。
16. 增加 LargeDocumentPolicy、ChunkingStrategy、TokenCounter、ContextAssemblyStrategy。
17. 增加 ContextPackage 和 ModelInvocation。
18. 增加 ExtractionPlan、ExtractionPass 和 ExtractionMergeStrategy。
19. 大文件默认走异步抽取，避免同步接口阻塞。

# DocFlow Lite 实施计划

## Phase 1: 中文需求和领域设计

Status: Done

Deliverables:

- 中文需求文档。
- Tenant -> Workspace -> Schema 层级模型。
- Initialization 学习闭环设计。
- cdas 实操流程映射。
- 模块设计文档。
- 激活校验对象模型。
- 系统上下文图。
- 服务架构图。
- 前后端包图。
- 组件图。
- 核心时序图。
- 数据流图。
- 数据库 ER 图。
- 状态机图。
- 页面功能地图。
- 大文件处理架构。
- 模型上下文预算和 ContextPackage 设计。
- 分阶段抽取与合并策略设计。

## Phase 2: 后端领域重构

Status: In progress

Deliverables:

- Tenant APIs。
- Workspace APIs 增加 tenant_id。
- SchemaDefinition / SchemaVersion。
- FieldValidationRule。
- TrainingExample。
- CorrectionSession。
- PromptProfile。
- ExtractionTask。
- API Access 描述。
- DocumentAsset 预检元数据。
- ParsedDocument / DocumentSegment / DocumentChunk。
- ContextPackage。
- ExtractionPlan / ExtractionPass / ModelInvocation。
- Repository 层。
- Service 层。
- DocumentIngestionService。
- DocumentChunkingService。
- ContextEngineeringService。
- ExtractionPlanningService。
- ExtractionMergeService。
- Structured activation validator。

## Phase 3: 前端模块重构

Status: In progress

Deliverables:

- Tenant Center。
- Workspace Home。
- Workspace Shell。
- Initialization 四阶段页面。
- Field-level correction detail。
- Prompt profile editing。
- Extracted Result。
- Integration workflow。
- API Access。
- Model settings。
- Processing Settings。
- 大文件处理轨迹展示。
- ContextPackage / chunk 来源查看。

## Phase 4: 扩展点实现

Status: Pending

Deliverables:

- ModelProvider Registry。
- DocumentParser Registry。
- SchemaLearningStrategy。
- PromptGenerator。
- FileEntranceConnector。
- DestinationAdapter。
- VariableReferenceResolver。
- LargeDocumentPolicy。
- ChunkingStrategy。
- TokenCounter。
- ContextAssemblyStrategy。
- RetrievalStrategy。
- ExtractionMergeStrategy。
- 所有扩展点 Registry 的单元测试。

## Phase 5: 质量和验收

Status: Pending

Deliverables:

- 后端单元测试。
- 前端构建检查。
- 品牌独立性扫描。
- 端到端样例数据。
- 路由层无复杂业务规则。
- UI 层无单文件巨型组件。
- 前端测试覆盖率 100%。
- 后端测试覆盖率 100%。
- 大文件预检、分块、上下文预算、分阶段抽取、合并冲突测试。
- 模型上下文超预算必须有明确测试覆盖。

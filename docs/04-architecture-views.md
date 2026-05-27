# DocFlow Lite 架构视图与 UML 图

## 1. 架构总原则

DocFlow Lite 的核心约束是：**每个环节都必须可扩展**。

这不是只给模型或解析器留接口，而是从 Tenant、Workspace、Schema、文档解析、样本学习、模型调用、Prompt 生成、人工纠正、结果校验、文件入口、调度、Mapping、Destination、API Access 到监控状态，每个环节都要通过接口、策略、注册表或插件点扩展。

核心设计要求：

1. Router 只处理 HTTP，不写业务规则。
2. Application Service 只编排用例，不直接绑定具体实现。
3. Domain Model 表达业务对象和状态机。
4. Provider / Connector / Adapter 负责外部能力。
5. Validator / Rule Object 表达校验规则。
6. Registry 负责选择具体实现。
7. 前端页面按 Feature 拆分，不能把所有逻辑放在单个 App 文件。

## 2. 系统上下文图

```mermaid
flowchart LR
    owner[Workspace Owner]
    apiUser[API Consumer]
    frontend[DocFlow Lite Web App]
    backend[DocFlow Lite API]
    db[(SQLite Database)]
    files[(Local File Storage)]
    ollama[Local Ollama]
    modelProvider[Other Model Providers]
    downstream[Downstream Systems]
    mailbox[Mailbox Source]
    sharedFolder[Shared Folder Source]

    owner -->|浏览器操作| frontend
    apiUser -->|API Key / Workspace ID| backend
    frontend -->|REST API| backend
    backend -->|读写业务数据| db
    backend -->|保存上传文件| files
    backend -->|默认模型调用| ollama
    backend -.可扩展.-> modelProvider
    backend -->|集成交付| downstream
    backend -.可扩展文件入口.-> mailbox
    backend -.可扩展文件入口.-> sharedFolder
```

## 3. 服务架构图

```mermaid
flowchart TB
    subgraph FE[Frontend - TypeScript]
        TenantUI[Tenant Center]
        WorkspaceUI[Workspace Home]
        InitUI[Initialization Pages]
        CorrectionUI[Analysis Detail / Correction]
        IntegrationUI[Integration Workflow]
        ResultUI[Extracted Result]
        ApiAccessUI[API Access]
        ModelSettingsUI[Model Settings]
        ApiClient[Typed API Client]
    end

    subgraph API[Backend API Routers - FastAPI]
        TenantRouter[Tenant Router]
        WorkspaceRouter[Workspace Router]
        InitRouter[Initialization Router]
        CorrectionRouter[Correction Router]
        ExtractionRouter[Extraction Router]
        IntegrationRouter[Integration Router]
        ApiAccessRouter[API Access Router]
        ModelRouter[Model Settings Router]
    end

    subgraph APP[Application Services]
        TenantService[TenantService]
        WorkspaceService[WorkspaceService]
        SchemaService[SchemaService]
        TrainingService[TrainingExampleService]
        LearningService[SchemaLearningService]
        PromptService[PromptProfileService]
        CorrectionService[CorrectionService]
        ExtractionService[ExtractionService]
        IntegrationService[IntegrationService]
        ApiAccessService[ApiAccessService]
    end

    subgraph DOMAIN[Domain Layer]
        DomainModels[Domain Models]
        StateMachines[State Machines]
        Validators[Validators / Rule Objects]
        Policies[Policies]
    end

    subgraph EXT[Extension Layer]
        ParserRegistry[DocumentParserRegistry]
        ModelRegistry[ModelProviderRegistry]
        LearningRegistry[SchemaLearningStrategyRegistry]
        PromptRegistry[PromptGeneratorRegistry]
        ConnectorRegistry[FileEntranceConnectorRegistry]
        DestinationRegistry[DestinationAdapterRegistry]
        ValidatorRegistry[ValidationRuleRegistry]
    end

    subgraph INFRA[Infrastructure]
        Repositories[Repositories]
        SQLite[(SQLite)]
        FileStorage[(File Storage)]
        Ollama[OllamaProvider]
        MockModel[MockProvider]
        PdfParser[PdfParser]
        ExcelParser[ExcelParser]
        CsvParser[CsvParser]
        HttpDestination[HttpDestinationAdapter]
    end

    TenantUI --> ApiClient
    WorkspaceUI --> ApiClient
    InitUI --> ApiClient
    CorrectionUI --> ApiClient
    IntegrationUI --> ApiClient
    ResultUI --> ApiClient
    ApiAccessUI --> ApiClient
    ModelSettingsUI --> ApiClient

    ApiClient --> TenantRouter
    ApiClient --> WorkspaceRouter
    ApiClient --> InitRouter
    ApiClient --> CorrectionRouter
    ApiClient --> ExtractionRouter
    ApiClient --> IntegrationRouter
    ApiClient --> ApiAccessRouter
    ApiClient --> ModelRouter

    TenantRouter --> TenantService
    WorkspaceRouter --> WorkspaceService
    InitRouter --> SchemaService
    InitRouter --> TrainingService
    InitRouter --> LearningService
    CorrectionRouter --> CorrectionService
    ExtractionRouter --> ExtractionService
    IntegrationRouter --> IntegrationService
    ApiAccessRouter --> ApiAccessService
    ModelRouter --> PromptService

    TenantService --> DomainModels
    WorkspaceService --> DomainModels
    SchemaService --> Validators
    TrainingService --> Validators
    LearningService --> Policies
    PromptService --> Validators
    CorrectionService --> Validators
    ExtractionService --> StateMachines
    IntegrationService --> StateMachines

    LearningService --> LearningRegistry
    LearningService --> PromptRegistry
    ExtractionService --> ParserRegistry
    ExtractionService --> ModelRegistry
    IntegrationService --> ConnectorRegistry
    IntegrationService --> DestinationRegistry
    IntegrationService --> ValidatorRegistry

    TenantService --> Repositories
    WorkspaceService --> Repositories
    SchemaService --> Repositories
    TrainingService --> Repositories
    PromptService --> Repositories
    CorrectionService --> Repositories
    ExtractionService --> Repositories
    IntegrationService --> Repositories

    Repositories --> SQLite
    ParserRegistry --> PdfParser
    ParserRegistry --> ExcelParser
    ParserRegistry --> CsvParser
    PdfParser --> FileStorage
    ExcelParser --> FileStorage
    CsvParser --> FileStorage
    ModelRegistry --> Ollama
    ModelRegistry --> MockModel
    DestinationRegistry --> HttpDestination
```

## 4. 后端包图

```mermaid
classDiagram
    namespace api.routers {
      class TenantRouter
      class WorkspaceRouter
      class InitializationRouter
      class CorrectionRouter
      class ExtractionRouter
      class IntegrationRouter
      class ApiAccessRouter
      class ModelSettingsRouter
    }

    namespace application {
      class TenantService
      class WorkspaceService
      class SchemaService
      class TrainingExampleService
      class SchemaLearningService
      class PromptProfileService
      class CorrectionService
      class ExtractionService
      class IntegrationService
      class ApiAccessService
    }

    namespace domain {
      class Tenant
      class Workspace
      class SchemaDefinition
      class TrainingExample
      class CorrectionSession
      class PromptProfile
      class ExtractionTask
      class IntegrationWorkflow
      class ValidationIssue
      class StateMachine
    }

    namespace infrastructure.repositories {
      class TenantRepository
      class WorkspaceRepository
      class SchemaRepository
      class TrainingExampleRepository
      class CorrectionSessionRepository
      class PromptProfileRepository
      class ExtractionTaskRepository
      class IntegrationWorkflowRepository
    }

    namespace infrastructure.extensions {
      class DocumentParserRegistry
      class ModelProviderRegistry
      class SchemaLearningStrategyRegistry
      class PromptGeneratorRegistry
      class FileEntranceConnectorRegistry
      class DestinationAdapterRegistry
      class ValidationRuleRegistry
    }

    TenantRouter --> TenantService
    WorkspaceRouter --> WorkspaceService
    InitializationRouter --> SchemaService
    InitializationRouter --> TrainingExampleService
    InitializationRouter --> SchemaLearningService
    CorrectionRouter --> CorrectionService
    ExtractionRouter --> ExtractionService
    IntegrationRouter --> IntegrationService
    ApiAccessRouter --> ApiAccessService

    TenantService --> TenantRepository
    WorkspaceService --> WorkspaceRepository
    SchemaService --> SchemaRepository
    TrainingExampleService --> TrainingExampleRepository
    CorrectionService --> CorrectionSessionRepository
    PromptProfileService --> PromptProfileRepository
    ExtractionService --> ExtractionTaskRepository
    IntegrationService --> IntegrationWorkflowRepository

    SchemaLearningService --> ModelProviderRegistry
    SchemaLearningService --> SchemaLearningStrategyRegistry
    SchemaLearningService --> PromptGeneratorRegistry
    ExtractionService --> DocumentParserRegistry
    ExtractionService --> ModelProviderRegistry
    IntegrationService --> FileEntranceConnectorRegistry
    IntegrationService --> DestinationAdapterRegistry
    IntegrationService --> ValidationRuleRegistry
```

## 5. 前端包图

```mermaid
classDiagram
    namespace app {
      class App
      class Routes
      class Layout
    }

    namespace api {
      class HttpClient
      class TenantApi
      class WorkspaceApi
      class InitializationApi
      class CorrectionApi
      class ExtractionApi
      class IntegrationApi
      class ApiAccessApi
      class ModelSettingsApi
    }

    namespace features.tenants {
      class TenantCenterPage
      class TenantCreateDialog
      class TenantSwitcher
    }

    namespace features.workspaceHome {
      class WorkspaceHomePage
      class WorkspaceCard
      class WorkspaceCreateDialog
      class WorkspaceFilters
    }

    namespace features.initialization {
      class InitializationPage
      class SchemaDesigner
      class FieldValidationDesigner
      class SampleTable
      class AnalysisDetailPage
      class FieldCorrectionPanel
      class PromptProfileEditor
    }

    namespace features.integration {
      class IntegrationPage
      class WorkflowCanvas
      class StartNodeDrawer
      class FileEntranceDrawer
      class SchedulerDrawer
      class MappingDrawer
      class DestinationDrawer
      class ActivationPanel
    }

    namespace features.results {
      class ExtractedResultPage
      class ResultStatusCards
      class ResultTable
      class ResultDetailDrawer
    }

    namespace domain {
      class TenantType
      class WorkspaceType
      class SchemaType
      class TrainingExampleType
      class PromptProfileType
      class ExtractionTaskType
      class IntegrationType
    }

    App --> Routes
    Routes --> TenantCenterPage
    Routes --> WorkspaceHomePage
    Routes --> InitializationPage
    Routes --> AnalysisDetailPage
    Routes --> IntegrationPage
    Routes --> ExtractedResultPage

    TenantCenterPage --> TenantApi
    WorkspaceHomePage --> WorkspaceApi
    InitializationPage --> InitializationApi
    AnalysisDetailPage --> CorrectionApi
    IntegrationPage --> IntegrationApi
    ExtractedResultPage --> ExtractionApi

    TenantApi --> HttpClient
    WorkspaceApi --> HttpClient
    InitializationApi --> HttpClient
    CorrectionApi --> HttpClient
    ExtractionApi --> HttpClient
    IntegrationApi --> HttpClient
```

## 6. 组件图

```mermaid
flowchart LR
    subgraph Browser
        Pages[Feature Pages]
        State[Feature State / Hooks]
        Client[Typed API Client]
    end

    subgraph API
        Routers[FastAPI Routers]
        DTO[Request / Response DTO]
    end

    subgraph Core
        Services[Application Services]
        Domain[Domain Objects]
        Rules[Validators and State Machines]
    end

    subgraph Plugins
        Parsers[Document Parsers]
        Models[Model Providers]
        Learning[Learning Strategies]
        Prompts[Prompt Generators]
        Entrances[File Entrance Connectors]
        Destinations[Destination Adapters]
    end

    subgraph Storage
        Repo[Repositories]
        DB[(SQLite)]
        FS[(File Storage)]
    end

    Pages --> State
    State --> Client
    Client --> Routers
    Routers --> DTO
    Routers --> Services
    Services --> Domain
    Services --> Rules
    Services --> Parsers
    Services --> Models
    Services --> Learning
    Services --> Prompts
    Services --> Entrances
    Services --> Destinations
    Services --> Repo
    Repo --> DB
    Parsers --> FS
```

## 7. 初始化学习闭环时序图

```mermaid
sequenceDiagram
    actor User as Tenant Owner
    participant UI as Initialization UI
    participant API as Initialization Router
    participant SchemaSvc as SchemaService
    participant TrainSvc as TrainingExampleService
    participant Parser as DocumentParserRegistry
    participant LearnSvc as SchemaLearningService
    participant Model as ModelProviderRegistry
    participant PromptSvc as PromptProfileService
    participant Repo as Repositories

    User->>UI: Create Schema / 上传期望 JSON
    UI->>API: 保存 SchemaDefinition
    API->>SchemaSvc: createOrUpdateSchema()
    SchemaSvc->>Repo: 保存 SchemaVersion
    Repo-->>SchemaSvc: SchemaVersion
    SchemaSvc-->>API: SchemaDefinition
    API-->>UI: Schema 保存成功

    User->>UI: 上传样本文档 + 输入期望 JSON
    UI->>API: createTrainingExample(file, expectedOutput)
    API->>TrainSvc: createExample()
    TrainSvc->>Parser: select(fileType)
    Parser-->>TrainSvc: DocumentParser
    TrainSvc->>TrainSvc: parse document
    TrainSvc->>TrainSvc: validate expected JSON
    TrainSvc->>Repo: 保存 DocumentAsset / ParsedDocument / TrainingExample
    Repo-->>TrainSvc: TrainingExample
    TrainSvc-->>API: TrainingExample
    API-->>UI: 样本创建成功

    User->>UI: 选中 Confirmed 样本并点击 Analyze
    UI->>API: analyzeExamples(workspaceId, exampleIds)
    API->>LearnSvc: generatePromptProfile()
    LearnSvc->>Repo: 读取 Schema + TrainingExamples
    LearnSvc->>Model: select(provider)
    Model-->>LearnSvc: ModelProvider
    LearnSvc->>Model: 总结抽取规则并生成 Prompt
    Model-->>LearnSvc: Prompt draft
    LearnSvc->>PromptSvc: validateAndCreateProfile()
    PromptSvc->>Repo: 保存 PromptProfile version
    PromptSvc-->>LearnSvc: PromptProfile
    LearnSvc-->>API: PromptProfile
    API-->>UI: 进入 Prompts Editing
```

## 8. 字段级纠正时序图

```mermaid
sequenceDiagram
    actor User as Tenant Owner
    participant UI as Analysis Detail UI
    participant API as Correction Router
    participant CorrSvc as CorrectionService
    participant Validator as SchemaCompatibilityValidator
    participant Repo as Repositories

    User->>UI: 打开样本详情
    UI->>API: getTrainingExampleDetail(exampleId)
    API->>Repo: 读取 TrainingExample + ParsedDocument + Schema
    Repo-->>API: Detail
    API-->>UI: 原文预览 + 字段抽取值

    User->>UI: 修改字段值
    UI->>API: saveFieldCorrection(fieldValues)
    API->>CorrSvc: saveCorrection()
    CorrSvc->>Validator: validate field values
    Validator-->>CorrSvc: ValidationResult
    CorrSvc->>Repo: 保存 CorrectionSession
    Repo-->>CorrSvc: CorrectionSession
    CorrSvc-->>API: CorrectionSession
    API-->>UI: 更新字段状态

    User->>UI: Add note
    UI->>API: addCorrectionNote(fieldId, note)
    API->>CorrSvc: addNote()
    CorrSvc->>Repo: 保存 CorrectionNote
    Repo-->>CorrSvc: CorrectionNote
    CorrSvc-->>API: CorrectionNote
    API-->>UI: note 保存成功

    User->>UI: Confirm 或 Reject
    UI->>API: decideCorrection(decision)
    API->>CorrSvc: confirmOrReject()
    CorrSvc->>Repo: 更新 TrainingExample 状态
    Repo-->>CorrSvc: TrainingExample
    CorrSvc-->>API: TrainingExample
    API-->>UI: 返回 Sample 列表
```

## 9. 正式文档同步抽取时序图

```mermaid
sequenceDiagram
    actor User as User or API Consumer
    participant API as Extraction Router
    participant ExtSvc as ExtractionService
    participant WorkspaceSvc as WorkspaceService
    participant Parser as DocumentParserRegistry
    participant Model as ModelProviderRegistry
    participant Validator as OutputValidator
    participant Repo as Repositories

    User->>API: POST /external/api/extract?workspaceId={id}
    API->>ExtSvc: extractSync(workspaceId, file)
    ExtSvc->>WorkspaceSvc: loadActiveWorkspace()
    WorkspaceSvc-->>ExtSvc: Workspace + ActivePromptProfile
    ExtSvc->>Parser: select(fileType)
    Parser-->>ExtSvc: DocumentParser
    ExtSvc->>ExtSvc: parse document
    ExtSvc->>Model: select(promptProfile.modelProvider)
    Model-->>ExtSvc: ModelProvider
    ExtSvc->>Model: extract(parsedDocument, promptProfile)
    Model-->>ExtSvc: extracted JSON
    ExtSvc->>Validator: validateAgainstSchema()
    Validator-->>ExtSvc: completed / incomplete
    ExtSvc->>Repo: 保存 ExtractionTask
    Repo-->>ExtSvc: ExtractionTask
    ExtSvc-->>API: extracted content
    API-->>User: 200 result
```

## 10. 正式文档异步抽取时序图

```mermaid
sequenceDiagram
    actor User as API Consumer
    participant API as Extraction Router
    participant ExtSvc as ExtractionService
    participant Queue as Local Job Scheduler
    participant Worker as Extraction Worker
    participant Repo as Repositories

    User->>API: POST /external/api/extract/async
    API->>ExtSvc: createAsyncTask(workspaceId, file)
    ExtSvc->>Repo: 创建 ExtractionTask(status=ready)
    ExtSvc->>Queue: enqueue(taskId)
    ExtSvc-->>API: taskId
    API-->>User: 202 Accepted

    Queue->>Worker: run(taskId)
    Worker->>Repo: load task
    Worker->>Worker: parse + model extract + validate
    Worker->>Repo: update status completed/incomplete/failed

    User->>API: GET /external/api/extract/result?taskId={taskId}
    API->>Repo: load task result
    Repo-->>API: ExtractionTask
    API-->>User: result / status
```

## 11. Integration 激活时序图

```mermaid
sequenceDiagram
    actor User as Tenant Owner
    participant UI as Integration UI
    participant API as Integration Router
    participant Svc as IntegrationService
    participant Var as VariableReferenceResolver
    participant Registry as ValidationRuleRegistry
    participant Repo as Repositories

    User->>UI: 配置 Start / File Entrance / Scheduler / Mapping / Destination
    UI->>API: saveWorkflow(workflowDefinition)
    API->>Svc: saveDraft()
    Svc->>Repo: 保存 IntegrationWorkflow(status=draft)
    Repo-->>Svc: Workflow
    Svc-->>API: Workflow
    API-->>UI: Auto saved

    User->>UI: Activate
    UI->>API: activateIntegration(workflowId)
    API->>Svc: activate()
    Svc->>Repo: 读取 Workspace + Workflow
    Svc->>Var: validate variable references
    Var-->>Svc: ValidationResult
    Svc->>Registry: getRules(nodeTypes)
    Registry-->>Svc: ActivationRules
    Svc->>Svc: evaluate rules
    alt 有阻断问题
        Svc-->>API: issues
        API-->>UI: 展示校验失败项
    else 校验通过
        Svc->>Repo: 更新 Workflow(status=active)
        Svc-->>API: active workflow
        API-->>UI: Active
    end
```

## 12. 数据流图：初始化学习

```mermaid
flowchart LR
    A[样本文档] --> B[DocumentParser]
    C[期望 JSON] --> D[ExpectedJsonValidator]
    E[SchemaDefinition] --> F[SchemaCompatibilityValidator]
    B --> G[ParsedDocument]
    D --> H[TrainingExample]
    F --> H
    G --> H
    H --> I[SchemaLearningStrategy]
    I --> J[ModelProvider]
    J --> K[Prompt Draft]
    K --> L[PromptGenerator]
    L --> M[PromptProfile]
    M --> N[验证抽取]
    N --> O[模型输出 JSON]
    O --> P[人工纠正]
    P --> Q[CorrectionSession]
    Q --> H
```

## 13. 数据流图：正式抽取与集成

```mermaid
flowchart LR
    A[文件入口 Manual/API/Mailbox/Folder] --> B[FileEntranceConnector]
    B --> C[ExtractionTask ready]
    C --> D[DocumentParser]
    D --> E[ParsedDocument]
    E --> F[Active PromptProfile]
    F --> G[ModelProvider]
    G --> H[Extracted JSON]
    H --> I[OutputValidator]
    I --> J{Valid?}
    J -->|完整| K[Completed]
    J -->|缺失| L[Incomplete]
    J -->|错误| M[Processing Error]
    K --> N[MappingDefinition]
    N --> O[DestinationAdapter]
    O -->|成功| P[Synced]
    O -->|失败| Q[Sync Error]
```

## 14. 数据库 ER 图

```mermaid
erDiagram
    TENANT ||--o{ WORKSPACE : owns
    TENANT ||--o{ MODEL_SETTINGS : configures
    TENANT ||--o{ API_KEY : issues
    WORKSPACE ||--o{ SCHEMA_DEFINITION : versions
    SCHEMA_DEFINITION ||--o{ SCHEMA_GROUP : contains
    SCHEMA_GROUP ||--o{ SCHEMA_FIELD : contains
    SCHEMA_FIELD ||--o{ FIELD_VALIDATION_RULE : validates
    WORKSPACE ||--o{ DOCUMENT_ASSET : stores
    DOCUMENT_ASSET ||--o{ PARSED_DOCUMENT : parsed_as
    WORKSPACE ||--o{ TRAINING_EXAMPLE : learns_from
    TRAINING_EXAMPLE ||--|| DOCUMENT_ASSET : uses
    TRAINING_EXAMPLE ||--o{ CORRECTION_SESSION : reviewed_by
    CORRECTION_SESSION ||--o{ CORRECTION_NOTE : notes
    WORKSPACE ||--o{ PROMPT_PROFILE : has
    PROMPT_PROFILE ||--o{ TRAINING_EXAMPLE : generated_from
    WORKSPACE ||--o{ EXTRACTION_TASK : processes
    EXTRACTION_TASK ||--|| DOCUMENT_ASSET : uses
    EXTRACTION_TASK }o--|| PROMPT_PROFILE : executed_with
    WORKSPACE ||--o{ INTEGRATION_WORKFLOW : configures
    INTEGRATION_WORKFLOW ||--o{ INTEGRATION_NODE : contains
    INTEGRATION_WORKFLOW ||--o{ INTEGRATION_EDGE : connects
    INTEGRATION_NODE ||--o{ VARIABLE_DEFINITION : exposes
    EXTRACTION_TASK ||--o{ DESTINATION_RECORD : syncs_to

    TENANT {
      string id PK
      string name
      string description
      string status
      datetime created_at
      datetime updated_at
    }

    WORKSPACE {
      string id PK
      string tenant_id FK
      string name
      string document_type
      string status
      string active_schema_version_id FK
      string active_prompt_profile_id FK
      datetime created_at
      datetime updated_at
    }

    SCHEMA_DEFINITION {
      string id PK
      string workspace_id FK
      int version
      string status
      json json_schema
      datetime created_at
    }

    SCHEMA_FIELD {
      string id PK
      string group_id FK
      string field_name
      string field_type
      bool required
      string description
    }

    TRAINING_EXAMPLE {
      string id PK
      string workspace_id FK
      string schema_definition_id FK
      string document_asset_id FK
      json expected_output
      json model_output
      json corrected_output
      string status
      datetime created_at
      datetime updated_at
    }

    PROMPT_PROFILE {
      string id PK
      string workspace_id FK
      string schema_definition_id FK
      int version
      string status
      string model_provider
      string model_name
      text system_prompt
      text extraction_instruction
      json field_rules
      datetime created_at
    }

    EXTRACTION_TASK {
      string id PK
      string tenant_id FK
      string workspace_id FK
      string document_asset_id FK
      string prompt_profile_id FK
      string source
      string status
      json extracted_output
      json corrected_output
      json validation_result
      text error_message
      datetime created_at
      datetime updated_at
    }
```

## 15. Workspace 状态机图

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> initializing: 创建 Workspace
    initializing --> initializing: 编辑 Schema / Validation / Sample
    initializing --> ready_for_activation: 有 Schema + Confirmed Sample + PromptProfile
    ready_for_activation --> active: 激活 PromptProfile
    active --> inactive: 手动停用
    inactive --> active: 重新激活
    active --> archived: 归档
    inactive --> archived: 归档
    archived --> [*]
```

## 16. Training Example 状态机图

```mermaid
stateDiagram-v2
    [*] --> uploaded
    uploaded --> parsed: 文档解析成功
    uploaded --> rejected: 文档解析失败或用户删除
    parsed --> expected_output_ready: 输入期望 JSON
    expected_output_ready --> extracted: 执行初始抽取
    extracted --> correction_required: 模型输出待审
    correction_required --> corrected: 用户修改字段或 JSON
    correction_required --> rejected: Reject
    corrected --> accepted: Confirm
    accepted --> analyzed: Analyze 生成 PromptProfile
    rejected --> [*]
    analyzed --> [*]
```

## 17. Prompt Profile 状态机图

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> validating: 用样本验证
    validating --> draft: 验证失败并继续编辑
    validating --> active: 用户激活
    active --> retired: 新版本激活
    draft --> retired: 放弃版本
    retired --> [*]
```

## 18. Extraction Task 状态机图

```mermaid
stateDiagram-v2
    [*] --> ready
    ready --> extracting: Worker 开始处理
    extracting --> completed: 输出完整且校验通过
    extracting --> incomplete: 输出缺字段或格式不完整
    extracting --> processing_error: 解析或模型失败
    completed --> syncing: 存在 Active Integration
    incomplete --> correction_required: 用户手动修正
    correction_required --> completed: 修正后通过校验
    syncing --> synced: 下游发送成功
    syncing --> sync_error: 下游发送失败
    processing_error --> ready: Retry
    sync_error --> syncing: Retry Sync
    failed --> [*]
    synced --> [*]
```

## 19. Integration Workflow 状态机图

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> draft: Auto Save
    draft --> validating: Activate
    validating --> draft: Validation Issues
    validating --> active: Validation Passed
    active --> inactive: Disable
    inactive --> validating: Re-activate
    active --> draft: Edit Workflow
    draft --> deleted: Delete
    inactive --> deleted: Delete
    deleted --> [*]
```

## 20. 部署图

```mermaid
flowchart TB
    subgraph LocalMachine[Local Developer Machine]
        Browser[Browser]
        Frontend[Vite / Static Frontend]
        Backend[FastAPI Backend]
        SQLite[(SQLite)]
        Uploads[(Uploads Folder)]
        Ollama[Ollama Runtime]
    end

    subgraph OptionalExternal[Optional External Integrations]
        ModelApi[OpenAI-compatible Model API]
        HttpTarget[HTTP Destination]
        Mailbox[Mailbox]
        SharedFolder[Shared Folder]
    end

    Browser --> Frontend
    Frontend --> Backend
    Backend --> SQLite
    Backend --> Uploads
    Backend --> Ollama
    Backend -.ModelProvider.-> ModelApi
    Backend -.DestinationAdapter.-> HttpTarget
    Backend -.FileEntranceConnector.-> Mailbox
    Backend -.FileEntranceConnector.-> SharedFolder
```

## 21. 端到端扩展点图

```mermaid
flowchart LR
    Tenant[Tenant Lifecycle]
    Workspace[Workspace Lifecycle]
    Schema[Schema Definition]
    Validation[Field Validation]
    Upload[Document Upload]
    Preflight[Large File Preflight]
    Parse[Document Parsing]
    Chunk[Document Chunking]
    Context[Context Package]
    Expected[Expected JSON]
    Learn[Schema Learning]
    Prompt[Prompt Generation]
    Extract[Extraction]
    Correct[Correction]
    Activate[Activation]
    Entrance[File Entrance]
    Schedule[Scheduler]
    Mapping[Mapping]
    Destination[Destination]
    ApiAccess[API Access]

    Tenant --> Workspace --> Schema --> Validation --> Upload --> Preflight --> Parse --> Chunk --> Context --> Expected --> Learn --> Prompt --> Extract --> Correct --> Activate --> Entrance --> Schedule --> Mapping --> Destination --> ApiAccess

    Tenant -.TenantPolicy.-> TenantExt[Tenant Extension]
    Workspace -.WorkspaceTemplate.-> WorkspaceExt[Workspace Template Extension]
    Schema -.SchemaImporter.-> SchemaExt[Schema Importer Extension]
    Validation -.ValidationRule.-> ValidationExt[Validation Rule Extension]
    Upload -.FileEntranceConnector.-> UploadExt[File Source Extension]
    Preflight -.LargeDocumentPolicy.-> PreflightExt[Large File Policy Extension]
    Parse -.DocumentParser.-> ParseExt[Parser Extension]
    Chunk -.ChunkingStrategy.-> ChunkExt[Chunking Extension]
    Context -.ContextAssemblyStrategy.-> ContextExt[Context Assembly Extension]
    Learn -.SchemaLearningStrategy.-> LearnExt[Learning Strategy Extension]
    Prompt -.PromptGenerator.-> PromptExt[Prompt Generator Extension]
    Extract -.ModelProvider.-> ExtractExt[Model Provider Extension]
    Correct -.CorrectionPolicy.-> CorrectExt[Correction Policy Extension]
    Activate -.ActivationRule.-> ActivateExt[Activation Rule Extension]
    Mapping -.MappingTransformer.-> MappingExt[Mapping Extension]
    Destination -.DestinationAdapter.-> DestinationExt[Destination Extension]
    ApiAccess -.ApiAuthStrategy.-> ApiAccessExt[API Auth Extension]
```

## 22. 大文件处理服务架构图

```mermaid
flowchart TB
    Upload[Upload / API Input] --> Ingestion[DocumentIngestionService]
    Ingestion --> Asset[(DocumentAsset)]
    Ingestion --> Policy[LargeDocumentPolicy]
    Policy -->|sync allowed| SmallPlan[Single Pass ExtractionPlan]
    Policy -->|async required| AsyncTask[Async ExtractionTask]
    Policy -->|rejected| PreflightIssue[Preflight ValidationIssue]

    AsyncTask --> ParserRegistry[DocumentParserRegistry]
    ParserRegistry --> Parsed[(ParsedDocument)]
    Parsed --> Normalizer[DocumentNormalizer]
    Normalizer --> Segment[(DocumentSegment)]
    Segment --> ChunkRegistry[ChunkingStrategyRegistry]
    ChunkRegistry --> Chunk[(DocumentChunk)]
    Chunk --> Index[Local Content Index]

    SmallPlan --> ContextService[ContextEngineeringService]
    Index --> Retrieval[RetrievalStrategy]
    Retrieval --> Planner[ExtractionPlanningService]
    Planner --> ContextService
    ContextService --> TokenBudgeter[TokenBudgeter]
    ContextService --> Context[(ContextPackage)]
    Context --> ModelRegistry[ModelProviderRegistry]
    ModelRegistry --> Invocation[(ModelInvocation)]
    Invocation --> Merger[ExtractionMergeService]
    Merger --> Validation[Schema + Field Validation]
    Validation --> Result[(Extraction Result)]
```

## 23. 大文件抽取时序图

```mermaid
sequenceDiagram
    actor User
    participant UI as Frontend
    participant API as Extraction Router
    participant Ingestion as DocumentIngestionService
    participant Policy as LargeDocumentPolicy
    participant Parser as DocumentParserRegistry
    participant Chunker as ChunkingStrategyRegistry
    participant Planner as ExtractionPlanningService
    participant Context as ContextEngineeringService
    participant Model as ModelProvider
    participant Merger as ExtractionMergeService
    participant Repo as Repositories

    User->>UI: Upload large PDF
    UI->>API: POST async extract
    API->>Ingestion: create document asset
    Ingestion->>Repo: save DocumentAsset metadata and file path
    Ingestion->>Policy: preflight size/pages/type
    Policy-->>Ingestion: async_required
    Ingestion->>Repo: create ExtractionTask uploaded/preflighted
    API-->>UI: task id

    Ingestion->>Parser: parse document
    Parser-->>Ingestion: ParsedDocument
    Ingestion->>Chunker: create chunks
    Chunker-->>Ingestion: DocumentChunk list
    Ingestion->>Repo: save ParsedDocument and chunks
    Ingestion->>Planner: build staged extraction plan
    Planner-->>Ingestion: ExtractionPlan

    loop each ExtractionPass
        Ingestion->>Context: assemble ContextPackage
        Context-->>Ingestion: budgeted prompt and chunk references
        Ingestion->>Model: invoke with ContextPackage
        Model-->>Ingestion: partial JSON
        Ingestion->>Repo: save ModelInvocation and pass output
    end

    Ingestion->>Merger: merge partial outputs
    Merger-->>Ingestion: merged JSON with conflicts
    Ingestion->>Repo: save validation result and final status
    UI->>API: GET task result
    API-->>UI: output, trace, chunk sources, issues
```

## 24. 模型上下文控制数据流图

```mermaid
flowchart LR
    Schema[Schema Contract] --> Budgeter[TokenBudgeter]
    Prompt[PromptProfile] --> Budgeter
    Rules[Field Rules] --> Budgeter
    Examples[Few-shot Examples] --> Budgeter
    Chunks[Candidate DocumentChunks] --> Retriever[RetrievalStrategy]
    TargetFields[Target Field Group] --> Retriever
    Retriever --> CandidateChunks[Ranked Candidate Chunks]
    Budgeter --> ContextAssembler[ContextAssemblyStrategy]
    CandidateChunks --> ContextAssembler
    ContextAssembler --> ContextPackage[(ContextPackage)]
    ContextPackage --> Validator[ContextBudgetValidator]
    Validator -->|valid| ModelCall[Model Invocation]
    Validator -->|over budget| Degrade[Reduce Examples / Field Group / Chunk Count]
    Degrade --> ContextAssembler
    Validator -->|cannot fit| Issue[context_budget_exceeded issue]
```

## 25. 大文件 ER 扩展图

```mermaid
erDiagram
    DOCUMENT_ASSET ||--o{ PARSED_DOCUMENT : parsed_as
    PARSED_DOCUMENT ||--o{ DOCUMENT_SEGMENT : contains
    DOCUMENT_SEGMENT ||--o{ DOCUMENT_CHUNK : chunked_into
    EXTRACTION_TASK ||--o{ EXTRACTION_PLAN : planned_by
    EXTRACTION_PLAN ||--o{ EXTRACTION_PASS : contains
    EXTRACTION_PASS ||--|| CONTEXT_PACKAGE : uses
    CONTEXT_PACKAGE }o--o{ DOCUMENT_CHUNK : includes
    CONTEXT_PACKAGE ||--o{ MODEL_INVOCATION : invokes
    EXTRACTION_PASS ||--o{ EXTRACTION_CHUNK_RESULT : produces
    EXTRACTION_TASK ||--o{ EXTRACTION_MERGE_RESULT : merged_as

    DOCUMENT_ASSET {
      string id PK
      string workspace_id FK
      string mime_type
      int size_bytes
      string sha256
      string storage_path
      int page_count
      string processing_mode
      string preflight_status
    }

    DOCUMENT_CHUNK {
      string id PK
      string parsed_document_id FK
      int chunk_index
      string chunk_type
      string source_range
      int token_count
      text content
      json semantic_hints
    }

    CONTEXT_PACKAGE {
      string id PK
      string workspace_id FK
      string prompt_profile_id FK
      string extraction_task_id FK
      json target_fields
      json chunk_ids
      int token_budget
      int estimated_input_tokens
      int reserved_output_tokens
      string assembly_strategy
    }

    MODEL_INVOCATION {
      string id PK
      string context_package_id FK
      string provider
      string model_name
      int estimated_input_tokens
      int estimated_output_tokens
      int duration_ms
      string status
      text error_message
    }
```

## 26. 大文件处理状态机图

```mermaid
stateDiagram-v2
    [*] --> uploaded
    uploaded --> preflighted
    preflighted --> rejected_by_policy
    preflighted --> sync_allowed
    preflighted --> async_required
    sync_allowed --> extracting
    async_required --> parsing
    parsing --> chunking
    chunking --> indexing
    indexing --> planning
    planning --> assembling_context
    assembling_context --> extracting
    extracting --> merging
    merging --> validating
    validating --> completed
    validating --> correction_required
    parsing --> failed
    chunking --> failed
    assembling_context --> failed
    extracting --> failed
    merging --> failed
    failed --> retrying
    retrying --> parsing
    retrying --> assembling_context
    retrying --> extracting
    correction_required --> completed
```

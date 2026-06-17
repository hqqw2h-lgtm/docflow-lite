# 架构设计

## 1. 架构原则

- 大模型负责规划、查询、决策和调用工具。
- Java 后端负责状态、校验、编译、部署、测试和审计。
- iFlow 的内部模型是 Graph JSON DSL，不是 BPMN XML。
- BPMN XML 和 iFlow ZIP 只能由确定性 compiler 生成。
- 所有外部系统访问通过 Tool / Client 封装。
- 每次需求执行过程必须可追踪、可回放、可评估。

## 2. 总体架构

```text
User / UI / API Client
        |
        v
Spring Boot REST API
        |
        v
Requirement Session Service
        |
        v
LangChain4j Agent Orchestrator
        |
        +--> Knowledge / Skills / Rules Retriever
        +--> OData Discovery Tools
        +--> Communication Tools
        +--> Graph Editing Tools
        +--> Mapping Tools
        +--> Compile / Deploy / Test Tools
        |
        v
Graph JSON DSL Repository
        |
        v
Template-based iFlow Compiler
        |
        v
iFlow ZIP Artifact Store
        |
        v
SAP Integration Suite Design-time / Runtime APIs
        |
        v
Smoke Test + MPL / Trace Analysis
```

## 3. 分层设计

### 3.1 API 层

负责对外暴露 REST API：

- `/api/requirements`
- `/api/graphs`
- `/api/discovery`
- `/api/lifecycle`

API 层只做参数校验和服务编排，不写业务状态逻辑。

### 3.2 Session / Trace 层

保存每个需求的生命周期：

- RequirementSession
- ConversationMessage
- ToolCallTrace
- GraphSnapshot
- Artifact
- Deployment
- TestRun

当前 MVP 使用内存 repository；后续替换为 PostgreSQL。

### 3.3 Agent Orchestration 层

LangChain4j Agent 使用系统提示词、历史消息、retrieved knowledge 和工具列表进行多轮决策。

Agent 的硬规则：

1. 不直接生成 BPMN XML。
2. 使用 OData 前必须查询 metadata。
3. 部署前必须 validate graph。
4. 失败后必须读取 MPL/trace 再修正。
5. 不得将 secret 写入 DSL。

### 3.4 Tool 层

工具分为 read-only discovery tool 和 state mutation tool。

Read-only tools：

- 查询 OData metadata。
- 查询 Communication Arrangement。
- 查询 credential alias 是否存在。
- 查询知识库、样本库、skills、rules。
- 查询部署和 MPL 日志。

State mutation tools：

- createGraph。
- addNode。
- addEdge。
- setNodeProperties。
- setEdgeProperties。
- addDataMappings。
- compileIflow。
- deployIflow。

### 3.5 Graph DSL 层

Graph DSL 是 iFlow 的中间表示：

```text
IntegrationGraph
  - nodes
  - edges
  - resources
  - externalizedParameters
  - version
```

它应支持：

- JSON 序列化。
- schema validation。
- diff。
- snapshot。
- rollback。
- compiler input。

### 3.6 Compiler 层

第一阶段采用 template-based compiler：

```text
Template ZIP
  -> load .iflw XML
  -> apply graph changes
  -> inject scripts / mappings / parameters
  -> update manifest
  -> package ZIP
```

这样比完全从零生成所有 SAP BPMN XML 稳定。

### 3.7 SAP Client 层

封装 SAP 访问能力：

- S/4HANA OData metadata client。
- S/4HANA OData sample query client。
- Integration Suite design-time artifact client。
- Integration Suite deploy client。
- Integration Suite MPL / trace client。

所有 client 通过接口定义，便于 mock 和测试。

## 4. 推荐包结构

```text
com.example.integrationsuiteagent
  agent/              Agent orchestration
  api/                REST controllers and DTOs
  config/             Spring configuration
  domain/graph/       Graph DSL domain model
  domain/session/     Requirement session and trace domain model
  graph/              Graph mutation and validation services
  lifecycle/          Compile/deploy/test lifecycle services
  odata/              OData metadata DTOs and clients
  repository/         Persistence abstraction
  session/            Session services
  tool/               LangChain4j tools
```

## 5. 数据流：创建 PO 查询 iFlow

```text
1. User sends requirement.
2. Session service stores message.
3. Agent retrieves PO query skill and rules.
4. Agent calls getODataMetadata(S4_DEV, API_PURCHASEORDER_2).
5. Agent calls getInboundServiceUrl(S4_DEV, SAP_COM_0053, API_PURCHASEORDER_2).
6. Agent calls createGraph.
7. Agent calls addNode / addEdge / setNodeProperties.
8. Agent calls validateGraph.
9. Agent calls compileIflow.
10. Agent calls uploadAndDeployIflow.
11. Agent calls runSmokeTest.
12. If failed, Agent reads MPL, edits graph, recompiles, redeploys.
```

## 6. 部署架构建议

MVP：

```text
Spring Boot app + in-memory repositories
```

生产化：

```text
Spring Boot app
PostgreSQL
pgvector / Milvus
Object Storage
Redis optional
SAP Integration Suite tenant
S/4HANA systems
LLM provider gateway
```

## 7. 安全设计

- Graph DSL 只保存 credential alias。
- Secret 存在 SAP Integration Suite security material 或企业 secret manager。
- ToolCallTrace 对敏感字段做脱敏。
- 生产部署必须可配置人工确认。
- 按 tenant、system、package、artifact 做权限控制。

## 8. 可观测性

需要记录：

- 每次用户消息。
- 每次模型回复。
- 每次工具调用输入输出。
- Graph 每次版本变化。
- 编译产物 checksum。
- 部署 ID。
- MPL ID。
- smoke test 输入输出。
- 自动修复次数和修复原因。

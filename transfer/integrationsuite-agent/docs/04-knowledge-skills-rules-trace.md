# 样本库、Skills、Rules、知识库与 Trace 设计

## 1. 设计目标

系统不能只依赖模型参数记忆。要让 Integration Suite Agent 越用越聪明，需要把每次成功和失败都沉淀为可检索、可评估、可复用的资产。

核心资产包括：

- 样本库 / few-shot。
- Skills。
- Rules。
- 技术知识库。
- Trace / Eval 数据。

## 2. 样本库 / Few-shot

样本不是简单问答，而是完整任务轨迹。

```json
{
  "taskType": "S4_ODATA_QUERY_IFLOW",
  "userGoal": "创建查询采购订单的 iFlow",
  "systemContext": {
    "targetSystem": "S4_DEV",
    "api": "API_PURCHASEORDER_2",
    "scenario": "SAP_COM_0053"
  },
  "toolSequence": [
    "retrieveKnowledge",
    "getODataMetadata",
    "getInboundServiceUrl",
    "createGraph",
    "addNode",
    "addEdge",
    "validateGraph",
    "compileIflow",
    "uploadAndDeployIflow",
    "runSmokeTest"
  ],
  "finalGraph": {},
  "testResult": "PASS",
  "lessons": [
    "Use _PurchaseOrderItem for OData V4 expand",
    "Use credential alias instead of storing password"
  ]
}
```

## 3. Skills

Skill 是可复用的工作流手册。

示例：`build_s4_purchase_order_query_iflow`

```text
适用场景：用户要查询 S/4HANA Purchase Order。
步骤：
1. 使用 API_PURCHASEORDER_2。
2. Communication Scenario 使用 SAP_COM_0053。
3. 查询 $metadata。
4. 使用 PurchaseOrder entity set。
5. 如需 item，使用 $expand=_PurchaseOrderItem。
6. 创建 HTTP sender。
7. 添加 request reply 和 OData receiver。
8. 部署前 validateGraph。
9. 部署后 runSmokeTest 并读取 MPL。
常见坑：
- V2 是 API_PURCHASEORDER_PROCESS_SRV，V4 是 API_PURCHASEORDER_2。
- V2 item navigation 是 to_PurchaseOrderItem，V4 是 _PurchaseOrderItem。
- 不要把 Communication User 密码写进 DSL。
```

## 4. Rules

Rules 是硬约束，必须同时给模型和后端校验器使用。

示例：

```yaml
- id: no-secrets-in-dsl
  severity: error
  description: Graph DSL must not contain passwords, tokens, or client secrets.
  enforcement: graph-validator

- id: odata-metadata-before-usage
  severity: error
  description: Agent must inspect metadata before configuring an OData receiver.
  enforcement: agent-policy

- id: validate-before-compile
  severity: error
  description: Graph must be validated before compiler runs.
  enforcement: lifecycle-service

- id: exception-subprocess-for-production
  severity: warning
  description: Production iFlows should contain an exception subprocess.
  enforcement: graph-validator
```

## 5. 知识库

知识库内容来源：

- SAP 官方文档摘要。
- SAP Business Accelerator Hub API 信息。
- 企业内部集成规范。
- S/4HANA Communication Arrangement 配置说明。
- 常见 MPL 错误和解决方案。
- 已有 iFlow 模板说明。
- 字段映射规则和业务术语表。

检索建议：

```text
keyword search + vector search + metadata filter
```

metadata 示例：

```json
{
  "system": "S4_DEV",
  "api": "API_PURCHASEORDER_2",
  "component": "ODATA_RECEIVER",
  "taskType": "QUERY",
  "sapScenario": "SAP_COM_0053"
}
```

## 6. Trace 模型

每个需求 session 必须记录：

```text
RequirementSession
ConversationMessage
ToolCallTrace
GraphSnapshot
Artifact
Deployment
TestRun
Feedback
```

### 6.1 ToolCallTrace

```json
{
  "toolName": "getODataMetadata",
  "inputJson": {
    "systemId": "S4_DEV",
    "serviceName": "API_PURCHASEORDER_2"
  },
  "outputJson": {},
  "status": "SUCCESS",
  "durationMs": 812,
  "createdAt": "..."
}
```

### 6.2 GraphSnapshot

```json
{
  "version": 7,
  "changeSummary": "Added OData receiver and _PurchaseOrderItem expand",
  "graphJson": {}
}
```

## 7. Eval 设计

为了持续优化模型和工具，需要评测集。

示例 case：

```yaml
id: eval-po-query-iflow
input: 创建查询采购订单的 iFlow，返回 header 和 item
expected:
  mustUseApi: API_PURCHASEORDER_2
  mustUseScenario: SAP_COM_0053
  mustInspectMetadata: true
  mustUseExpand: _PurchaseOrderItem
  mustValidateGraph: true
  mustNotStoreSecrets: true
```

指标：

- 工具调用正确率。
- Graph validation pass rate。
- 编译成功率。
- 部署成功率。
- smoke test pass rate。
- 自动修复成功率。
- 人工介入次数。
- 规则违反次数。

## 8. 从 Trace 到知识资产

成功 session：

```text
Trace -> 自动总结 -> few-shot candidate -> 人工审核 -> 样本库
```

失败 session：

```text
Trace + MPL error -> root cause -> debug skill / rule candidate -> 人工审核 -> rules / skills
```

这样系统才能从每次使用中学习。

# Graph JSON DSL 与 Tool 设计

## 1. 为什么使用 Graph JSON DSL

iFlow 的底层 artifact 包含 BPMN XML、SAP `ifl` 扩展属性、图形坐标、adapter 配置、脚本、mapping 和参数文件。直接让大模型生成这些文件不稳定。

Graph JSON DSL 提供一个更稳定的中间层：

- 大模型容易理解。
- 工具容易增删改。
- Java 容易校验。
- 可以版本化、diff 和回滚。
- 可以由 compiler 转换成 SAP artifact。

## 2. 顶层结构

```json
{
  "id": "graph_001",
  "sessionId": "req_001",
  "name": "Query Purchase Order",
  "packageId": "PKG_PROCUREMENT",
  "version": 3,
  "nodes": [],
  "edges": [],
  "resources": {
    "mappings": [],
    "scripts": [],
    "schemas": []
  },
  "externalizedParameters": {}
}
```

## 3. Node

```json
{
  "id": "odata_receiver_001",
  "type": "ODATA_RECEIVER",
  "label": "Read Purchase Order",
  "position": { "x": 500, "y": 200 },
  "properties": {
    "systemId": "S4_DEV",
    "serviceName": "API_PURCHASEORDER_2",
    "entitySet": "PurchaseOrder",
    "operation": "GET",
    "queryOptions": "$expand=_PurchaseOrderItem",
    "credentialAlias": "S4_PO_API"
  }
}
```

### 3.1 NodeType 枚举

MVP 支持：

- `START_EVENT`
- `END_EVENT`
- `HTTP_SENDER`
- `CONTENT_MODIFIER`
- `REQUEST_REPLY`
- `ODATA_RECEIVER`
- `GROOVY_SCRIPT`
- `MESSAGE_MAPPING`
- `ROUTER`
- `EXCEPTION_SUBPROCESS`

后续可扩展：

- SOAP sender / receiver
- SFTP sender / receiver
- JMS sender / receiver
- Splitter
- Gather
- Multicast
- Value mapping
- Local integration process

## 4. Edge

```json
{
  "id": "edge_001",
  "type": "SEQUENCE_FLOW",
  "source": "http_sender_001",
  "target": "request_reply_001",
  "properties": {}
}
```

### 4.1 EdgeType 枚举

- `SEQUENCE_FLOW`
- `MESSAGE_FLOW`
- `ROUTER_BRANCH`
- `EXCEPTION_FLOW`

Router branch 示例：

```json
{
  "type": "ROUTER_BRANCH",
  "properties": {
    "conditionType": "simple",
    "condition": "${property.country} = 'CN'"
  }
}
```

## 5. Data Mapping

```json
{
  "id": "mapping_001",
  "name": "SourceOrderToPurchaseOrder",
  "rules": [
    {
      "sourcePath": "$.supplierCode",
      "targetPath": "$.Supplier",
      "expression": "source.supplierCode",
      "note": "Supplier code is already aligned with S/4 vendor ID"
    }
  ]
}
```

## 6. 原子 Graph Tool

### 6.1 createGraph

创建新的 iFlow Graph DSL。

```json
{
  "sessionId": "req_001",
  "name": "Query Purchase Order",
  "packageId": "PKG_PROCUREMENT"
}
```

### 6.2 addNode

新增节点。

```json
{
  "graphId": "graph_001",
  "nodeType": "HTTP_SENDER",
  "label": "Inbound HTTP",
  "position": { "x": 100, "y": 200 },
  "properties": {
    "path": "/purchase-orders"
  }
}
```

### 6.3 setNodeProperties

合并更新节点属性。

```json
{
  "graphId": "graph_001",
  "nodeId": "odata_receiver_001",
  "properties": {
    "queryOptions": "$expand=_PurchaseOrderItem"
  }
}
```

### 6.4 addEdge

新增边。

```json
{
  "graphId": "graph_001",
  "sourceNodeId": "http_sender_001",
  "targetNodeId": "request_reply_001",
  "edgeType": "SEQUENCE_FLOW",
  "properties": {}
}
```

### 6.5 setEdgeProperties

更新边属性，常用于 router branch condition。

### 6.6 addDataMappings

添加 mapping 规则。

### 6.7 validateGraph

执行结构和规则校验。

## 7. Discovery Tool

### 7.1 OData tools

- `listODataServices(systemId)`
- `getODataMetadata(systemId, serviceName)`
- `getEntityType(systemId, serviceName, entityName)`
- `queryOData(command)`

这些工具防止大模型猜字段、猜 entity set、猜 navigation property。

### 7.2 Communication tools

- `listCommunicationArrangements(systemId)`
- `getInboundServiceUrl(systemId, scenarioId, serviceName)`
- `validateCredentialAlias(tenantId, credentialAlias)`

### 7.3 Knowledge tools

- `retrieveKnowledge(query)`
- 返回 rules、skills、few-shot、内部文档片段。

## 8. Validation Rules

MVP 中已包含：

- Edge source / target 必须存在。
- Router branch 必须有 condition。
- `HTTP_SENDER` 必须有 `path`。
- `ODATA_RECEIVER` 必须有 `systemId`、`serviceName`、`entitySet`、`operation`、`credentialAlias`。
- Graph DSL 禁止保存 password、secret、token 类字段。

后续规则：

- 所有 receiver 必须设置 timeout。
- 所有 endpoint 必须 externalized。
- 生产 iFlow 必须有 exception subprocess。
- OData write 操作必须处理 CSRF token。
- 部署生产前必须人工确认。

## 9. PO 查询 Graph 示例

```json
{
  "name": "Query Purchase Order",
  "nodes": [
    { "id": "start_1", "type": "START_EVENT", "label": "Start" },
    {
      "id": "http_sender_1",
      "type": "HTTP_SENDER",
      "label": "HTTP Sender",
      "properties": { "path": "/purchase-orders/{poNumber}" }
    },
    {
      "id": "request_reply_1",
      "type": "REQUEST_REPLY",
      "label": "Call S4"
    },
    {
      "id": "odata_receiver_1",
      "type": "ODATA_RECEIVER",
      "label": "Read PO",
      "properties": {
        "systemId": "S4_DEV",
        "serviceName": "API_PURCHASEORDER_2",
        "entitySet": "PurchaseOrder",
        "operation": "GET",
        "queryOptions": "$expand=_PurchaseOrderItem",
        "credentialAlias": "S4_PO_API"
      }
    },
    { "id": "end_1", "type": "END_EVENT", "label": "End" }
  ],
  "edges": [
    { "source": "start_1", "target": "http_sender_1", "type": "SEQUENCE_FLOW" },
    { "source": "http_sender_1", "target": "request_reply_1", "type": "SEQUENCE_FLOW" },
    { "source": "request_reply_1", "target": "odata_receiver_1", "type": "MESSAGE_FLOW" },
    { "source": "request_reply_1", "target": "end_1", "type": "SEQUENCE_FLOW" }
  ]
}
```

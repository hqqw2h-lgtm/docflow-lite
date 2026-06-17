# Integration Suite Agent

Integration Suite Agent is a Java/Spring Boot prototype for an agentic SAP Integration Suite iFlow builder.

The core idea is:

```text
User requirement
  -> LangChain4j orchestrator
  -> discovery tools / graph tools / knowledge tools
  -> graph-based JSON DSL
  -> deterministic compiler
  -> iFlow ZIP upload, deployment, smoke test, and trace analysis
```

The model never writes SAP BPMN XML directly. It calls tools such as `addNode`, `addEdge`, `setNodeProperties`, and `addDataMappings`; the backend validates and versions the graph JSON DSL.

## Modules in this prototype

- Requirement sessions and conversation trace
- Tool call trace model
- Graph JSON DSL with node/edge/resource/mapping state
- Atomic graph editing tools
- OData discovery tool contracts with safe sample responses
- Knowledge, rules, skills, and few-shot retrieval contracts
- Compile/deploy/test lifecycle contracts with placeholder implementations
- REST APIs for driving and inspecting sessions and graphs


## Documentation

- [Requirements](docs/01-requirements.md)
- [Architecture Design](docs/02-architecture.md)
- [Graph DSL and Tools](docs/03-graph-dsl-and-tools.md)
- [Knowledge, Skills, Rules, and Trace](docs/04-knowledge-skills-rules-trace.md)
- [Roadmap](docs/05-roadmap.md)

## Run

```bash
mvn spring-boot:run
```

Open Swagger UI:

```text
http://localhost:8080/swagger-ui.html
```

## Example flow

Create a requirement session:

```bash
curl -X POST http://localhost:8080/api/requirements \
  -H 'Content-Type: application/json' \
  -d '{"title":"Build PO query iFlow","userId":"demo","targetEnvironment":"S4_DEV","initialMessage":"创建一个查询采购订单的 iFlow"}'
```

Create a graph:

```bash
curl -X POST http://localhost:8080/api/graphs \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"<session-id>","name":"Query Purchase Order","packageId":"PKG_PROCUREMENT"}'
```

## Next implementation milestones

1. Replace in-memory repositories with PostgreSQL persistence.
2. Add pgvector or Milvus backed retrieval for sample library, skills, and rules.
3. Implement SAP S/4HANA OData metadata clients.
4. Implement SAP Integration Suite design-time artifact upload/deploy clients.
5. Implement template-based `.iflw` compiler and ZIP packager.
6. Add real LangChain4j tool-calling loop with model/provider configuration.

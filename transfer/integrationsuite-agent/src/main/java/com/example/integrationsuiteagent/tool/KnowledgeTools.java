package com.example.integrationsuiteagent.tool;

import dev.langchain4j.agent.tool.Tool;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class KnowledgeTools {

    public record KnowledgeHit(String type, String title, String content, double score) {
    }

    @Tool("Retrieve skills, rules, samples, and knowledge snippets relevant to the requirement")
    public List<KnowledgeHit> retrieveKnowledge(String query) {
        return List.of(
                new KnowledgeHit("RULE", "Never store secrets in DSL", "Use credential aliases for passwords, tokens, and OAuth secrets.", 0.98),
                new KnowledgeHit("SKILL", "Build S4 purchase order query iFlow", "Use API_PURCHASEORDER_2, SAP_COM_0053, PurchaseOrder entity set, and _PurchaseOrderItem expand for items.", 0.95),
                new KnowledgeHit("FEW_SHOT", "PO query sample", "Tool path: getODataMetadata -> getInboundServiceUrl -> createGraph -> addNode HTTP_SENDER -> addNode REQUEST_REPLY -> addNode ODATA_RECEIVER -> addEdge -> validateGraph.", 0.91)
        );
    }
}

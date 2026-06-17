package com.example.integrationsuiteagent.graph;

import com.example.integrationsuiteagent.domain.graph.EdgeType;
import com.example.integrationsuiteagent.domain.graph.IntegrationGraph;
import com.example.integrationsuiteagent.domain.graph.NodeType;
import com.example.integrationsuiteagent.repository.InMemoryGraphRepository;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class GraphServiceTest {

    private final GraphService graphService = new GraphService(new InMemoryGraphRepository());

    @Test
    void buildsAndValidatesPurchaseOrderQueryGraph() {
        IntegrationGraph graph = graphService.createGraph(new CreateGraphCommand("req_1", "Query PO", "PKG_PROCUREMENT"));
        String start = graphService.addNode(new AddNodeCommand(graph.getId(), NodeType.START_EVENT, "Start", null, Map.of()))
                .changedObjectId();
        String sender = graphService.addNode(new AddNodeCommand(graph.getId(), NodeType.HTTP_SENDER, "HTTP Sender", null,
                        Map.of("path", "/purchase-orders")))
                .changedObjectId();
        String receiver = graphService.addNode(new AddNodeCommand(graph.getId(), NodeType.ODATA_RECEIVER, "Read PO", null,
                        Map.of(
                                "systemId", "S4_DEV",
                                "serviceName", "API_PURCHASEORDER_2",
                                "entitySet", "PurchaseOrder",
                                "operation", "GET",
                                "credentialAlias", "S4_PO_API"
                        )))
                .changedObjectId();
        String end = graphService.addNode(new AddNodeCommand(graph.getId(), NodeType.END_EVENT, "End", null, Map.of()))
                .changedObjectId();

        graphService.addEdge(new AddEdgeCommand(graph.getId(), start, sender, EdgeType.SEQUENCE_FLOW, Map.of()));
        graphService.addEdge(new AddEdgeCommand(graph.getId(), sender, receiver, EdgeType.SEQUENCE_FLOW, Map.of()));
        graphService.addEdge(new AddEdgeCommand(graph.getId(), receiver, end, EdgeType.SEQUENCE_FLOW, Map.of()));

        ValidationResult validation = graphService.validate(graph.getId());

        assertThat(validation.valid()).isTrue();
    }

    @Test
    void rejectsSecretLikeNodeProperties() {
        IntegrationGraph graph = graphService.createGraph(new CreateGraphCommand("req_1", "Unsafe", "PKG"));
        graphService.addNode(new AddNodeCommand(graph.getId(), NodeType.ODATA_RECEIVER, "Read PO", null,
                Map.of(
                        "systemId", "S4_DEV",
                        "serviceName", "API_PURCHASEORDER_2",
                        "entitySet", "PurchaseOrder",
                        "operation", "GET",
                        "credentialAlias", "S4_PO_API",
                        "password", "do-not-store"
                )));

        ValidationResult validation = graphService.validate(graph.getId());

        assertThat(validation.valid()).isFalse();
        assertThat(validation.issues()).anyMatch(issue -> issue.message().contains("Secrets must not be stored"));
    }
}

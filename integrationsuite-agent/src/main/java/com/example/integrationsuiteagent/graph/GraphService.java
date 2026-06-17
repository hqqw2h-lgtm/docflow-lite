package com.example.integrationsuiteagent.graph;

import com.example.integrationsuiteagent.domain.graph.DataMapping;
import com.example.integrationsuiteagent.domain.graph.EdgeType;
import com.example.integrationsuiteagent.domain.graph.GraphEdge;
import com.example.integrationsuiteagent.domain.graph.GraphNode;
import com.example.integrationsuiteagent.domain.graph.IntegrationGraph;
import com.example.integrationsuiteagent.domain.graph.NodeType;
import com.example.integrationsuiteagent.domain.graph.Position;
import com.example.integrationsuiteagent.repository.GraphRepository;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class GraphService {

    private final GraphRepository graphRepository;

    public GraphService(GraphRepository graphRepository) {
        this.graphRepository = graphRepository;
    }

    public IntegrationGraph createGraph(CreateGraphCommand command) {
        IntegrationGraph graph = new IntegrationGraph(
                newId("graph"),
                command.sessionId(),
                command.name(),
                command.packageId()
        );
        return graphRepository.save(graph);
    }

    public IntegrationGraph getGraph(String graphId) {
        return graphRepository.findById(graphId)
                .orElseThrow(() -> new IllegalArgumentException("Graph not found: " + graphId));
    }

    public List<IntegrationGraph> getGraphsBySession(String sessionId) {
        return graphRepository.findBySessionId(sessionId);
    }

    public GraphMutationResult addNode(AddNodeCommand command) {
        IntegrationGraph graph = getGraph(command.graphId());
        Map<String, Object> properties = command.properties() == null ? Map.of() : command.properties();
        GraphNode node = new GraphNode(
                newId(command.nodeType().name().toLowerCase()),
                command.nodeType(),
                command.label(),
                command.position() == null ? Position.origin() : command.position(),
                properties
        );
        graph.getNodes().add(node);
        graph.touch();
        graphRepository.save(graph);
        return new GraphMutationResult(graph.getId(), node.getId(), graph.getVersion(), graph, validate(graph).issues());
    }

    public GraphMutationResult setNodeProperties(SetNodePropertiesCommand command) {
        IntegrationGraph graph = getGraph(command.graphId());
        GraphNode node = findNode(graph, command.nodeId());
        node.mergeProperties(command.properties());
        graph.touch();
        graphRepository.save(graph);
        return new GraphMutationResult(graph.getId(), node.getId(), graph.getVersion(), graph, validate(graph).issues());
    }

    public GraphMutationResult addEdge(AddEdgeCommand command) {
        IntegrationGraph graph = getGraph(command.graphId());
        findNode(graph, command.sourceNodeId());
        findNode(graph, command.targetNodeId());
        Map<String, Object> properties = command.properties() == null ? Map.of() : command.properties();
        GraphEdge edge = new GraphEdge(
                newId(command.edgeType().name().toLowerCase()),
                command.edgeType(),
                command.sourceNodeId(),
                command.targetNodeId(),
                properties
        );
        graph.getEdges().add(edge);
        graph.touch();
        graphRepository.save(graph);
        return new GraphMutationResult(graph.getId(), edge.getId(), graph.getVersion(), graph, validate(graph).issues());
    }

    public GraphMutationResult setEdgeProperties(SetEdgePropertiesCommand command) {
        IntegrationGraph graph = getGraph(command.graphId());
        GraphEdge edge = findEdge(graph, command.edgeId());
        edge.mergeProperties(command.properties());
        graph.touch();
        graphRepository.save(graph);
        return new GraphMutationResult(graph.getId(), edge.getId(), graph.getVersion(), graph, validate(graph).issues());
    }

    public GraphMutationResult addDataMappings(AddDataMappingsCommand command) {
        IntegrationGraph graph = getGraph(command.graphId());
        DataMapping mapping = new DataMapping(newId("mapping"), command.name(), command.rules());
        graph.getResources().getMappings().add(mapping);
        graph.touch();
        graphRepository.save(graph);
        return new GraphMutationResult(graph.getId(), mapping.getId(), graph.getVersion(), graph, validate(graph).issues());
    }

    public GraphMutationResult setExternalizedParameter(String graphId, String name, String defaultValue) {
        IntegrationGraph graph = getGraph(graphId);
        graph.getExternalizedParameters().put(name, defaultValue);
        graph.touch();
        graphRepository.save(graph);
        return new GraphMutationResult(graph.getId(), name, graph.getVersion(), graph, validate(graph).issues());
    }

    public ValidationResult validate(String graphId) {
        return validate(getGraph(graphId));
    }

    public ValidationResult validate(IntegrationGraph graph) {
        List<ValidationIssue> issues = new ArrayList<>();
        requireNodeType(graph, NodeType.START_EVENT, issues);
        requireNodeType(graph, NodeType.END_EVENT, issues);
        validateEdges(graph, issues);
        validateNodeProperties(graph, issues);
        return new ValidationResult(issues.stream().noneMatch(issue -> "ERROR".equals(issue.severity())), issues);
    }

    private void requireNodeType(IntegrationGraph graph, NodeType type, List<ValidationIssue> issues) {
        boolean exists = graph.getNodes().stream().anyMatch(node -> node.getType() == type);
        if (!exists) {
            issues.add(new ValidationIssue("WARN", "nodes", "Graph does not contain " + type));
        }
    }

    private void validateEdges(IntegrationGraph graph, List<ValidationIssue> issues) {
        for (GraphEdge edge : graph.getEdges()) {
            if (graph.getNodes().stream().noneMatch(node -> node.getId().equals(edge.getSource()))) {
                issues.add(new ValidationIssue("ERROR", "edges." + edge.getId() + ".source", "Source node does not exist"));
            }
            if (graph.getNodes().stream().noneMatch(node -> node.getId().equals(edge.getTarget()))) {
                issues.add(new ValidationIssue("ERROR", "edges." + edge.getId() + ".target", "Target node does not exist"));
            }
            if (edge.getType() == EdgeType.ROUTER_BRANCH && !edge.getProperties().containsKey("condition")) {
                issues.add(new ValidationIssue("ERROR", "edges." + edge.getId() + ".properties.condition", "Router branch requires a condition"));
            }
        }
    }

    private void validateNodeProperties(IntegrationGraph graph, List<ValidationIssue> issues) {
        for (GraphNode node : graph.getNodes()) {
            Map<String, Object> properties = node.getProperties();
            switch (node.getType()) {
                case HTTP_SENDER -> requireProperties(node, properties, issues, "path");
                case ODATA_RECEIVER -> requireProperties(node, properties, issues,
                        "systemId", "serviceName", "entitySet", "operation", "credentialAlias");
                case GROOVY_SCRIPT -> requireProperties(node, properties, issues, "scriptName");
                case MESSAGE_MAPPING -> requireProperties(node, properties, issues, "mappingId");
                case CONTENT_MODIFIER, REQUEST_REPLY, ROUTER, EXCEPTION_SUBPROCESS, START_EVENT, END_EVENT -> {
                }
            }
            warnOnSecretLikeProperties(node, properties, issues);
        }
    }

    private void requireProperties(GraphNode node, Map<String, Object> properties, List<ValidationIssue> issues, String... required) {
        for (String key : required) {
            Object value = properties.get(key);
            if (value == null || !StringUtils.hasText(String.valueOf(value))) {
                issues.add(new ValidationIssue("ERROR", "nodes." + node.getId() + ".properties." + key,
                        node.getType() + " requires property " + key));
            }
        }
    }

    private void warnOnSecretLikeProperties(GraphNode node, Map<String, Object> properties, List<ValidationIssue> issues) {
        for (String key : properties.keySet()) {
            String normalized = key.toLowerCase();
            if (normalized.contains("password") || normalized.contains("secret") || normalized.contains("token")) {
                issues.add(new ValidationIssue("ERROR", "nodes." + node.getId() + ".properties." + key,
                        "Secrets must not be stored in graph DSL; use a credential alias"));
            }
        }
    }

    private GraphNode findNode(IntegrationGraph graph, String nodeId) {
        return graph.getNodes().stream()
                .filter(node -> node.getId().equals(nodeId))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Node not found: " + nodeId));
    }

    private GraphEdge findEdge(IntegrationGraph graph, String edgeId) {
        return graph.getEdges().stream()
                .filter(edge -> edge.getId().equals(edgeId))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Edge not found: " + edgeId));
    }

    private String newId(String prefix) {
        return prefix + "_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
    }
}

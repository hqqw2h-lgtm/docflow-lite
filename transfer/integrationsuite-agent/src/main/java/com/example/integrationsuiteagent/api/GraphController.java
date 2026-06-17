package com.example.integrationsuiteagent.api;

import com.example.integrationsuiteagent.domain.graph.IntegrationGraph;
import com.example.integrationsuiteagent.graph.AddDataMappingsCommand;
import com.example.integrationsuiteagent.graph.AddEdgeCommand;
import com.example.integrationsuiteagent.graph.AddNodeCommand;
import com.example.integrationsuiteagent.graph.CreateGraphCommand;
import com.example.integrationsuiteagent.graph.GraphMutationResult;
import com.example.integrationsuiteagent.graph.GraphService;
import com.example.integrationsuiteagent.graph.SetEdgePropertiesCommand;
import com.example.integrationsuiteagent.graph.SetNodePropertiesCommand;
import com.example.integrationsuiteagent.graph.ValidationResult;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/graphs")
public class GraphController {

    private final GraphService graphService;

    public GraphController(GraphService graphService) {
        this.graphService = graphService;
    }

    @PostMapping
    public IntegrationGraph createGraph(@Valid @RequestBody CreateGraphCommand command) {
        return graphService.createGraph(command);
    }

    @GetMapping("/{graphId}")
    public IntegrationGraph getGraph(@PathVariable String graphId) {
        return graphService.getGraph(graphId);
    }

    @GetMapping("/by-session/{sessionId}")
    public List<IntegrationGraph> getGraphsBySession(@PathVariable String sessionId) {
        return graphService.getGraphsBySession(sessionId);
    }

    @PostMapping("/{graphId}/nodes")
    public GraphMutationResult addNode(@PathVariable String graphId, @Valid @RequestBody AddNodeCommand command) {
        return graphService.addNode(new AddNodeCommand(graphId, command.nodeType(), command.label(), command.position(), command.properties()));
    }

    @PutMapping("/{graphId}/nodes/{nodeId}/properties")
    public GraphMutationResult setNodeProperties(
            @PathVariable String graphId,
            @PathVariable String nodeId,
            @Valid @RequestBody SetNodePropertiesCommand command
    ) {
        return graphService.setNodeProperties(new SetNodePropertiesCommand(graphId, nodeId, command.properties()));
    }

    @PostMapping("/{graphId}/edges")
    public GraphMutationResult addEdge(@PathVariable String graphId, @Valid @RequestBody AddEdgeCommand command) {
        return graphService.addEdge(new AddEdgeCommand(graphId, command.sourceNodeId(), command.targetNodeId(), command.edgeType(), command.properties()));
    }

    @PutMapping("/{graphId}/edges/{edgeId}/properties")
    public GraphMutationResult setEdgeProperties(
            @PathVariable String graphId,
            @PathVariable String edgeId,
            @Valid @RequestBody SetEdgePropertiesCommand command
    ) {
        return graphService.setEdgeProperties(new SetEdgePropertiesCommand(graphId, edgeId, command.properties()));
    }

    @PostMapping("/{graphId}/mappings")
    public GraphMutationResult addDataMappings(@PathVariable String graphId, @Valid @RequestBody AddDataMappingsCommand command) {
        return graphService.addDataMappings(new AddDataMappingsCommand(graphId, command.name(), command.rules()));
    }

    @PostMapping("/{graphId}/validate")
    public ValidationResult validateGraph(@PathVariable String graphId) {
        return graphService.validate(graphId);
    }
}

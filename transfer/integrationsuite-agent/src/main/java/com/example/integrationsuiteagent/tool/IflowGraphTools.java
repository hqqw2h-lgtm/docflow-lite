package com.example.integrationsuiteagent.tool;

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
import dev.langchain4j.agent.tool.Tool;
import org.springframework.stereotype.Component;

@Component
public class IflowGraphTools {

    private final GraphService graphService;

    public IflowGraphTools(GraphService graphService) {
        this.graphService = graphService;
    }

    @Tool("Create a new iFlow graph JSON DSL model")
    public IntegrationGraph createGraph(CreateGraphCommand command) {
        return graphService.createGraph(command);
    }

    @Tool("Add a node to the current iFlow graph JSON DSL")
    public GraphMutationResult addNode(AddNodeCommand command) {
        return graphService.addNode(command);
    }

    @Tool("Set or merge properties for an existing iFlow graph node")
    public GraphMutationResult setNodeProperties(SetNodePropertiesCommand command) {
        return graphService.setNodeProperties(command);
    }

    @Tool("Add an edge between two iFlow graph nodes")
    public GraphMutationResult addEdge(AddEdgeCommand command) {
        return graphService.addEdge(command);
    }

    @Tool("Set or merge properties for an existing iFlow graph edge")
    public GraphMutationResult setEdgeProperties(SetEdgePropertiesCommand command) {
        return graphService.setEdgeProperties(command);
    }

    @Tool("Add data mapping rules to the iFlow graph resources")
    public GraphMutationResult addDataMappings(AddDataMappingsCommand command) {
        return graphService.addDataMappings(command);
    }

    @Tool("Set an externalized parameter on the iFlow graph")
    public GraphMutationResult setExternalizedParameter(String graphId, String name, String defaultValue) {
        return graphService.setExternalizedParameter(graphId, name, defaultValue);
    }

    @Tool("Validate the current iFlow graph JSON DSL")
    public ValidationResult validateGraph(String graphId) {
        return graphService.validate(graphId);
    }
}

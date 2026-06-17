package com.example.integrationsuiteagent.graph;

import com.example.integrationsuiteagent.domain.graph.IntegrationGraph;

import java.util.List;

public record GraphMutationResult(
        String graphId,
        String changedObjectId,
        int graphVersion,
        IntegrationGraph graph,
        List<ValidationIssue> warnings
) {
}

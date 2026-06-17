package com.example.integrationsuiteagent.graph;

import com.example.integrationsuiteagent.domain.graph.EdgeType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.Map;

public record AddEdgeCommand(
        @NotBlank String graphId,
        @NotBlank String sourceNodeId,
        @NotBlank String targetNodeId,
        @NotNull EdgeType edgeType,
        Map<String, Object> properties
) {
}

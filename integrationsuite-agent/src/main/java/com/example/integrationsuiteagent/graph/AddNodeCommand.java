package com.example.integrationsuiteagent.graph;

import com.example.integrationsuiteagent.domain.graph.NodeType;
import com.example.integrationsuiteagent.domain.graph.Position;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.Map;

public record AddNodeCommand(
        @NotBlank String graphId,
        @NotNull NodeType nodeType,
        @NotBlank String label,
        Position position,
        Map<String, Object> properties
) {
}

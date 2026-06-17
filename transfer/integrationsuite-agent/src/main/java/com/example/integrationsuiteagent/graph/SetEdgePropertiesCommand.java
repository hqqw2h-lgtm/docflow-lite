package com.example.integrationsuiteagent.graph;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.Map;

public record SetEdgePropertiesCommand(
        @NotBlank String graphId,
        @NotBlank String edgeId,
        @NotNull Map<String, Object> properties
) {
}

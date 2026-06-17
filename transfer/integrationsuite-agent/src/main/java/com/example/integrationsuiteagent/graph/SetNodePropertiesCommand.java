package com.example.integrationsuiteagent.graph;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.Map;

public record SetNodePropertiesCommand(
        @NotBlank String graphId,
        @NotBlank String nodeId,
        @NotNull Map<String, Object> properties
) {
}

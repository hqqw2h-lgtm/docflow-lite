package com.example.integrationsuiteagent.graph;

import jakarta.validation.constraints.NotBlank;

public record CreateGraphCommand(
        @NotBlank String sessionId,
        @NotBlank String name,
        @NotBlank String packageId
) {
}

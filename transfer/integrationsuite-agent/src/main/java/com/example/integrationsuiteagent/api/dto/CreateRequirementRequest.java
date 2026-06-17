package com.example.integrationsuiteagent.api.dto;

import jakarta.validation.constraints.NotBlank;

public record CreateRequirementRequest(
        @NotBlank String title,
        @NotBlank String userId,
        @NotBlank String targetEnvironment,
        String initialMessage
) {
}

package com.example.integrationsuiteagent.graph;

import java.util.List;

public record ValidationResult(
        boolean valid,
        List<ValidationIssue> issues
) {
}

package com.example.integrationsuiteagent.graph;

public record ValidationIssue(
        String severity,
        String path,
        String message
) {
}

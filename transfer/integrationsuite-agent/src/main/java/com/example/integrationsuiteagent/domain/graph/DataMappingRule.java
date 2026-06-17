package com.example.integrationsuiteagent.domain.graph;

public record DataMappingRule(
        String sourcePath,
        String targetPath,
        String expression,
        String note
) {
}

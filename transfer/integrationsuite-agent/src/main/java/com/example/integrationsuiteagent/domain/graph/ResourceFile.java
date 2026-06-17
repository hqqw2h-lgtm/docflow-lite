package com.example.integrationsuiteagent.domain.graph;

public record ResourceFile(
        String id,
        String name,
        String mediaType,
        String content
) {
}

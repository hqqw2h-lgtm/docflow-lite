package com.example.integrationsuiteagent.domain.session;

import java.time.Instant;

public record ToolCallTrace(
        String id,
        String sessionId,
        String toolName,
        String inputJson,
        String outputJson,
        TraceStatus status,
        String errorMessage,
        long durationMs,
        Instant createdAt
) {
}

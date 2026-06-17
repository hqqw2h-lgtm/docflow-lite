package com.example.integrationsuiteagent.domain.session;

import java.time.Instant;

public record GraphSnapshot(
        String id,
        String sessionId,
        String graphId,
        int version,
        String changeSummary,
        String graphJson,
        Instant createdAt
) {
}

package com.example.integrationsuiteagent.domain.session;

import java.time.Instant;

public record ConversationMessage(
        String id,
        String sessionId,
        MessageRole role,
        String content,
        Instant createdAt
) {
}

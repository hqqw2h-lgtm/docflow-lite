package com.example.integrationsuiteagent.agent;

import java.util.List;

public record AgentResponse(
        String sessionId,
        String message,
        List<String> suggestedNextTools
) {
}

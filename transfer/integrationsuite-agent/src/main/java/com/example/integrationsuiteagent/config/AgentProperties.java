package com.example.integrationsuiteagent.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "integrationsuite-agent")
public record AgentProperties(
        int maxAutoFixAttempts,
        String defaultModelProvider,
        String systemPrompt
) {
}

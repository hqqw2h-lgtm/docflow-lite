package com.example.integrationsuiteagent.api.dto;

import com.example.integrationsuiteagent.domain.session.ConversationMessage;
import com.example.integrationsuiteagent.domain.session.GraphSnapshot;
import com.example.integrationsuiteagent.domain.session.RequirementSession;
import com.example.integrationsuiteagent.domain.session.ToolCallTrace;

import java.util.List;

public record SessionDetailResponse(
        RequirementSession session,
        List<ConversationMessage> messages,
        List<ToolCallTrace> toolCalls,
        List<GraphSnapshot> graphSnapshots
) {
}

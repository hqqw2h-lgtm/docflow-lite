package com.example.integrationsuiteagent.repository;

import com.example.integrationsuiteagent.domain.session.ConversationMessage;
import com.example.integrationsuiteagent.domain.session.GraphSnapshot;
import com.example.integrationsuiteagent.domain.session.RequirementSession;
import com.example.integrationsuiteagent.domain.session.ToolCallTrace;

import java.util.List;
import java.util.Optional;

public interface SessionRepository {

    RequirementSession saveSession(RequirementSession session);

    Optional<RequirementSession> findSession(String sessionId);

    List<RequirementSession> findSessions();

    ConversationMessage addMessage(ConversationMessage message);

    List<ConversationMessage> findMessages(String sessionId);

    ToolCallTrace addToolTrace(ToolCallTrace trace);

    List<ToolCallTrace> findToolTraces(String sessionId);

    GraphSnapshot addGraphSnapshot(GraphSnapshot snapshot);

    List<GraphSnapshot> findGraphSnapshots(String sessionId);
}

package com.example.integrationsuiteagent.repository;

import com.example.integrationsuiteagent.domain.session.ConversationMessage;
import com.example.integrationsuiteagent.domain.session.GraphSnapshot;
import com.example.integrationsuiteagent.domain.session.RequirementSession;
import com.example.integrationsuiteagent.domain.session.ToolCallTrace;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Repository
public class InMemorySessionRepository implements SessionRepository {

    private final ConcurrentHashMap<String, RequirementSession> sessions = new ConcurrentHashMap<>();
    private final CopyOnWriteArrayList<ConversationMessage> messages = new CopyOnWriteArrayList<>();
    private final CopyOnWriteArrayList<ToolCallTrace> toolTraces = new CopyOnWriteArrayList<>();
    private final CopyOnWriteArrayList<GraphSnapshot> graphSnapshots = new CopyOnWriteArrayList<>();

    @Override
    public RequirementSession saveSession(RequirementSession session) {
        sessions.put(session.getId(), session);
        return session;
    }

    @Override
    public Optional<RequirementSession> findSession(String sessionId) {
        return Optional.ofNullable(sessions.get(sessionId));
    }

    @Override
    public List<RequirementSession> findSessions() {
        return new ArrayList<>(sessions.values()).stream()
                .sorted(Comparator.comparing(RequirementSession::getCreatedAt).reversed())
                .toList();
    }

    @Override
    public ConversationMessage addMessage(ConversationMessage message) {
        messages.add(message);
        return message;
    }

    @Override
    public List<ConversationMessage> findMessages(String sessionId) {
        return messages.stream()
                .filter(message -> sessionId.equals(message.sessionId()))
                .sorted(Comparator.comparing(ConversationMessage::createdAt))
                .toList();
    }

    @Override
    public ToolCallTrace addToolTrace(ToolCallTrace trace) {
        toolTraces.add(trace);
        return trace;
    }

    @Override
    public List<ToolCallTrace> findToolTraces(String sessionId) {
        return toolTraces.stream()
                .filter(trace -> sessionId.equals(trace.sessionId()))
                .sorted(Comparator.comparing(ToolCallTrace::createdAt))
                .toList();
    }

    @Override
    public GraphSnapshot addGraphSnapshot(GraphSnapshot snapshot) {
        graphSnapshots.add(snapshot);
        return snapshot;
    }

    @Override
    public List<GraphSnapshot> findGraphSnapshots(String sessionId) {
        return graphSnapshots.stream()
                .filter(snapshot -> sessionId.equals(snapshot.sessionId()))
                .sorted(Comparator.comparing(GraphSnapshot::createdAt))
                .toList();
    }
}

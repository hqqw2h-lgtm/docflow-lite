package com.example.integrationsuiteagent.session;

import com.example.integrationsuiteagent.api.dto.CreateRequirementRequest;
import com.example.integrationsuiteagent.api.dto.SessionDetailResponse;
import com.example.integrationsuiteagent.domain.session.ConversationMessage;
import com.example.integrationsuiteagent.domain.session.MessageRole;
import com.example.integrationsuiteagent.domain.session.RequirementSession;
import com.example.integrationsuiteagent.domain.session.TraceStatus;
import com.example.integrationsuiteagent.domain.session.ToolCallTrace;
import com.example.integrationsuiteagent.repository.SessionRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.function.Supplier;

@Service
public class RequirementSessionService {

    private final SessionRepository sessionRepository;
    private final ObjectMapper objectMapper;

    public RequirementSessionService(SessionRepository sessionRepository, ObjectMapper objectMapper) {
        this.sessionRepository = sessionRepository;
        this.objectMapper = objectMapper;
    }

    public RequirementSession createSession(CreateRequirementRequest request) {
        RequirementSession session = new RequirementSession(
                newId("req"),
                request.title(),
                request.userId(),
                request.targetEnvironment()
        );
        sessionRepository.saveSession(session);
        if (request.initialMessage() != null && !request.initialMessage().isBlank()) {
            addMessage(session.getId(), MessageRole.USER, request.initialMessage());
        }
        return session;
    }

    public RequirementSession getSession(String sessionId) {
        return sessionRepository.findSession(sessionId)
                .orElseThrow(() -> new IllegalArgumentException("Requirement session not found: " + sessionId));
    }

    public List<RequirementSession> listSessions() {
        return sessionRepository.findSessions();
    }

    public ConversationMessage addMessage(String sessionId, MessageRole role, String content) {
        getSession(sessionId);
        return sessionRepository.addMessage(new ConversationMessage(newId("msg"), sessionId, role, content, Instant.now()));
    }

    public SessionDetailResponse getSessionDetail(String sessionId) {
        RequirementSession session = getSession(sessionId);
        return new SessionDetailResponse(
                session,
                sessionRepository.findMessages(sessionId),
                sessionRepository.findToolTraces(sessionId),
                sessionRepository.findGraphSnapshots(sessionId)
        );
    }

    public <T> T traceToolCall(String sessionId, String toolName, Object input, Supplier<T> action) {
        long started = System.currentTimeMillis();
        try {
            T result = action.get();
            sessionRepository.addToolTrace(new ToolCallTrace(
                    newId("tool"),
                    sessionId,
                    toolName,
                    toJson(input),
                    toJson(result),
                    TraceStatus.SUCCESS,
                    null,
                    System.currentTimeMillis() - started,
                    Instant.now()
            ));
            return result;
        } catch (RuntimeException exception) {
            sessionRepository.addToolTrace(new ToolCallTrace(
                    newId("tool"),
                    sessionId,
                    toolName,
                    toJson(input),
                    null,
                    TraceStatus.FAILURE,
                    exception.getMessage(),
                    System.currentTimeMillis() - started,
                    Instant.now()
            ));
            throw exception;
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException e) {
            return String.valueOf(value);
        }
    }

    private String newId(String prefix) {
        return prefix + "_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
    }
}

package com.example.integrationsuiteagent.api;

import com.example.integrationsuiteagent.agent.AgentResponse;
import com.example.integrationsuiteagent.agent.IflowAgentService;
import com.example.integrationsuiteagent.api.dto.CreateRequirementRequest;
import com.example.integrationsuiteagent.api.dto.SendMessageRequest;
import com.example.integrationsuiteagent.api.dto.SessionDetailResponse;
import com.example.integrationsuiteagent.domain.session.RequirementSession;
import com.example.integrationsuiteagent.session.RequirementSessionService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/requirements")
public class RequirementController {

    private final RequirementSessionService sessionService;
    private final IflowAgentService agentService;

    public RequirementController(RequirementSessionService sessionService, IflowAgentService agentService) {
        this.sessionService = sessionService;
        this.agentService = agentService;
    }

    @PostMapping
    public RequirementSession createRequirement(@Valid @RequestBody CreateRequirementRequest request) {
        return sessionService.createSession(request);
    }

    @GetMapping
    public List<RequirementSession> listRequirements() {
        return sessionService.listSessions();
    }

    @GetMapping("/{sessionId}")
    public SessionDetailResponse getRequirement(@PathVariable String sessionId) {
        return sessionService.getSessionDetail(sessionId);
    }

    @PostMapping("/{sessionId}/messages")
    public AgentResponse sendMessage(@PathVariable String sessionId, @Valid @RequestBody SendMessageRequest request) {
        return agentService.handleUserMessage(sessionId, request.content());
    }
}

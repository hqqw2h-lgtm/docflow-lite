package com.example.integrationsuiteagent.agent;

import com.example.integrationsuiteagent.config.AgentProperties;
import com.example.integrationsuiteagent.domain.session.MessageRole;
import com.example.integrationsuiteagent.session.RequirementSessionService;
import com.example.integrationsuiteagent.tool.KnowledgeTools;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class IflowAgentService {

    private final AgentProperties agentProperties;
    private final RequirementSessionService sessionService;
    private final KnowledgeTools knowledgeTools;

    public IflowAgentService(
            AgentProperties agentProperties,
            RequirementSessionService sessionService,
            KnowledgeTools knowledgeTools
    ) {
        this.agentProperties = agentProperties;
        this.sessionService = sessionService;
        this.knowledgeTools = knowledgeTools;
    }

    public AgentResponse handleUserMessage(String sessionId, String content) {
        sessionService.addMessage(sessionId, MessageRole.USER, content);
        List<KnowledgeTools.KnowledgeHit> knowledge = sessionService.traceToolCall(
                sessionId,
                "retrieveKnowledge",
                content,
                () -> knowledgeTools.retrieveKnowledge(content)
        );
        String message = "我已经记录需求，并检索了相关规则/技能/样本。下一步应先查询 OData/Communication 信息，再用 addNode/addEdge 构建 Graph JSON DSL。"
                + " 当前 system prompt 已加载 " + agentProperties.defaultModelProvider() + " provider 配置。"
                + " 命中知识条目数: " + knowledge.size();
        sessionService.addMessage(sessionId, MessageRole.ASSISTANT, message);
        return new AgentResponse(sessionId, message, List.of(
                "getODataMetadata",
                "getInboundServiceUrl",
                "createGraph",
                "addNode",
                "addEdge",
                "validateGraph"
        ));
    }
}

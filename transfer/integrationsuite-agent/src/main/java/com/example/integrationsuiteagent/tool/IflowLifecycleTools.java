package com.example.integrationsuiteagent.tool;

import com.example.integrationsuiteagent.lifecycle.IflowLifecycleService;
import dev.langchain4j.agent.tool.Tool;
import org.springframework.stereotype.Component;

@Component
public class IflowLifecycleTools {

    private final IflowLifecycleService lifecycleService;

    public IflowLifecycleTools(IflowLifecycleService lifecycleService) {
        this.lifecycleService = lifecycleService;
    }

    @Tool("Compile iFlow graph JSON DSL into a deployable iFlow ZIP artifact")
    public IflowLifecycleService.CompileResult compileIflow(String graphId) {
        return lifecycleService.compile(graphId);
    }

    @Tool("Upload and deploy compiled iFlow artifact to SAP Integration Suite")
    public IflowLifecycleService.DeployResult uploadAndDeployIflow(String graphId, String tenantId) {
        return lifecycleService.uploadAndDeploy(graphId, tenantId);
    }

    @Tool("Run a smoke test against the deployed iFlow endpoint")
    public IflowLifecycleService.SmokeTestResult runSmokeTest(String graphId, String payload) {
        return lifecycleService.runSmokeTest(graphId, payload);
    }
}

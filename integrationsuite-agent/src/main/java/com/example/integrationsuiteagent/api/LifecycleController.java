package com.example.integrationsuiteagent.api;

import com.example.integrationsuiteagent.lifecycle.IflowLifecycleService;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/lifecycle")
public class LifecycleController {

    private final IflowLifecycleService lifecycleService;

    public LifecycleController(IflowLifecycleService lifecycleService) {
        this.lifecycleService = lifecycleService;
    }

    @PostMapping("/graphs/{graphId}/compile")
    public IflowLifecycleService.CompileResult compile(@PathVariable String graphId) {
        return lifecycleService.compile(graphId);
    }

    @PostMapping("/graphs/{graphId}/deploy/{tenantId}")
    public IflowLifecycleService.DeployResult deploy(@PathVariable String graphId, @PathVariable String tenantId) {
        return lifecycleService.uploadAndDeploy(graphId, tenantId);
    }

    @PostMapping("/graphs/{graphId}/smoke-test")
    public IflowLifecycleService.SmokeTestResult smokeTest(@PathVariable String graphId, @RequestBody String payload) {
        return lifecycleService.runSmokeTest(graphId, payload);
    }
}

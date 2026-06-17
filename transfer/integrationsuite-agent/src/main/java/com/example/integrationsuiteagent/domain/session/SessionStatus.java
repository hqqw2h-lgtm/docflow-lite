package com.example.integrationsuiteagent.domain.session;

public enum SessionStatus {
    OPEN,
    GRAPH_BUILDING,
    VALIDATED,
    COMPILED,
    DEPLOYED,
    TEST_PASSED,
    TEST_FAILED,
    BLOCKED
}

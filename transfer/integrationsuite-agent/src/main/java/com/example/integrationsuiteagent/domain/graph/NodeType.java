package com.example.integrationsuiteagent.domain.graph;

public enum NodeType {
    START_EVENT,
    END_EVENT,
    HTTP_SENDER,
    CONTENT_MODIFIER,
    REQUEST_REPLY,
    ODATA_RECEIVER,
    GROOVY_SCRIPT,
    MESSAGE_MAPPING,
    ROUTER,
    EXCEPTION_SUBPROCESS
}

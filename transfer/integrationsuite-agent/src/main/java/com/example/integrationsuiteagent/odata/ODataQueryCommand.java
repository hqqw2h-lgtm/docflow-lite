package com.example.integrationsuiteagent.odata;

import java.util.List;
import java.util.Map;

public record ODataQueryCommand(
        String systemId,
        String serviceName,
        String entitySet,
        List<String> select,
        List<String> expand,
        String filter,
        Integer top,
        Map<String, Object> key
) {
}

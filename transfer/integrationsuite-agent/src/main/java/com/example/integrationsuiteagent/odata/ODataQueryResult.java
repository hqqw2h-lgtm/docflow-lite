package com.example.integrationsuiteagent.odata;

import java.util.List;
import java.util.Map;

public record ODataQueryResult(
        String requestUrl,
        List<Map<String, Object>> records,
        String note
) {
}

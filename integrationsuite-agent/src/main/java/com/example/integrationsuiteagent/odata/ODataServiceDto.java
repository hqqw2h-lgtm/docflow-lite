package com.example.integrationsuiteagent.odata;

public record ODataServiceDto(
        String systemId,
        String serviceName,
        String version,
        String communicationScenario,
        String basePath
) {
}

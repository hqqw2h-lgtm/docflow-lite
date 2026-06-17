package com.example.integrationsuiteagent.odata;

import java.util.List;

public record ODataMetadataDto(
        String systemId,
        String serviceName,
        String version,
        List<String> entitySets,
        List<ODataEntityTypeDto> entityTypes
) {
}

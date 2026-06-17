package com.example.integrationsuiteagent.odata;

import java.util.List;

public record ODataEntityTypeDto(
        String serviceName,
        String entityName,
        List<String> keys,
        List<ODataPropertyDto> properties,
        List<ODataNavigationDto> navigationProperties
) {
}

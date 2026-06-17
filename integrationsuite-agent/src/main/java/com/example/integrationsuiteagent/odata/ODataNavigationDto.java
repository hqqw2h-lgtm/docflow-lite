package com.example.integrationsuiteagent.odata;

public record ODataNavigationDto(
        String name,
        String targetEntity,
        boolean collection
) {
}

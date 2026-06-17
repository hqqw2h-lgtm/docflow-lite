package com.example.integrationsuiteagent.odata;

public record ODataPropertyDto(
        String name,
        String type,
        boolean nullable,
        Integer maxLength
) {
}

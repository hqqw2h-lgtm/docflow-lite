package com.example.integrationsuiteagent.graph;

import com.example.integrationsuiteagent.domain.graph.DataMappingRule;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;

import java.util.List;

public record AddDataMappingsCommand(
        @NotBlank String graphId,
        @NotBlank String name,
        @NotEmpty List<DataMappingRule> rules
) {
}

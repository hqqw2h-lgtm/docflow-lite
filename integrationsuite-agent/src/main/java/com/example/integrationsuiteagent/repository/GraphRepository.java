package com.example.integrationsuiteagent.repository;

import com.example.integrationsuiteagent.domain.graph.IntegrationGraph;

import java.util.List;
import java.util.Optional;

public interface GraphRepository {

    IntegrationGraph save(IntegrationGraph graph);

    Optional<IntegrationGraph> findById(String id);

    List<IntegrationGraph> findBySessionId(String sessionId);
}

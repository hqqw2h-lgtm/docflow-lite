package com.example.integrationsuiteagent.repository;

import com.example.integrationsuiteagent.domain.graph.IntegrationGraph;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Repository
public class InMemoryGraphRepository implements GraphRepository {

    private final ConcurrentHashMap<String, IntegrationGraph> graphs = new ConcurrentHashMap<>();

    @Override
    public IntegrationGraph save(IntegrationGraph graph) {
        graphs.put(graph.getId(), graph);
        return graph;
    }

    @Override
    public Optional<IntegrationGraph> findById(String id) {
        return Optional.ofNullable(graphs.get(id));
    }

    @Override
    public List<IntegrationGraph> findBySessionId(String sessionId) {
        return graphs.values().stream()
                .filter(graph -> sessionId.equals(graph.getSessionId()))
                .toList();
    }
}

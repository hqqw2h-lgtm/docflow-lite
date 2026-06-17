package com.example.integrationsuiteagent.domain.graph;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class IntegrationGraph {

    private String id;
    private String sessionId;
    private String name;
    private String packageId;
    private int version;
    private List<GraphNode> nodes = new ArrayList<>();
    private List<GraphEdge> edges = new ArrayList<>();
    private GraphResources resources = new GraphResources();
    private Map<String, String> externalizedParameters = new LinkedHashMap<>();
    private Instant createdAt;
    private Instant updatedAt;

    public IntegrationGraph() {
    }

    public IntegrationGraph(String id, String sessionId, String name, String packageId) {
        this.id = id;
        this.sessionId = sessionId;
        this.name = name;
        this.packageId = packageId;
        this.version = 1;
        this.createdAt = Instant.now();
        this.updatedAt = createdAt;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getPackageId() {
        return packageId;
    }

    public void setPackageId(String packageId) {
        this.packageId = packageId;
    }

    public int getVersion() {
        return version;
    }

    public void setVersion(int version) {
        this.version = version;
    }

    public List<GraphNode> getNodes() {
        return nodes;
    }

    public void setNodes(List<GraphNode> nodes) {
        this.nodes = new ArrayList<>(nodes);
    }

    public List<GraphEdge> getEdges() {
        return edges;
    }

    public void setEdges(List<GraphEdge> edges) {
        this.edges = new ArrayList<>(edges);
    }

    public GraphResources getResources() {
        return resources;
    }

    public void setResources(GraphResources resources) {
        this.resources = resources;
    }

    public Map<String, String> getExternalizedParameters() {
        return externalizedParameters;
    }

    public void setExternalizedParameters(Map<String, String> externalizedParameters) {
        this.externalizedParameters = new LinkedHashMap<>(externalizedParameters);
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }

    public void touch() {
        version++;
        updatedAt = Instant.now();
    }
}

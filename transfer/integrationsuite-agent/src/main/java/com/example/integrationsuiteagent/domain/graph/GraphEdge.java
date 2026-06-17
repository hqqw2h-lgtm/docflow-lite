package com.example.integrationsuiteagent.domain.graph;

import java.util.LinkedHashMap;
import java.util.Map;

public class GraphEdge {

    private String id;
    private EdgeType type;
    private String source;
    private String target;
    private Map<String, Object> properties = new LinkedHashMap<>();

    public GraphEdge() {
    }

    public GraphEdge(String id, EdgeType type, String source, String target, Map<String, Object> properties) {
        this.id = id;
        this.type = type;
        this.source = source;
        this.target = target;
        this.properties = new LinkedHashMap<>(properties);
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public EdgeType getType() {
        return type;
    }

    public void setType(EdgeType type) {
        this.type = type;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    public String getTarget() {
        return target;
    }

    public void setTarget(String target) {
        this.target = target;
    }

    public Map<String, Object> getProperties() {
        return properties;
    }

    public void setProperties(Map<String, Object> properties) {
        this.properties = new LinkedHashMap<>(properties);
    }

    public void mergeProperties(Map<String, Object> newProperties) {
        properties.putAll(newProperties);
    }
}

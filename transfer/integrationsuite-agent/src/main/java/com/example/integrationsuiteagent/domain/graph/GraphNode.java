package com.example.integrationsuiteagent.domain.graph;

import java.util.LinkedHashMap;
import java.util.Map;

public class GraphNode {

    private String id;
    private NodeType type;
    private String label;
    private Position position;
    private Map<String, Object> properties = new LinkedHashMap<>();

    public GraphNode() {
    }

    public GraphNode(String id, NodeType type, String label, Position position, Map<String, Object> properties) {
        this.id = id;
        this.type = type;
        this.label = label;
        this.position = position;
        this.properties = new LinkedHashMap<>(properties);
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public NodeType getType() {
        return type;
    }

    public void setType(NodeType type) {
        this.type = type;
    }

    public String getLabel() {
        return label;
    }

    public void setLabel(String label) {
        this.label = label;
    }

    public Position getPosition() {
        return position;
    }

    public void setPosition(Position position) {
        this.position = position;
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

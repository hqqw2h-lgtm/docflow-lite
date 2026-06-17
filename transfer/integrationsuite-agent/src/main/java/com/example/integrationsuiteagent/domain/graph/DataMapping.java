package com.example.integrationsuiteagent.domain.graph;

import java.util.ArrayList;
import java.util.List;

public class DataMapping {

    private String id;
    private String name;
    private List<DataMappingRule> rules = new ArrayList<>();

    public DataMapping() {
    }

    public DataMapping(String id, String name, List<DataMappingRule> rules) {
        this.id = id;
        this.name = name;
        this.rules = new ArrayList<>(rules);
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public List<DataMappingRule> getRules() {
        return rules;
    }

    public void setRules(List<DataMappingRule> rules) {
        this.rules = new ArrayList<>(rules);
    }
}

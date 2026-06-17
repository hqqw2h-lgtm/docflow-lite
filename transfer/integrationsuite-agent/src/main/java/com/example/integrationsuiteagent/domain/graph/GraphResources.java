package com.example.integrationsuiteagent.domain.graph;

import java.util.ArrayList;
import java.util.List;

public class GraphResources {

    private List<DataMapping> mappings = new ArrayList<>();
    private List<ResourceFile> scripts = new ArrayList<>();
    private List<ResourceFile> schemas = new ArrayList<>();

    public List<DataMapping> getMappings() {
        return mappings;
    }

    public void setMappings(List<DataMapping> mappings) {
        this.mappings = new ArrayList<>(mappings);
    }

    public List<ResourceFile> getScripts() {
        return scripts;
    }

    public void setScripts(List<ResourceFile> scripts) {
        this.scripts = new ArrayList<>(scripts);
    }

    public List<ResourceFile> getSchemas() {
        return schemas;
    }

    public void setSchemas(List<ResourceFile> schemas) {
        this.schemas = new ArrayList<>(schemas);
    }
}

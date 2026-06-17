package com.example.integrationsuiteagent.domain.graph;

public record Position(int x, int y) {

    public static Position origin() {
        return new Position(0, 0);
    }
}

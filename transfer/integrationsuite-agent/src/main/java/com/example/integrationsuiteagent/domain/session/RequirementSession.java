package com.example.integrationsuiteagent.domain.session;

import java.time.Instant;

public class RequirementSession {

    private String id;
    private String title;
    private String userId;
    private String targetEnvironment;
    private SessionStatus status;
    private Instant createdAt;
    private Instant updatedAt;

    public RequirementSession() {
    }

    public RequirementSession(String id, String title, String userId, String targetEnvironment) {
        this.id = id;
        this.title = title;
        this.userId = userId;
        this.targetEnvironment = targetEnvironment;
        this.status = SessionStatus.OPEN;
        this.createdAt = Instant.now();
        this.updatedAt = createdAt;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getTargetEnvironment() {
        return targetEnvironment;
    }

    public void setTargetEnvironment(String targetEnvironment) {
        this.targetEnvironment = targetEnvironment;
    }

    public SessionStatus getStatus() {
        return status;
    }

    public void setStatus(SessionStatus status) {
        this.status = status;
        this.updatedAt = Instant.now();
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
}

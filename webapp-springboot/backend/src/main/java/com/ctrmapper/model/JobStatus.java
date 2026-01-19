package com.ctrmapper.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class JobStatus {
    @JsonProperty("job_id")
    private String jobId;

    private String status; // pending, processing, completed, failed

    @JsonProperty("created_at")
    private LocalDateTime createdAt;

    @JsonProperty("completed_at")
    private LocalDateTime completedAt;

    private Map<String, Object> result;
    private String error;
}

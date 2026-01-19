package com.ctrmapper.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProcessingResponse {
    private boolean success;
    private String message;

    @JsonProperty("job_id")
    private String jobId;
}

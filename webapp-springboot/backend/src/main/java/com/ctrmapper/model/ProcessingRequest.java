package com.ctrmapper.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProcessingRequest {
    @Builder.Default
    private int inputHeaderStart = 27;

    @Builder.Default
    private int inputDataStart = 28;

    @Builder.Default
    private int templateHeaderStart = 1;

    @Builder.Default
    private int templateDataStart = 2;
}

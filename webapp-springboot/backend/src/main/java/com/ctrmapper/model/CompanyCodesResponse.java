package com.ctrmapper.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CompanyCodesResponse {
    private boolean success;

    @JsonProperty("company_codes")
    private List<String> companyCodes;

    @JsonProperty("total_count")
    private int totalCount;
}

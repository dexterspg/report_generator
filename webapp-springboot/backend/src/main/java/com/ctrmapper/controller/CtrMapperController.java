package com.ctrmapper.controller;

import com.ctrmapper.model.*;
import com.ctrmapper.service.ExcelProcessorService;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequiredArgsConstructor
public class CtrMapperController {

    private final ExcelProcessorService processorService;

    @PostMapping("/upload")
    public ResponseEntity<ProcessingResponse> uploadFile(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "input_header_start", defaultValue = "27") int inputHeaderStart,
            @RequestParam(value = "input_data_start", defaultValue = "28") int inputDataStart,
            @RequestParam(value = "template_header_start", defaultValue = "1") int templateHeaderStart,
            @RequestParam(value = "template_data_start", defaultValue = "2") int templateDataStart,
            @RequestParam(value = "company_code", required = false) String companyCode) {

        // Validate file type
        String filename = file.getOriginalFilename();
        if (filename == null || (!filename.endsWith(".xlsx") && !filename.endsWith(".xls"))) {
            return ResponseEntity.badRequest().body(ProcessingResponse.builder()
                    .success(false)
                    .message("Only Excel files (.xlsx, .xls) are allowed")
                    .build());
        }

        String jobId = UUID.randomUUID().toString();

        try {
            // Clean up old files
            processorService.cleanupOldFiles();

            // Save uploaded file
            Path inputPath = processorService.getUploadDir().resolve(jobId + "_input_" + filename);
            Path outputPath = processorService.getUploadDir().resolve(jobId + "_output_poliza_ledger.xlsx");

            Files.copy(file.getInputStream(), inputPath);

            // Create job
            processorService.createJob(jobId);
            System.out.println("Created job: " + jobId);

            // Create processing request
            ProcessingRequest request = ProcessingRequest.builder()
                    .inputHeaderStart(inputHeaderStart)
                    .inputDataStart(inputDataStart)
                    .templateHeaderStart(templateHeaderStart)
                    .templateDataStart(templateDataStart)
                    .build();

            // Start async processing
            processorService.processFileAsync(jobId, inputPath.toString(), outputPath.toString(), request, companyCode);

            return ResponseEntity.ok(ProcessingResponse.builder()
                    .success(true)
                    .message("File uploaded successfully. Processing started.")
                    .jobId(jobId)
                    .build());

        } catch (IOException e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(ProcessingResponse.builder()
                            .success(false)
                            .message("Upload failed: " + e.getMessage())
                            .build());
        }
    }

    @GetMapping("/status/{jobId}")
    public ResponseEntity<JobStatus> getJobStatus(@PathVariable String jobId) {
        System.out.println("Status check for jobId: " + jobId);
        System.out.println("Available jobs: " + processorService.getAllJobs().keySet());

        JobStatus status = processorService.getJobStatus(jobId);

        if (status == null) {
            System.out.println("Job not found: " + jobId);
            return ResponseEntity.notFound().build();
        }

        System.out.println("Job status: " + status.getStatus());
        return ResponseEntity.ok(status);
    }

    @GetMapping("/download/{jobId}")
    public ResponseEntity<Resource> downloadResult(@PathVariable String jobId) {
        JobStatus status = processorService.getJobStatus(jobId);

        if (status == null) {
            return ResponseEntity.notFound().build();
        }

        if (!"completed".equals(status.getStatus())) {
            return ResponseEntity.badRequest().build();
        }

        Path outputPath = processorService.getUploadDir().resolve(jobId + "_output_poliza_ledger.xlsx");

        if (!Files.exists(outputPath)) {
            return ResponseEntity.notFound().build();
        }

        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String downloadFilename = "poliza_ledger_" + timestamp + ".xlsx";

        Resource resource = new FileSystemResource(outputPath);

        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + downloadFilename + "\"")
                .body(resource);
    }

    @PostMapping("/extract-company-codes")
    public ResponseEntity<CompanyCodesResponse> extractCompanyCodes(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "input_header_start", defaultValue = "27") int inputHeaderStart) {

        // Validate file type
        String filename = file.getOriginalFilename();
        if (filename == null || (!filename.endsWith(".xlsx") && !filename.endsWith(".xls"))) {
            return ResponseEntity.badRequest().body(CompanyCodesResponse.builder()
                    .success(false)
                    .build());
        }

        try {
            // Save temp file
            String tempId = UUID.randomUUID().toString();
            Path tempPath = processorService.getUploadDir().resolve(tempId + "_temp_" + filename);
            Files.copy(file.getInputStream(), tempPath);

            // Extract company codes
            List<String> companyCodes = processorService.extractCompanyCodes(tempPath.toString(), inputHeaderStart);

            // Clean up temp file
            Files.deleteIfExists(tempPath);

            return ResponseEntity.ok(CompanyCodesResponse.builder()
                    .success(true)
                    .companyCodes(companyCodes)
                    .totalCount(companyCodes.size())
                    .build());

        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(CompanyCodesResponse.builder()
                            .success(false)
                            .build());
        }
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> healthCheck() {
        Map<String, Object> health = new HashMap<>();
        health.put("status", "healthy");
        health.put("timestamp", LocalDateTime.now().toString());
        health.put("active_jobs", processorService.getAllJobs().values().stream()
                .filter(j -> "pending".equals(j.getStatus()) || "processing".equals(j.getStatus()))
                .count());
        health.put("mode", "web");
        health.put("framework", "Spring Boot");

        return ResponseEntity.ok(health);
    }

    @DeleteMapping("/cleanup")
    public ResponseEntity<Map<String, String>> cleanup() {
        try {
            int jobsBefore = processorService.getAllJobs().size();
            processorService.cleanupOldFiles();
            int jobsAfter = processorService.getAllJobs().size();

            Map<String, String> response = new HashMap<>();
            response.put("message", "Cleanup completed. Removed " + (jobsBefore - jobsAfter) + " old jobs.");

            return ResponseEntity.ok(response);
        } catch (Exception e) {
            Map<String, String> error = new HashMap<>();
            error.put("message", "Cleanup failed: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
        }
    }
}

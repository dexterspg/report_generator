# CTR Mapper Spring Boot - Controllers & REST API

## REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /upload | Upload and process Excel file |
| GET | /status/{jobId} | Get processing job status |
| GET | /download/{jobId} | Download processed file |
| POST | /extract-company-codes | Extract company codes from Excel |
| GET | /health | Health check |
| DELETE | /cleanup | Clean up old files |

---

## 1. CtrMapperController.java (Main REST API)

```java
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

    /**
     * Upload and process Excel file
     *
     * @param file The Excel file to process
     * @param inputHeaderStart Row number where headers start (1-indexed, default 27)
     * @param inputDataStart Row number where data starts (1-indexed, default 28)
     * @param companyCode Optional filter by company code
     */
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

            // Create job tracking entry
            processorService.createJob(jobId);
            System.out.println("Created job: " + jobId);

            // Create processing request
            ProcessingRequest request = ProcessingRequest.builder()
                    .inputHeaderStart(inputHeaderStart)
                    .inputDataStart(inputDataStart)
                    .templateHeaderStart(templateHeaderStart)
                    .templateDataStart(templateDataStart)
                    .build();

            // Start async processing (non-blocking)
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

    /**
     * Get job processing status
     * Frontend polls this endpoint to check if processing is complete
     */
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

    /**
     * Download processed Excel file
     */
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

    /**
     * Extract unique company codes from Excel file
     */
    @PostMapping("/extract-company-codes")
    public ResponseEntity<CompanyCodesResponse> extractCompanyCodes(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "input_header_start", defaultValue = "27") int inputHeaderStart) {

        String filename = file.getOriginalFilename();
        if (filename == null || (!filename.endsWith(".xlsx") && !filename.endsWith(".xls"))) {
            return ResponseEntity.badRequest().body(CompanyCodesResponse.builder()
                    .success(false)
                    .build());
        }

        try {
            String tempId = UUID.randomUUID().toString();
            Path tempPath = processorService.getUploadDir().resolve(tempId + "_temp_" + filename);
            Files.copy(file.getInputStream(), tempPath);

            List<String> companyCodes = processorService.extractCompanyCodes(tempPath.toString(), inputHeaderStart);

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

    /**
     * Health check endpoint
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> healthCheck() {
        Map<String, Object> health = new HashMap<>();
        health.put("status", "healthy");
        health.put("timestamp", LocalDateTime.now().toString());
        health.put("active_jobs", processorService.getAllJobs().values().stream()
                .filter(j -> "pending".equals(j.getStatus()) || "processing".equals(j.getStatus()))
                .count());
        health.put("framework", "Spring Boot");

        return ResponseEntity.ok(health);
    }

    /**
     * Manual cleanup of old files and jobs
     */
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
```

---

## 2. FrontendController.java (Serves Vue.js Frontend)

```java
package com.ctrmapper.controller;

import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@Controller
public class FrontendController {

    /**
     * Serve the Vue.js frontend index.html
     * This allows the SPA (Single Page Application) to work
     */
    @GetMapping("/")
    public ResponseEntity<Resource> serveIndex() {
        // Try to serve from frontend-dist directory
        Path frontendPath = Paths.get("../frontend-dist/index.html");

        if (Files.exists(frontendPath)) {
            return ResponseEntity.ok()
                    .contentType(MediaType.TEXT_HTML)
                    .body(new FileSystemResource(frontendPath));
        }

        // Try alternative path
        Path altPath = Paths.get("frontend-dist/index.html");
        if (Files.exists(altPath)) {
            return ResponseEntity.ok()
                    .contentType(MediaType.TEXT_HTML)
                    .body(new FileSystemResource(altPath));
        }

        return ResponseEntity.notFound().build();
    }
}
```

---

## Key Concepts Demonstrated

1. **@RestController** - Combines @Controller + @ResponseBody (returns JSON)
2. **@Controller** - For serving HTML views
3. **@RequiredArgsConstructor** - Lombok generates constructor for final fields (dependency injection)
4. **@PostMapping, @GetMapping, @DeleteMapping** - HTTP method mappings
5. **@RequestParam** - Extract query/form parameters
6. **@PathVariable** - Extract URL path variables
7. **MultipartFile** - Handle file uploads
8. **ResponseEntity** - Full control over HTTP response (status, headers, body)
9. **UUID.randomUUID()** - Generate unique job IDs
10. **Async processing** - Non-blocking file processing with status polling

---

## Request/Response Flow

```
1. Frontend sends POST /upload with file
   ↓
2. Controller saves file, creates job, starts async processing
   ↓
3. Controller returns { success: true, job_id: "abc-123" }
   ↓
4. Frontend polls GET /status/abc-123 every second
   ↓
5. When status = "completed", frontend calls GET /download/abc-123
   ↓
6. User downloads the processed Excel file
```

---

## Comparison: Python FastAPI vs Spring Boot

| Feature | FastAPI (Python) | Spring Boot (Java) |
|---------|------------------|-------------------|
| Route definition | `@app.post("/upload")` | `@PostMapping("/upload")` |
| Async | `async def` | `@Async` annotation |
| File upload | `UploadFile` | `MultipartFile` |
| Response | `return ProcessingResponse(...)` | `return ResponseEntity.ok(...)` |
| JSON naming | Automatic snake_case | Needs `@JsonProperty` |
| Dependency injection | Function parameters | Constructor injection |

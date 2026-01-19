# CTR Mapper - Python FastAPI vs Java Spring Boot Comparison

## Overview

This guide compares the Python/FastAPI implementation with the Java/Spring Boot implementation, highlighting key differences and lessons learned during the migration.

---

## 1. Project Structure Comparison

### Python/FastAPI
```
webapp/
├── backend/
│   ├── app.py              # Single entry point + routes
│   ├── models/schemas.py   # Pydantic models
│   └── requirements.txt    # pip dependencies
└── frontend-vue/
```

### Java/Spring Boot
```
webapp-springboot/
├── backend/
│   ├── pom.xml                           # Maven dependencies
│   ├── src/main/resources/
│   │   └── application.properties        # Configuration
│   └── src/main/java/com/ctrmapper/
│       ├── CtrMapperApplication.java     # Entry point
│       ├── config/                       # Configuration classes
│       ├── controller/                   # REST endpoints
│       ├── model/                        # DTOs
│       └── service/                      # Business logic
└── frontend-vue/
```

**Key Difference:** Spring Boot separates concerns into packages (controller, service, model, config) while Python/FastAPI typically uses fewer files.

---

## 2. Dependency Management

### Python (requirements.txt)
```
fastapi>=0.104.0
uvicorn>=0.24.0
pandas>=2.1.0
openpyxl>=3.1.0
```

### Java (pom.xml)
```xml
<dependencies>
    <!-- Spring Boot Web -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- Apache POI for Excel -->
    <dependency>
        <groupId>org.apache.poi</groupId>
        <artifactId>poi-ooxml</artifactId>
        <version>5.2.5</version>
    </dependency>

    <!-- Streaming Excel reader -->
    <dependency>
        <groupId>com.github.pjfanning</groupId>
        <artifactId>excel-streaming-reader</artifactId>
        <version>4.3.0</version>
    </dependency>

    <!-- Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
    </dependency>
</dependencies>
```

---

## 3. Route/Endpoint Definition

### Python FastAPI
```python
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    input_header_start: int = Form(27),
    input_data_start: int = Form(28),
    company_code: Optional[str] = Form(None)
):
    # Automatic request parsing
    # Automatic OpenAPI docs generation
    return ProcessingResponse(success=True, job_id=job_id)
```

### Java Spring Boot
```java
@PostMapping("/upload")
public ResponseEntity<ProcessingResponse> uploadFile(
        @RequestParam("file") MultipartFile file,
        @RequestParam(value = "input_header_start", defaultValue = "27") int inputHeaderStart,
        @RequestParam(value = "input_data_start", defaultValue = "28") int inputDataStart,
        @RequestParam(value = "company_code", required = false) String companyCode) {

    // Manual file handling
    // ResponseEntity for full HTTP control
    return ResponseEntity.ok(ProcessingResponse.builder()
            .success(true)
            .jobId(jobId)
            .build());
}
```

---

## 4. Model/DTO Definition

### Python (Pydantic)
```python
from pydantic import BaseModel
from typing import Optional

class ProcessingResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    job_id: Optional[str] = None  # Automatic snake_case in JSON
```

### Java (Lombok + Jackson)
```java
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.*;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProcessingResponse {
    private boolean success;
    private String message;

    @JsonProperty("job_id")  // REQUIRED for snake_case output
    private String jobId;
}
```

**Critical Difference:** Python automatically uses snake_case in JSON. Java defaults to camelCase and needs `@JsonProperty` annotations.

---

## 5. Async Processing

### Python FastAPI
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

@app.post("/upload")
async def upload_file(...):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending"}

    # Run in background thread pool
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, process_file_sync, job_id, input_path)

    return {"success": True, "job_id": job_id}
```

### Java Spring Boot
```java
// AsyncConfig.java
@Configuration
@EnableAsync
public class AsyncConfig {
    @Bean(name = "taskExecutor")
    public Executor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(2);
        executor.setMaxPoolSize(5);
        executor.setQueueCapacity(100);
        executor.initialize();
        return executor;
    }
}

// Service
@Async("taskExecutor")
public void processFileAsync(String jobId, String inputPath, ...) {
    // Runs in background thread
}
```

---

## 6. Excel Processing - Memory Issue

### Problem
Large Excel file (~149MB) caused `OutOfMemoryError` in Java but worked fine in Python.

### Why Python Works
Pandas reads Excel files efficiently by default, using streaming internally.

```python
import pandas as pd
df = pd.read_excel(input_file, header=26)  # Just works
```

### Java Solution - Streaming APIs

**Reading (StreamingReader):**
```java
import com.github.pjfanning.xlsx.StreamingReader;

Workbook inputWorkbook = StreamingReader.builder()
        .rowCacheSize(100)      // Keep 100 rows in memory
        .bufferSize(4096)       // Buffer size in bytes
        .open(inputStream);

for (Row row : sheet) {
    // Process one row at a time
}
```

**Writing (SXSSFWorkbook):**
```java
import org.apache.poi.xssf.streaming.SXSSFWorkbook;

SXSSFWorkbook outputWorkbook = new SXSSFWorkbook(100);  // Window of 100 rows
// Rows outside window are flushed to disk
```

---

## 7. Row Indexing Bug

### Problem
Headers were read incorrectly - data values appeared instead of column names.

### Root Cause
Manual row counting vs actual Excel row numbers.

```java
// WRONG - Manual counting
int rowIndex = 0;
for (Row row : sheet) {
    if (rowIndex == headerRowNum) {  // rowIndex doesn't match Excel row
        // Read headers
    }
    rowIndex++;
}

// CORRECT - Use actual row number
for (Row row : sheet) {
    int currentRowNum = row.getRowNum();  // 0-indexed Excel row number
    if (currentRowNum == headerRowNum) {
        // Read headers
    }
}
```

**Lesson:** StreamingReader may skip empty rows, so never assume sequential iteration matches row numbers.

---

## 8. JSON Field Naming Issue

### Problem
Frontend got 404 error. Console showed: `Status check for jobId: undefined`

### Root Cause
- Frontend expected: `response.data.job_id` (snake_case, matching Python API)
- Java returned: `{ "jobId": "..." }` (camelCase)

### Solution
Add Jackson annotations to Java models:

```java
public class ProcessingResponse {
    @JsonProperty("job_id")
    private String jobId;
}

public class JobStatus {
    @JsonProperty("job_id")
    private String jobId;

    @JsonProperty("created_at")
    private LocalDateTime createdAt;

    @JsonProperty("completed_at")
    private LocalDateTime completedAt;
}
```

---

## 9. Feature Comparison Table

| Feature | Python/FastAPI | Java/Spring Boot |
|---------|----------------|------------------|
| **File Upload** | `UploadFile` | `MultipartFile` |
| **JSON Response** | Automatic snake_case | Needs `@JsonProperty` |
| **Async** | `async/await` + executor | `@Async` annotation |
| **DI** | Function parameters | Constructor injection |
| **Excel Read** | pandas (efficient) | POI + StreamingReader |
| **Excel Write** | openpyxl | POI SXSSFWorkbook |
| **Config** | Environment vars | application.properties |
| **Build** | pip install | Maven (mvn package) |
| **Run** | `uvicorn app:app` | `java -jar app.jar` |
| **Hot Reload** | Yes (--reload) | Spring DevTools |
| **Memory** | ~200MB | ~500MB+ (JVM overhead) |

---

## 10. Running Both Applications

### Python Version (Port 8000)
```bash
cd webapp/backend
pip install -r requirements.txt
python app.py
# Runs on http://localhost:8000
```

### Spring Boot Version (Port 8080)
```bash
cd webapp-springboot/backend
mvn clean package -DskipTests
java -jar target/ctr-mapper-1.0.0.jar
# Runs on http://localhost:8080
```

### Frontend (Development)
```bash
# For Python backend (port 3000 → 8000)
cd webapp/frontend-vue
npm run dev

# For Spring Boot backend (port 3001 → 8080)
cd webapp-springboot/frontend-vue
npm run dev
```

---

## 11. Lessons Learned

1. **JSON Naming Matters** - Always check API response format matches frontend expectations. Use `@JsonProperty` for snake_case.

2. **Memory Management** - Java needs explicit streaming for large files. Python/pandas handles this automatically.

3. **Row Indexing** - Use `row.getRowNum()` not manual counters when rows may be skipped.

4. **POI Size Limits** - Increase `IOUtils.setByteArrayMaxOverride()` for large files.

5. **Streaming vs Loading** - For 100MB+ files:
   - Read: `StreamingReader` (not `XSSFWorkbook`)
   - Write: `SXSSFWorkbook` (not `XSSFWorkbook`)

6. **Lombok Reduces Boilerplate** - `@Data`, `@Builder`, `@RequiredArgsConstructor` eliminate getters/setters.

7. **Spring Boot Structure** - Separation into controller/service/model layers makes code maintainable.

8. **Proxy Configuration** - Vite proxy makes development seamless between frontend and backend.

---

## 12. Quick Reference Commands

```bash
# Build Spring Boot JAR
mvn clean package -DskipTests

# Run with increased heap
java -Xmx2g -jar target/ctr-mapper-1.0.0.jar

# Build Vue frontend
npm run build

# Development mode
npm run dev
```

---

## Summary

The migration from Python/FastAPI to Java/Spring Boot required:
1. More boilerplate code (solved with Lombok)
2. Explicit JSON naming (solved with `@JsonProperty`)
3. Streaming APIs for large files (solved with excel-streaming-reader + SXSSFWorkbook)
4. Careful row indexing (solved with `getRowNum()`)

Both implementations achieve the same result but with different trade-offs in verbosity, memory management, and configuration.

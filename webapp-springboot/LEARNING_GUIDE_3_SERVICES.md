# CTR Mapper Spring Boot - Service Layer (Excel Processing)

## Overview

The service layer contains the business logic for:
1. Excel file processing (reading, transforming, writing)
2. Job status management
3. Formula calculations

---

## 1. ExcelProcessorService.java (Main Processing Logic)

```java
package com.ctrmapper.service;

import com.ctrmapper.model.JobStatus;
import com.ctrmapper.model.ProcessingRequest;
import com.github.pjfanning.xlsx.StreamingReader;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.apache.poi.xssf.streaming.SXSSFWorkbook;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Service
public class ExcelProcessorService {

    // Thread-safe map to store job status (in production, use Redis/database)
    private final Map<String, JobStatus> jobs = new ConcurrentHashMap<>();
    private final Path uploadDir;

    public ExcelProcessorService() {
        this.uploadDir = Paths.get("uploads");
        try {
            Files.createDirectories(uploadDir);
        } catch (IOException e) {
            throw new RuntimeException("Could not create upload directory", e);
        }
    }

    public Path getUploadDir() {
        return uploadDir;
    }

    public JobStatus getJobStatus(String jobId) {
        return jobs.get(jobId);
    }

    public void createJob(String jobId) {
        jobs.put(jobId, JobStatus.builder()
                .jobId(jobId)
                .status("pending")
                .createdAt(LocalDateTime.now())
                .build());
    }

    public Map<String, JobStatus> getAllJobs() {
        return jobs;
    }

    /**
     * Process file asynchronously in background thread
     * The @Async annotation makes this method non-blocking
     */
    @Async("taskExecutor")
    public void processFileAsync(String jobId, String inputPath, String outputPath,
                                  ProcessingRequest request, String companyCode) {
        try {
            jobs.get(jobId).setStatus("processing");

            long startTime = System.currentTimeMillis();
            Map<String, Object> result = processFile(inputPath, outputPath, request, companyCode);
            long endTime = System.currentTimeMillis();

            JobStatus job = jobs.get(jobId);
            job.setCompletedAt(LocalDateTime.now());
            job.setResult(result);
            result.put("processing_time", (endTime - startTime) / 1000.0);

            if ((Boolean) result.get("success")) {
                job.setStatus("completed");
            } else {
                job.setStatus("failed");
                job.setError((String) result.get("error"));
            }

        } catch (Exception e) {
            JobStatus job = jobs.get(jobId);
            job.setStatus("failed");
            job.setError(e.getMessage());
            job.setCompletedAt(LocalDateTime.now());
            e.printStackTrace();
        }
    }

    /**
     * Main file processing logic
     * Uses streaming for memory efficiency (like Python pandas)
     */
    public Map<String, Object> processFile(String inputPath, String outputPath,
                                            ProcessingRequest request, String companyCode) {
        Map<String, Object> result = new HashMap<>();

        // StreamingReader: Memory-efficient reading (like pandas)
        // Only keeps 100 rows in memory at a time
        try (FileInputStream fis = new FileInputStream(inputPath);
             Workbook inputWorkbook = StreamingReader.builder()
                     .rowCacheSize(100)      // Number of rows to keep in memory
                     .bufferSize(4096)       // Buffer size for reading
                     .open(fis)) {

            Sheet inputSheet = inputWorkbook.getSheetAt(0);

            // Read headers and data in single pass (streaming requirement)
            Map<String, Integer> headerMap = new LinkedHashMap<>();
            List<Map<String, Object>> allData = new ArrayList<>();

            // Convert 1-indexed (user input) to 0-indexed (POI)
            int headerRowNum = request.getInputHeaderStart() - 1;
            int dataStartRowNum = request.getInputDataStart() - 1;

            System.out.println("Looking for header at row " + request.getInputHeaderStart());

            for (Row row : inputSheet) {
                int currentRowNum = row.getRowNum(); // 0-indexed Excel row number

                // Skip rows before header
                if (currentRowNum < headerRowNum) {
                    continue;
                }

                // Read header row
                if (currentRowNum == headerRowNum) {
                    for (Cell cell : row) {
                        String headerName = getCellValueAsString(cell);
                        if (headerName != null && !headerName.isEmpty()) {
                            headerMap.put(headerName, cell.getColumnIndex());
                        }
                    }
                    System.out.println("Found headers: " + headerMap.keySet());

                    // Validate required columns
                    List<String> requiredColumns = Arrays.asList(
                            "Translation Type", "Fiscal Year", "Fiscal Period", "Unit",
                            "Contract Name", "Vendor", "GL Account", "Contract Currency",
                            "Amount in Contract Currency"
                    );

                    List<String> missingColumns = requiredColumns.stream()
                            .filter(col -> !headerMap.containsKey(col))
                            .collect(Collectors.toList());

                    if (!missingColumns.isEmpty()) {
                        throw new IllegalArgumentException("Missing required columns: " + missingColumns);
                    }
                    continue;
                }

                // Skip rows between header and data
                if (currentRowNum < dataStartRowNum) {
                    continue;
                }

                // Read data rows
                Map<String, Object> rowData = new LinkedHashMap<>();
                for (Map.Entry<String, Integer> entry : headerMap.entrySet()) {
                    Cell cell = row.getCell(entry.getValue());
                    rowData.put(entry.getKey(), getCellValue(cell));
                }

                // Skip empty rows
                boolean hasData = rowData.values().stream()
                        .anyMatch(v -> v != null && !v.toString().trim().isEmpty());
                if (hasData) {
                    allData.add(rowData);
                }

                // Log progress every 10000 rows
                if (allData.size() % 10000 == 0 && allData.size() > 0) {
                    System.out.println("Read " + allData.size() + " data rows...");
                }
            }

            System.out.println("Total data rows read: " + allData.size());

            int originalRows = allData.size();

            // Apply Company Code filter if provided
            if (companyCode != null && !companyCode.isEmpty()) {
                if (!headerMap.containsKey("Company Code")) {
                    throw new IllegalArgumentException("Company Code column not found");
                }

                allData = allData.stream()
                        .filter(row -> companyCode.equals(
                                FormulaMapper.getStringValue(row.get("Company Code"))))
                        .collect(Collectors.toList());

                if (allData.isEmpty()) {
                    throw new IllegalArgumentException("No records found for Company Code: " + companyCode);
                }
            }

            // Group data by Translation Type (creates separate sheets)
            Map<String, List<Map<String, Object>>> groupedData = allData.stream()
                    .collect(Collectors.groupingBy(row ->
                            FormulaMapper.getStringValue(row.get("Translation Type"))));

            // SXSSFWorkbook: Memory-efficient writing (streaming)
            // Only keeps 100 rows in memory, flushes older rows to disk
            try (SXSSFWorkbook outputWorkbook = new SXSSFWorkbook(100)) {

                // Create cell styles
                CellStyle headerStyle = createHeaderStyle(outputWorkbook);
                CellStyle sumStyle = createSumStyle(outputWorkbook);
                Map<String, CellStyle> numberStyles = createNumberStyles(outputWorkbook);

                // Get column indices for formulas
                int tcIdx = FormulaMapper.TEMPLATE_COLUMNS.indexOf("TC");
                int debitoIdx = FormulaMapper.TEMPLATE_COLUMNS.indexOf("debito");
                int creditoIdx = FormulaMapper.TEMPLATE_COLUMNS.indexOf("credito");
                int debitoConvertidoIdx = FormulaMapper.TEMPLATE_COLUMNS.indexOf("debito_convertido");
                int creditoConvertidoIdx = FormulaMapper.TEMPLATE_COLUMNS.indexOf("credito_convertido");

                String tcLetter = FormulaMapper.getColumnLetter(tcIdx);
                String debitoLetter = FormulaMapper.getColumnLetter(debitoIdx);
                String creditoLetter = FormulaMapper.getColumnLetter(creditoIdx);
                String debitoConvertidoLetter = FormulaMapper.getColumnLetter(debitoConvertidoIdx);
                String creditoConvertidoLetter = FormulaMapper.getColumnLetter(creditoConvertidoIdx);

                // Create sheet for each Translation Type
                for (Map.Entry<String, List<Map<String, Object>>> entry : groupedData.entrySet()) {
                    String sheetName = sanitizeSheetName(entry.getKey());
                    List<Map<String, Object>> sheetData = entry.getValue();

                    Sheet sheet = outputWorkbook.createSheet(sheetName);

                    // Create header row
                    Row headerRowOut = sheet.createRow(request.getTemplateHeaderStart() - 1);
                    for (int i = 0; i < FormulaMapper.TEMPLATE_COLUMNS.size(); i++) {
                        Cell cell = headerRowOut.createCell(i);
                        cell.setCellValue(FormulaMapper.TEMPLATE_COLUMNS.get(i));
                        cell.setCellStyle(headerStyle);
                    }

                    // Add data rows
                    int rowNum = request.getTemplateHeaderStart();
                    for (Map<String, Object> rowData : sheetData) {
                        Row dataRow = sheet.createRow(rowNum);
                        String glAccount = FormulaMapper.getStringValue(rowData.get("GL Account"));
                        double amount = FormulaMapper.getDoubleValue(
                                rowData.get("Amount in Contract Currency"));

                        for (int colIdx = 0; colIdx < FormulaMapper.TEMPLATE_COLUMNS.size(); colIdx++) {
                            String header = FormulaMapper.TEMPLATE_COLUMNS.get(colIdx);
                            Cell cell = dataRow.createCell(colIdx);

                            switch (header) {
                                case "TC":
                                    // Leave empty for user to fill exchange rate
                                    break;
                                case "Nombre":
                                    cell.setCellValue(FormulaMapper.generateNombre(rowData));
                                    break;
                                case "divisa":
                                    cell.setCellValue(FormulaMapper.getStringValue(
                                            rowData.get("Contract Currency")));
                                    break;
                                case "compania":
                                case "Unidad":
                                case "CC":
                                case "ubicacion":
                                case "cuenta":
                                case "subcuenta":
                                case "equipo":
                                case "intercompania":
                                    cell.setCellValue(FormulaMapper.splitGlAccount(glAccount, header));
                                    break;
                                case "debito":
                                    double debito = FormulaMapper.calculateDebito(amount);
                                    cell.setCellValue(debito);
                                    cell.setCellStyle(numberStyles.get("debito"));
                                    break;
                                case "credito":
                                    double credito = FormulaMapper.calculateCredito(amount);
                                    cell.setCellValue(credito);
                                    cell.setCellStyle(numberStyles.get("credito"));
                                    break;
                                case "debito_convertido":
                                    // Excel formula: =IF(OR(ISBLANK(A2),ISBLANK(L2)),0,A2*L2)
                                    cell.setCellFormula(FormulaMapper.getExchangeMultiplierFormula(
                                            rowNum + 1, tcLetter, debitoLetter));
                                    cell.setCellStyle(numberStyles.get("debito_convertido"));
                                    break;
                                case "credito_convertido":
                                    cell.setCellFormula(FormulaMapper.getExchangeMultiplierFormula(
                                            rowNum + 1, tcLetter, creditoLetter));
                                    cell.setCellStyle(numberStyles.get("credito_convertido"));
                                    break;
                                case "descripcion":
                                    cell.setCellValue(FormulaMapper.generateDescripcion(rowData));
                                    break;
                            }
                        }
                        rowNum++;
                    }

                    // Add sum formulas at the end
                    int lastDataRow = rowNum;
                    Row sumRow = sheet.createRow(lastDataRow);

                    Cell debitoSumCell = sumRow.createCell(debitoIdx);
                    debitoSumCell.setCellFormula(FormulaMapper.getSumRowsFormula(lastDataRow, debitoLetter));
                    debitoSumCell.setCellStyle(sumStyle);

                    Cell creditoSumCell = sumRow.createCell(creditoIdx);
                    creditoSumCell.setCellFormula(FormulaMapper.getSumRowsFormula(lastDataRow, creditoLetter));
                    creditoSumCell.setCellStyle(sumStyle);

                    Cell debitoConvSumCell = sumRow.createCell(debitoConvertidoIdx);
                    debitoConvSumCell.setCellFormula(
                            FormulaMapper.getSumRowsFormula(lastDataRow, debitoConvertidoLetter));
                    debitoConvSumCell.setCellStyle(sumStyle);

                    Cell creditoConvSumCell = sumRow.createCell(creditoConvertidoIdx);
                    creditoConvSumCell.setCellFormula(
                            FormulaMapper.getSumRowsFormula(lastDataRow, creditoConvertidoLetter));
                    creditoConvSumCell.setCellStyle(sumStyle);

                    // Set column widths (auto-size not supported with streaming)
                    for (int i = 0; i < FormulaMapper.TEMPLATE_COLUMNS.size(); i++) {
                        sheet.setColumnWidth(i, 4000);
                    }
                }

                // Save workbook
                try (FileOutputStream fos = new FileOutputStream(outputPath)) {
                    outputWorkbook.write(fos);
                }

                // Clean up temporary files used by SXSSF
                outputWorkbook.dispose();
            }

            result.put("success", true);
            result.put("message", "File processed successfully");
            result.put("input_rows", allData.size());
            result.put("output_rows", allData.size());
            result.put("output_file", outputPath);
            result.put("file_size", Files.size(Paths.get(outputPath)));

            if (companyCode != null && !companyCode.isEmpty()) {
                result.put("filtered_by_company_code", companyCode);
                result.put("original_rows", originalRows);
            }

        } catch (Exception e) {
            result.put("success", false);
            result.put("message", "Processing error: " + e.getMessage());
            result.put("error", e.getMessage());
            e.printStackTrace();
        }

        return result;
    }

    /**
     * Extract unique company codes from Excel file (for filter dropdown)
     */
    public List<String> extractCompanyCodes(String filePath, int headerStart) throws IOException {
        try (FileInputStream fis = new FileInputStream(filePath);
             Workbook workbook = StreamingReader.builder()
                     .rowCacheSize(100)
                     .bufferSize(4096)
                     .open(fis)) {

            Sheet sheet = workbook.getSheetAt(0);
            int companyCodeCol = -1;
            Set<String> companyCodes = new TreeSet<>();
            int headerRowNum = headerStart - 1;

            for (Row row : sheet) {
                int currentRowNum = row.getRowNum();

                if (currentRowNum < headerRowNum) continue;

                if (currentRowNum == headerRowNum) {
                    for (Cell cell : row) {
                        String headerName = getCellValueAsString(cell);
                        if ("Company Code".equalsIgnoreCase(headerName)) {
                            companyCodeCol = cell.getColumnIndex();
                            break;
                        }
                    }
                    if (companyCodeCol == -1) {
                        throw new IllegalArgumentException("Company Code column not found");
                    }
                    continue;
                }

                Cell cell = row.getCell(companyCodeCol);
                String value = FormulaMapper.getStringValue(getCellValue(cell));
                if (!value.isEmpty()) {
                    companyCodes.add(value);
                }
            }

            return new ArrayList<>(companyCodes);
        }
    }

    // Helper methods for reading cell values...
    private Object getCellValue(Cell cell) {
        if (cell == null) return null;

        switch (cell.getCellType()) {
            case STRING: return cell.getStringCellValue();
            case NUMERIC:
                if (DateUtil.isCellDateFormatted(cell)) {
                    return cell.getLocalDateTimeCellValue();
                }
                return cell.getNumericCellValue();
            case BOOLEAN: return cell.getBooleanCellValue();
            case FORMULA:
                try { return cell.getNumericCellValue(); }
                catch (Exception e) {
                    try { return cell.getStringCellValue(); }
                    catch (Exception e2) { return null; }
                }
            default: return null;
        }
    }

    private String getCellValueAsString(Cell cell) {
        if (cell == null) return null;

        switch (cell.getCellType()) {
            case STRING: return cell.getStringCellValue().trim();
            case NUMERIC:
                double numValue = cell.getNumericCellValue();
                if (numValue == Math.floor(numValue)) {
                    return String.valueOf((int) numValue);
                }
                return String.valueOf(numValue);
            case BOOLEAN: return String.valueOf(cell.getBooleanCellValue());
            case BLANK: return "";
            default: return null;
        }
    }

    // Styling methods...
    private CellStyle createHeaderStyle(Workbook workbook) {
        CellStyle style = workbook.createCellStyle();
        Font font = workbook.createFont();
        font.setBold(true);
        style.setFont(font);
        style.setFillForegroundColor(IndexedColors.LIGHT_TURQUOISE.getIndex());
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        style.setAlignment(HorizontalAlignment.CENTER);
        return style;
    }

    private CellStyle createSumStyle(Workbook workbook) {
        CellStyle style = workbook.createCellStyle();
        style.setFillForegroundColor(IndexedColors.ROSE.getIndex());
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        DataFormat format = workbook.createDataFormat();
        style.setDataFormat(format.getFormat("#,##0.00"));
        return style;
    }

    private Map<String, CellStyle> createNumberStyles(Workbook workbook) {
        Map<String, CellStyle> styles = new HashMap<>();
        DataFormat format = workbook.createDataFormat();
        for (String key : FormulaMapper.CELL_NUMBER_FORMAT.keySet()) {
            CellStyle style = workbook.createCellStyle();
            style.setDataFormat(format.getFormat("#,##0.00"));
            styles.put(key, style);
        }
        return styles;
    }

    private String sanitizeSheetName(String name) {
        if (name == null || name.isEmpty()) return "Sheet";
        String sanitized = name.replaceAll("[\\[\\]*/\\\\?:]", "_");
        return sanitized.length() > 31 ? sanitized.substring(0, 31) : sanitized;
    }

    public void cleanupOldFiles() {
        // Cleanup logic...
    }
}
```

---

## Key Concepts: Memory-Efficient Excel Processing

### Problem: Traditional Apache POI
```java
// BAD: Loads entire file into memory (OutOfMemoryError for large files)
Workbook workbook = new XSSFWorkbook(new FileInputStream("large.xlsx"));
```

### Solution: Streaming APIs

**Reading (StreamingReader):**
```java
// GOOD: Streams rows, only 100 rows in memory
Workbook workbook = StreamingReader.builder()
        .rowCacheSize(100)
        .open(inputStream);

for (Row row : sheet) {
    // Process row by row
}
```

**Writing (SXSSFWorkbook):**
```java
// GOOD: Flushes rows to disk, only 100 rows in memory
SXSSFWorkbook workbook = new SXSSFWorkbook(100);
// ... write rows ...
workbook.dispose(); // Clean up temp files
```

### Comparison: Python vs Java

| Aspect | Python (pandas) | Java (POI Streaming) |
|--------|----------------|---------------------|
| Memory | Lazy loading by default | Need StreamingReader |
| Reading | `pd.read_excel()` | `StreamingReader.builder().open()` |
| Writing | `df.to_excel()` | `SXSSFWorkbook` |
| Speed | ~44 seconds | Similar with streaming |

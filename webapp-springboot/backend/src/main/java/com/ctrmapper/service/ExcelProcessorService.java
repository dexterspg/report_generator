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

    public Map<String, Object> processFile(String inputPath, String outputPath,
                                            ProcessingRequest request, String companyCode) {
        Map<String, Object> result = new HashMap<>();

        // Use streaming reader for memory efficiency (like pandas)
        try (FileInputStream fis = new FileInputStream(inputPath);
             Workbook inputWorkbook = StreamingReader.builder()
                     .rowCacheSize(100)      // Number of rows to keep in memory
                     .bufferSize(4096)       // Buffer size for reading
                     .open(fis)) {

            Sheet inputSheet = inputWorkbook.getSheetAt(0);

            // Read headers and data in a single pass (streaming requires this)
            Map<String, Integer> headerMap = new LinkedHashMap<>();
            List<Map<String, Object>> allData = new ArrayList<>();

            // Header row is 1-indexed from user, but POI uses 0-indexed
            int headerRowNum = request.getInputHeaderStart() - 1;
            int dataStartRowNum = request.getInputDataStart() - 1;

            System.out.println("Looking for header at row " + request.getInputHeaderStart() + " (0-indexed: " + headerRowNum + ")");

            for (Row row : inputSheet) {
                int currentRowNum = row.getRowNum(); // 0-indexed actual Excel row number

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
                    System.out.println("Found headers at row " + (currentRowNum + 1) + ": " + headerMap.keySet());

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

                // Skip rows between header and data start
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
                boolean hasData = rowData.values().stream().anyMatch(v -> v != null && !v.toString().trim().isEmpty());
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
                    throw new IllegalArgumentException("Company Code column not found in the input file");
                }

                allData = allData.stream()
                        .filter(row -> companyCode.equals(FormulaMapper.getStringValue(row.get("Company Code"))))
                        .collect(Collectors.toList());

                if (allData.isEmpty()) {
                    throw new IllegalArgumentException("No records found for Company Code: " + companyCode);
                }
            }

            // Group by Translation Type
            Map<String, List<Map<String, Object>>> groupedData = allData.stream()
                    .collect(Collectors.groupingBy(row ->
                            FormulaMapper.getStringValue(row.get("Translation Type"))));

            // Create output workbook (using streaming for memory efficiency)
            try (SXSSFWorkbook outputWorkbook = new SXSSFWorkbook(100)) { // Keep 100 rows in memory

                // Create styles
                CellStyle headerStyle = createHeaderStyle(outputWorkbook);
                CellStyle sumStyle = createSumStyle(outputWorkbook);
                Map<String, CellStyle> numberStyles = createNumberStyles(outputWorkbook);

                // Get column indices
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
                    String sheetName = entry.getKey();
                    List<Map<String, Object>> sheetData = entry.getValue();

                    // Sanitize sheet name (Excel has restrictions)
                    sheetName = sanitizeSheetName(sheetName);
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
                        double amount = FormulaMapper.getDoubleValue(rowData.get("Amount in Contract Currency"));

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
                                    cell.setCellValue(FormulaMapper.getStringValue(rowData.get("Contract Currency")));
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

                    // Add sum row
                    int lastDataRow = rowNum;
                    Row sumRow = sheet.createRow(lastDataRow);

                    // Debito sum
                    Cell debitoSumCell = sumRow.createCell(debitoIdx);
                    debitoSumCell.setCellFormula(FormulaMapper.getSumRowsFormula(lastDataRow, debitoLetter));
                    debitoSumCell.setCellStyle(sumStyle);

                    // Credito sum
                    Cell creditoSumCell = sumRow.createCell(creditoIdx);
                    creditoSumCell.setCellFormula(FormulaMapper.getSumRowsFormula(lastDataRow, creditoLetter));
                    creditoSumCell.setCellStyle(sumStyle);

                    // Debito convertido sum
                    Cell debitoConvSumCell = sumRow.createCell(debitoConvertidoIdx);
                    debitoConvSumCell.setCellFormula(FormulaMapper.getSumRowsFormula(lastDataRow, debitoConvertidoLetter));
                    debitoConvSumCell.setCellStyle(sumStyle);

                    // Credito convertido sum
                    Cell creditoConvSumCell = sumRow.createCell(creditoConvertidoIdx);
                    creditoConvSumCell.setCellFormula(FormulaMapper.getSumRowsFormula(lastDataRow, creditoConvertidoLetter));
                    creditoConvSumCell.setCellStyle(sumStyle);

                    // Note: Auto-size columns not supported with streaming workbook
                    // Set reasonable default widths instead
                    for (int i = 0; i < FormulaMapper.TEMPLATE_COLUMNS.size(); i++) {
                        sheet.setColumnWidth(i, 4000); // ~14 characters wide
                    }
                }

                // Save workbook
                try (FileOutputStream fos = new FileOutputStream(outputPath)) {
                    outputWorkbook.write(fos);
                }

                // Dispose of temporary files used by SXSSF
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
                result.put("message", "File processed successfully (filtered for Company Code: " + companyCode + ")");
            }

        } catch (Exception e) {
            result.put("success", false);
            result.put("message", "Processing error: " + e.getMessage());
            result.put("error", e.getMessage());
            e.printStackTrace();
        }

        return result;
    }

    public List<String> extractCompanyCodes(String filePath, int headerStart) throws IOException {
        // Use streaming reader for memory efficiency
        try (FileInputStream fis = new FileInputStream(filePath);
             Workbook workbook = StreamingReader.builder()
                     .rowCacheSize(100)
                     .bufferSize(4096)
                     .open(fis)) {

            Sheet sheet = workbook.getSheetAt(0);

            // Find Company Code column and extract values in single pass
            int companyCodeCol = -1;
            Set<String> companyCodes = new TreeSet<>();

            // Header row is 1-indexed from user, but POI uses 0-indexed
            int headerRowNum = headerStart - 1;

            for (Row row : sheet) {
                int currentRowNum = row.getRowNum(); // 0-indexed actual Excel row number

                if (currentRowNum < headerRowNum) {
                    continue;
                }

                // Header row - find Company Code column
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

                // Data rows - extract company code values
                Cell cell = row.getCell(companyCodeCol);
                String value = FormulaMapper.getStringValue(getCellValue(cell));
                if (!value.isEmpty()) {
                    companyCodes.add(value);
                }
            }

            return new ArrayList<>(companyCodes);
        }
    }

    private Object getCellValue(Cell cell) {
        if (cell == null) {
            return null;
        }

        switch (cell.getCellType()) {
            case STRING:
                return cell.getStringCellValue();
            case NUMERIC:
                if (DateUtil.isCellDateFormatted(cell)) {
                    return cell.getLocalDateTimeCellValue();
                }
                return cell.getNumericCellValue();
            case BOOLEAN:
                return cell.getBooleanCellValue();
            case FORMULA:
                try {
                    return cell.getNumericCellValue();
                } catch (Exception e) {
                    try {
                        return cell.getStringCellValue();
                    } catch (Exception e2) {
                        return null;
                    }
                }
            default:
                return null;
        }
    }

    private String getCellValueAsString(Cell cell) {
        if (cell == null) {
            return null;
        }

        switch (cell.getCellType()) {
            case STRING:
                return cell.getStringCellValue().trim();
            case NUMERIC:
                double numValue = cell.getNumericCellValue();
                if (numValue == Math.floor(numValue)) {
                    return String.valueOf((int) numValue);
                }
                return String.valueOf(numValue);
            case BOOLEAN:
                return String.valueOf(cell.getBooleanCellValue());
            case FORMULA:
                try {
                    return cell.getStringCellValue().trim();
                } catch (Exception e) {
                    try {
                        return String.valueOf(cell.getNumericCellValue());
                    } catch (Exception e2) {
                        return null;
                    }
                }
            case BLANK:
                return "";
            default:
                return null;
        }
    }

    private CellStyle createHeaderStyle(Workbook workbook) {
        CellStyle style = workbook.createCellStyle();
        Font font = workbook.createFont();
        font.setBold(true);
        font.setFontName("Calibri");
        font.setFontHeightInPoints((short) 11);
        style.setFont(font);
        style.setFillForegroundColor(IndexedColors.LIGHT_TURQUOISE.getIndex());
        style.setFillPattern(FillPatternType.SOLID_FOREGROUND);
        style.setAlignment(HorizontalAlignment.CENTER);
        style.setVerticalAlignment(VerticalAlignment.CENTER);
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

        for (Map.Entry<String, String> entry : FormulaMapper.CELL_NUMBER_FORMAT.entrySet()) {
            CellStyle style = workbook.createCellStyle();
            style.setDataFormat(format.getFormat("#,##0.00"));
            styles.put(entry.getKey(), style);
        }

        return styles;
    }

    private String sanitizeSheetName(String name) {
        if (name == null || name.isEmpty()) {
            return "Sheet";
        }
        // Excel sheet name restrictions: max 31 chars, no special chars
        String sanitized = name.replaceAll("[\\[\\]*/\\\\?:]", "_");
        if (sanitized.length() > 31) {
            sanitized = sanitized.substring(0, 31);
        }
        return sanitized;
    }

    public void cleanupOldFiles() {
        try {
            long currentTime = System.currentTimeMillis();
            long oneHour = 3600000;

            Files.list(uploadDir)
                    .filter(path -> {
                        try {
                            return currentTime - Files.getLastModifiedTime(path).toMillis() > oneHour;
                        } catch (IOException e) {
                            return false;
                        }
                    })
                    .forEach(path -> {
                        try {
                            Files.deleteIfExists(path);
                        } catch (IOException e) {
                            System.err.println("Could not delete: " + path);
                        }
                    });

            // Clean up old jobs
            jobs.entrySet().removeIf(entry -> {
                JobStatus job = entry.getValue();
                if (job.getCompletedAt() != null) {
                    return job.getCompletedAt().plusHours(1).isBefore(LocalDateTime.now());
                }
                return false;
            });

        } catch (IOException e) {
            System.err.println("Cleanup error: " + e.getMessage());
        }
    }
}

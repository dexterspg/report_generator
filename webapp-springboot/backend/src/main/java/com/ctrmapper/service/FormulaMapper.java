package com.ctrmapper.service;

import org.apache.poi.ss.usermodel.*;
import org.apache.poi.ss.util.CellReference;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;

public class FormulaMapper {

    // Column headers in order
    public static final List<String> TEMPLATE_COLUMNS = Arrays.asList(
            "TC", "Nombre", "divisa", "compania", "Unidad", "CC", "ubicacion",
            "cuenta", "subcuenta", "equipo", "intercompania", "debito", "credito",
            "debito_convertido", "credito_convertido", "descripcion"
    );

    // GL Account split index mapping
    private static final Map<String, Integer> GL_ACCOUNT_INDEX = new LinkedHashMap<>();
    static {
        GL_ACCOUNT_INDEX.put("compania", 0);
        GL_ACCOUNT_INDEX.put("Unidad", 1);
        GL_ACCOUNT_INDEX.put("CC", 2);
        GL_ACCOUNT_INDEX.put("ubicacion", 3);
        GL_ACCOUNT_INDEX.put("cuenta", 4);
        GL_ACCOUNT_INDEX.put("subcuenta", 5);
        GL_ACCOUNT_INDEX.put("equipo", 6);
        GL_ACCOUNT_INDEX.put("intercompania", 7);
    }

    // Cell number formats
    public static final Map<String, String> CELL_NUMBER_FORMAT = new LinkedHashMap<>();
    static {
        CELL_NUMBER_FORMAT.put("TC", "_-* #,##0.0000_-;-* #,##0.0000_-;_-* \"-\"??_-;_-@_-");
        CELL_NUMBER_FORMAT.put("debito", "_-* #,##0.00_-;-* #,##0.00_-;_-* \"-\"??_-;_-@_-");
        CELL_NUMBER_FORMAT.put("credito", "_-* #,##0.00_-;-* #,##0.00_-;_-* \"-\"??_-;_-@_-");
        CELL_NUMBER_FORMAT.put("debito_convertido", "_-* #,##0.00_-;-* #,##0.00_-;_-* \"-\"??_-;_-@_-");
        CELL_NUMBER_FORMAT.put("credito_convertido", "_-* #,##0.00_-;-* #,##0.00_-;_-* \"-\"??_-;_-@_-");
    }

    /**
     * Generate Nombre formula: Translation Type + Month-Year
     */
    public static String generateNombre(Map<String, Object> rowData) {
        try {
            String translationType = getStringValue(rowData.get("Translation Type"));
            String fiscalYear = getStringValue(rowData.get("Fiscal Year"));
            String fiscalPeriod = getStringValue(rowData.get("Fiscal Period"));

            int year = Integer.parseInt(fiscalYear);
            int month = Integer.parseInt(fiscalPeriod);

            LocalDate date = LocalDate.of(year, month, 1);
            String monthYear = date.format(DateTimeFormatter.ofPattern("MMM-yyyy")).toLowerCase();

            return translationType + " " + monthYear;
        } catch (Exception e) {
            return "";
        }
    }

    /**
     * Generate Descripcion formula
     */
    public static String generateDescripcion(Map<String, Object> rowData) {
        String unit = getStringValue(rowData.get("Unit"));
        String fiscalYear = getStringValue(rowData.get("Fiscal Year"));
        String fiscalPeriod = getStringValue(rowData.get("Fiscal Period"));
        String contractName = getStringValue(rowData.get("Contract Name"));
        String vendor = getStringValue(rowData.get("Vendor"));

        return String.format("M1/%s/%s/%s/%s/%s", unit, fiscalYear, fiscalPeriod, contractName, vendor);
    }

    /**
     * Split GL Account by dash and return the specified component
     */
    public static String splitGlAccount(String glAccount, String component) {
        Integer index = GL_ACCOUNT_INDEX.get(component);
        if (index == null || glAccount == null) {
            return "";
        }

        String[] parts = glAccount.split("-");
        if (parts.length > index) {
            return parts[index];
        }
        return "";
    }

    /**
     * Calculate debito (positive amounts)
     */
    public static double calculateDebito(double amount) {
        return amount > 0 ? amount : 0;
    }

    /**
     * Calculate credito (absolute value of negative amounts)
     */
    public static double calculateCredito(double amount) {
        return amount < 0 ? Math.abs(amount) : 0;
    }

    /**
     * Generate Excel formula for exchange rate multiplication
     */
    public static String getExchangeMultiplierFormula(int rowIdx, String tcLetter, String debitCreditLetter) {
        return String.format("IF(OR(ISBLANK(%s%d),ISBLANK(%s%d)),0,%s%d*%s%d)",
                tcLetter, rowIdx, debitCreditLetter, rowIdx, tcLetter, rowIdx, debitCreditLetter, rowIdx);
    }

    /**
     * Generate Excel formula for summing rows
     */
    public static String getSumRowsFormula(int lastRowIdx, String debitCreditLetter) {
        return String.format("SUM(%s2:%s%d)", debitCreditLetter, debitCreditLetter, lastRowIdx);
    }

    /**
     * Get column letter from column index (0-based)
     */
    public static String getColumnLetter(int columnIndex) {
        return CellReference.convertNumToColString(columnIndex);
    }

    /**
     * Get string value from object, handling nulls
     */
    public static String getStringValue(Object value) {
        if (value == null) {
            return "";
        }
        if (value instanceof Double) {
            double d = (Double) value;
            if (d == Math.floor(d)) {
                return String.valueOf((int) d);
            }
        }
        return value.toString().trim();
    }

    /**
     * Get double value from object, handling nulls
     */
    public static double getDoubleValue(Object value) {
        if (value == null) {
            return 0.0;
        }
        if (value instanceof Number) {
            return ((Number) value).doubleValue();
        }
        try {
            return Double.parseDouble(value.toString());
        } catch (NumberFormatException e) {
            return 0.0;
        }
    }
}

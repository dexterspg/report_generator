# Changelog

## [Unreleased] - 2026-02-05

### Added

#### Auto-Export Multiple Excel Files by Company Code

The application now automatically generates one Excel file per unique company code, bundled in a ZIP archive.

**New Behavior:**
- Upload file → Automatically processes ALL company codes → ZIP file download
- Each Excel file named: `poliza_ledger_{company_code}.xlsx`
- Each file contains sheets grouped by Transaction Type

**Backend Changes:**
- Added `process_file_all_company_codes()` method in `excel_processor.py`
- Updated `/upload` endpoint to generate ZIP files
- Updated `/download` endpoint to serve ZIP files

**Frontend Changes:**
- Company code dropdown hidden (code preserved for future use)
- Results section shows list of company codes included in ZIP
- Download button indicates ZIP file

**Note:** The single company code filter functionality is preserved in the code and can be re-enabled by:
1. Setting `showCompanyCodeFilter` prop to `true` in `UploadSection`
2. Uncommenting the company code extraction and form data in `App.vue`

#### Added i18n Translations for ZIP Results

Added missing translation keys for the new ZIP file results display:

**English (`en.json`):**
- `results.companyCodes`: "Company Codes in ZIP:"
- `results.files`: "files"
- `results.readyDownloadZip`: "Your ZIP file with all company codes is ready for download."
- `results.downloadZip`: "📥 Download ZIP"

**Spanish (`es.json`):**
- `results.companyCodes`: "Códigos de Empresa en ZIP:"
- `results.files`: "archivos"
- `results.readyDownloadZip`: "Tu archivo ZIP con todos los códigos de empresa está listo para descargar."
- `results.downloadZip`: "📥 Descargar ZIP"

### Changed

#### Field Mapping Logic - Data-Driven Approach

Migrated from a formula-based approach to a data-driven approach for currency conversion fields.

**Before:** Users manually entered the exchange rate (TC) in Excel, and converted amounts were calculated via Excel formulas (`=TC * debito`).

**After:** Exchange rate and converted amounts are now pulled directly from pre-calculated columns in the source data.

#### Field Mapping Updates

| Output Field | Previous Source | New Source |
|--------------|-----------------|------------|
| TC | Manual entry | `Company Currency Exchange Rate` |
| debito_convertido | Excel formula (`=TC * debito`) | `Amount in Company Currency` (positive values) |
| credito_convertido | Excel formula (`=TC * credito`) | `Amount in Company Currency` (negative values, absolute) |

#### Input Column Renames

| Previous Column Name | New Column Name |
|----------------------|-----------------|
| GL Account | Account Number |
| Translation Type | Transaction Type |
| Unit | Activation Group ID |

#### New Required Input Columns

- `Company Currency Exchange Rate`
- `Amount in Company Currency`

#### Removed Features

- Sum totals row at the bottom of each sheet (commented out)
- Excel formula generation for converted amounts

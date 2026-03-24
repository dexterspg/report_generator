from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(10)
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ""
            run = cell.paragraphs[0].add_run(val)
            run.font.size = Pt(10)
    return table


doc = Document()

# Style setup
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)
style.paragraph_format.space_after = Pt(6)

for level in range(1, 4):
    h = doc.styles[f"Heading {level}"]
    h.font.name = "Calibri"
    h.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

# ---- TITLE ----
p = doc.add_heading("Proof of Concept: CTR FX Remeasurement Tool", level=0)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

meta = [
    ("Ticket", "LAE-44136 (Abbott Laboratories)"),
    ("Author", "Dexter Pagkaliwangan"),
    ("Date", "2026-03-23"),
    ("Status", "Draft"),
]
for label, value in meta:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{label}: ")
    run.bold = True
    run.font.size = Pt(11)
    run = p.add_run(value)
    run.font.size = Pt(11)

doc.add_paragraph()

# ---- 1. EXECUTIVE SUMMARY ----
doc.add_heading("1. Executive Summary", level=1)
doc.add_paragraph(
    "Multi-currency clients such as Abbott Laboratories currently perform FX "
    "remeasurement manually in Excel every fiscal period \u2014 a high-risk, "
    "error-prone process that directly affects financial statements under IFRS 16 "
    "and GAAP. This PoC validates that the core calculation engine can be automated "
    "reliably: parse a Nakisa CTR, aggregate closing balances, apply period-end "
    "exchange rates, and produce the correct FX (Gain) or Loss per GL account."
)
doc.add_paragraph(
    "If the PoC passes, the result is a standalone desktop tool that eliminates "
    "the manual pivot process entirely. Abbott\u2019s implementation team will "
    "validate the output against their existing verified P1 worksheet \u2014 if "
    "values match, the Go decision is made to build the full application."
)

# ---- 2. PROBLEM STATEMENT ----
doc.add_heading("2. Problem Statement", level=1)
p = doc.add_paragraph()
run = p.add_run("The problem: ")
run.bold = True
p.add_run(
    "Multi-currency lease clients must calculate FX remeasurement every fiscal "
    "period to comply with IFRS 16 / GAAP. This is done entirely in Excel through "
    "a four-step manual process:"
)

for i, s in enumerate(
    [
        "Export the CTR from Nakisa Lease Administration",
        "Manually pivot the CTR to aggregate closing balances by GL account and currency",
        "Manually apply period-end exchange rates",
        "Manually calculate FX gain/loss per account",
    ],
    1,
):
    doc.add_paragraph(f"{i}. {s}")

p = doc.add_paragraph()
run = p.add_run("Who is affected: ")
run.bold = True
p.add_run(
    "Abbott Laboratories finance team; any Nakisa client with multi-currency lease portfolios."
)

p = doc.add_paragraph()
run = p.add_run("Current state: ")
run.bold = True
p.add_run(
    "Fully manual. Every fiscal period, a finance team member spends significant "
    "time performing the pivot and calculation in Excel with no automated checks."
)

p = doc.add_paragraph()
run = p.add_run("Impact of not solving: ")
run.bold = True
p.add_run(
    "Calculation errors go undetected until financial close review. Manual rework "
    "is required each period. Risk of misstatement on financial reports filed under "
    "IFRS 16 / GAAP."
)

# ---- 3. PROPOSED SOLUTION ----
doc.add_heading("3. Proposed Solution", level=1)
doc.add_paragraph(
    "A standalone desktop application that automates the end-to-end FX remeasurement process:"
)
for i, s in enumerate(
    [
        "Accepts a Nakisa CTR Excel export as input",
        "Reads account type (BS/P&L) and monetary flag from a client-supplied mapping file",
        "Reads period-end spot rates from a client-supplied exchange rates file",
        "Produces an output workbook with one worksheet per currency showing the FX (Gain) or Loss per GL account \u2014 the primary deliverable",
    ],
    1,
):
    doc.add_paragraph(f"{i}. {s}")

p = doc.add_paragraph()
run = p.add_run("Key capabilities:")
run.bold = True
for c in [
    "Automated CTR parsing with column validation",
    "Closing balance aggregation by account and contract currency",
    "FX calculation: Re-measured Balance = Balance in Contract Currency \u00d7 Period-End Spot Rate",
    "Multi-sheet output organized by currency",
    "Unmapped accounts flagged clearly rather than silently dropped",
]:
    doc.add_paragraph(c, style="List Bullet")

# ---- 4. GOALS & OBJECTIVES ----
doc.add_heading("4. Goals & Objectives", level=1)
add_table(
    doc,
    ["Goal", "Measurable Outcome"],
    [
        [
            "Validate calculation correctness",
            'FX (Gain) or Loss values match Abbott\u2019s manually verified \u201c3. CTR Pivot P1\u201d worksheet for CTR_0422.xlsx',
        ],
        [
            "Validate aggregation logic",
            "Closing balance sums per {Account, Currency} group reconcile row-by-row against the source CTR",
        ],
        [
            "Validate non-monetary handling",
            "Non-monetary accounts produce FX = 0 in output",
        ],
        [
            "Validate output structure",
            "One sheet per unique Contract Currency, named by currency code",
        ],
        [
            "Validate performance",
            "Processing completes in under 10 seconds for CTR_0422.xlsx",
        ],
    ],
)

# ---- 5. SCOPE ----
doc.add_heading("5. Scope", level=1)
p = doc.add_paragraph()
run = p.add_run("In scope:")
run.bold = True
for item in [
    "CTR file reading and validation (detect and reject files missing required columns)",
    "Closing balance aggregation by GL account and currency",
    "Account mapping input: account type (BS/P&L) and monetary flag (Yes/No)",
    "Exchange rate input: period-end spot rates per currency",
    "FX calculation and multi-sheet Excel output",
    "Standalone desktop application (.exe) that Abbott can run without installing additional software",
    "Validation against Abbott\u2019s P1 manual pivot for CTR_0422.xlsx",
]:
    doc.add_paragraph(item, style="List Bullet")

p = doc.add_paragraph()
run = p.add_run("Out of scope for PoC:")
run.bold = True
for item in [
    "Configuration history and rollback",
    "Prior period FX carryforward",
    "P&L account exclusion",
    "Multi-company output",
]:
    doc.add_paragraph(item, style="List Bullet")

p = doc.add_paragraph()
run = p.add_run("Assumptions:")
run.bold = True
for item in [
    "CTR column names follow the Nakisa standard format",
    "Abbott will supply the account mapping and P1 exchange rates",
    'Abbott\u2019s \u201c3. CTR Pivot P1\u201d worksheet is the authoritative expected output',
]:
    doc.add_paragraph(item, style="List Bullet")

# ---- 6. REQUIRED RESOURCES ----
doc.add_heading("6. Required Resources", level=1)
add_table(
    doc,
    ["Resource", "Details"],
    [
        [
            "People",
            "1 implementation engineer (build + test); Abbott finance contact (data supply + sign-off)",
        ],
        [
            "Data",
            "CTR_0422.xlsx, account mapping file, P1 exchange rates file, Abbott\u2019s manual pivot worksheet",
        ],
        [
            "Budget",
            "Minimal \u2014 existing tooling and licenses; no new spend required",
        ],
        [
            "Time",
            "Estimated 8-9 weeks to build and validate; 1-2 additional weeks for client review and sign-off",
        ],
    ],
)

# ---- 7. SUCCESS CRITERIA ----
doc.add_heading("7. Success Criteria", level=1)
p = doc.add_paragraph()
run = p.add_run("The PoC is considered passed ")
run.bold = True
p.add_run("when all of the following are met:")

add_table(
    doc,
    ["#", "Criterion", "How Verified"],
    [
        [
            "SC-01",
            'FX (Gain) or Loss values match Abbott\u2019s \u201c3. CTR Pivot P1\u201d worksheet',
            "Side-by-side comparison by Abbott implementation team",
        ],
        [
            "SC-02",
            "Closing balance aggregation correctly sums all CTR rows per {Account, Currency}",
            "Row-by-row reconciliation against source CTR",
        ],
        ["SC-03", "Non-monetary accounts show FX (Gain) or Loss = 0", "Output inspection"],
        [
            "SC-04",
            "Output workbook contains one sheet per unique Contract Currency, named by currency code",
            "File inspection",
        ],
        [
            "SC-05",
            'Accounts missing from the mapping produce \u201cN/A\u201d in type/monetary columns and blank in FX columns',
            "Output inspection with partial mapping file",
        ],
        [
            "SC-06",
            "Processing completes in under 10 seconds for CTR_0422.xlsx",
            "Timed run",
        ],
    ],
)

doc.add_paragraph()
p = doc.add_paragraph()
run = p.add_run("The PoC is considered failed ")
run.bold = True
p.add_run("if:")
for item in [
    "FX values do not match Abbott\u2019s manual pivot after mapping and rate files are confirmed correct",
    "CTR structure is inconsistent enough that parsing cannot be reliably automated",
    "Abbott\u2019s account mapping cannot be supplied in time to run the validation",
]:
    doc.add_paragraph(item, style="List Bullet")

# ---- 8. RISK ASSESSMENT ----
doc.add_heading("8. Risk Assessment", level=1)
add_table(
    doc,
    ["Risk", "Likelihood", "Impact", "Mitigation"],
    [
        [
            "CTR column names differ from Nakisa standard",
            "Low",
            "High",
            "Confirm column names against CTR_0422.xlsx before PoC run",
        ],
        [
            "Abbott\u2019s account mapping is incomplete",
            "Medium",
            "Medium",
            "Flag unmapped accounts in output; Abbott fills in gaps before sign-off",
        ],
        [
            "Exchange rates for P1 not yet available",
            "Low",
            "High",
            "Use P1 rates from Abbott\u2019s existing manual worksheet",
        ],
        [
            "Metadata row count varies by export settings",
            "Low",
            "Medium",
            "Configurable header start parameter (default: row 27)",
        ],
        [
            "Non-standard currency codes in CTR",
            "Low",
            "Low",
            "Normalize to uppercase; non-standard codes produce a warning, not a failure",
        ],
    ],
)

# ---- 9. TIMELINE & MILESTONES ----
doc.add_heading("9. Timeline & Milestones", level=1)
add_table(
    doc,
    ["Milestone", "Target Date"],
    [
        ["Abbott supplies CTR, mapping, and rates files", "2026-03-25"],
        ["CTR file reading and validation complete", "2026-04-01"],
        ["Aggregation and FX calculation engine complete", "2026-04-08"],
        ["Excel output writer complete", "2026-04-14"],
        ["Backend API complete", "2026-04-28"],
        ["Frontend interface complete", "2026-05-19"],
        ["Desktop application packaging complete", "2026-05-23"],
        ["Internal validation and bug fixes", "2026-06-03"],
        ["Abbott review and sign-off", "2026-06-13"],
        ["Go / No-Go decision", "2026-06-17"],
    ],
)

# ---- 10. STAKEHOLDERS ----
doc.add_heading("10. Stakeholders", level=1)
add_table(
    doc,
    ["Name / Role", "Responsibility"],
    [
        [
            "Abbott Finance Contact",
            "Supplies input files; validates output against manual pivot; provides sign-off",
        ],
        ["Implementation Engineer", "Builds and runs the PoC; documents results"],
        ["Implementation Manager", "Go/No-Go decision maker"],
        [
            "Abbott Project Sponsor",
            "Informed of outcome; approves next phase if Go",
        ],
    ],
)

# ---- 11. HOW IT WORKS ----
doc.add_heading("11. How It Works", level=1)
doc.add_heading("Processing Steps", level=2)

steps_detail = [
    (
        "Step 1: Upload CTR Export",
        [
            "The tool reads the CTR Excel file exported from Nakisa",
            "Validates that all required columns are present",
            "Flags any rows with missing or invalid data",
        ],
    ),
    (
        "Step 2: Apply Configuration",
        [
            "Reads the account mapping file (account type + monetary flag)",
            "Reads the exchange rates file (period-end spot rates per currency)",
        ],
    ),
    (
        "Step 3: Calculate FX Remeasurement",
        [
            "Aggregates closing balances by GL account and currency",
            "Applies the period-end spot rate to monetary accounts",
            "Preserves historical rates for non-monetary accounts",
            "Calculates the FX (Gain) or Loss per account",
        ],
    ),
    (
        "Step 4: Generate Output",
        [
            "Produces an Excel workbook with one worksheet per currency",
            "Accounts sorted by Account Number within each sheet",
            "Unmapped accounts flagged clearly for review",
        ],
    ),
]
for title, details in steps_detail:
    p = doc.add_paragraph()
    run = p.add_run(title)
    run.bold = True
    for d in details:
        doc.add_paragraph(d, style="List Bullet")

doc.add_heading("Key Formula", level=2)
add_table(
    doc,
    ["Account Type", "Re-measured Balance", "FX (Gain) or Loss"],
    [
        [
            "Monetary",
            "Balance in Contract Currency \u00d7 Period-End Spot Rate",
            "Re-measured Balance \u2212 Initial Measurement",
        ],
        [
            "Non-Monetary",
            "Initial Measurement (unchanged \u2014 historical rate preserved)",
            "0",
        ],
        ["Unmapped", "Blank", "Blank"],
    ],
)

doc.add_heading("Example Calculation", level=2)
add_table(
    doc,
    ["Input", "Value"],
    [
        ["Balance in Contract Currency", "10,000 USD"],
        ["Initial Measurement (Company Currency)", "130,000 MXN"],
        ["Period-End Spot Rate", "14.0"],
        ["Re-measured Balance", "140,000 MXN"],
        ["FX (Gain) or Loss", "10,000 MXN"],
    ],
)

# ---- 12. RECOMMENDATION ----
doc.add_heading("12. Recommendation", level=1)
p = doc.add_paragraph()
run = p.add_run("Go \u2014 pending Abbott sign-off")
run.bold = True
run.font.size = Pt(13)

doc.add_paragraph(
    "The problem is well-defined, the calculation logic is deterministic, and the "
    "expected output (Abbott\u2019s manual pivot) is already available for validation. "
    "The implementation risk is low. If the PoC run confirms that calculated FX values "
    "match Abbott\u2019s manual worksheet, the decision is to proceed with the full "
    "build and rollout to Abbott."
)

# Footer
doc.add_paragraph()
p = doc.add_paragraph()
run = p.add_run("Document Status: ")
run.bold = True
p.add_run("Draft")
p = doc.add_paragraph()
run = p.add_run("Last Updated: ")
run.bold = True
p.add_run("2026-03-23")

doc.save("C:/workarea/report_generator/docs/proof-of-concept.docx")
print("Done: proof-of-concept.docx created")

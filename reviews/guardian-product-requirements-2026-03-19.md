# Quality Review: Product Requirements - CTR Closing Balance Extraction for FX Remeasurement

## Review Type
Documentation (Product Requirements)

## Summary

The product requirements document is well-structured, thorough, and demonstrates clear domain understanding. It correctly positions this as a standalone application separate from the Poliza Ledger CTR Mapper. The phasing is sensible, user stories are realistic, and the functional requirements are specific enough to implement against. However, there are several issues: leftover "mode" language from when this was conceived as a feature within the existing CTR Mapper, a few areas of over-engineering for a mini project of this scope, and some minor contradictions and gaps that should be cleaned up before implementation begins.

---

## Verdict

**Status:** REVISION_NEEDED
**Issue Type:** DOCUMENTATION_ISSUE
**Route To:** product-strategist
**Iteration:** 1 of 2

---

## Critical (Must Fix)

### 1. Phantom "FX Remeasurement mode" language in Acceptance Criteria

Lines 240, 244, 264, 292, 296 all use the phrase "selects FX Remeasurement mode" or "processed in FX Remeasurement mode." This is a standalone application -- there is no mode to select. The user uploads a file and gets output. This language is a leftover from when this was being designed as a mode within the existing CTR Mapper. Every instance of "FX Remeasurement mode" in section 5 should be replaced with plain action language (e.g., "uploads the file" or "the file is processed").

**Specific lines to fix:**
- Line 240: "the user selects FX Remeasurement mode and uploads the file" --> "the user uploads the file"
- Line 244: "processed in FX Remeasurement mode" --> "processed"
- Line 264: "processed in FX Remeasurement mode" --> "processed"
- Line 292: "processed in FX Remeasurement mode" --> "processed"
- Line 296: "processed in FX Remeasurement mode" --> "processed"

### 2. FR-017 introduces unnecessary async job complexity for Phase 1

FR-017 specifies "Asynchronous background processing with job ID, status polling (pending --> processing --> completed/failed)." While the existing CTR Mapper uses this pattern, that app processes multiple company codes and generates ZIPs. The FX Remeasurement tool in Phase 1 is simpler: read one file, group/aggregate, write one output file. For a file with 50,000 rows, this is a sub-second pandas operation.

**Recommendation:** Keep the async pattern if you want architectural consistency with the sister app (copy-paste simplicity), but explicitly note in the requirement that this is for consistency, not because Phase 1 processing warrants it. Otherwise an engineer might over-build the status polling UI. A simple synchronous upload-process-download would suffice for Phase 1 scope.

---

## Major (Should Fix)

### 3. NFR-002 (Scalability) is over-engineered for this scope

"The system shall handle multiple simultaneous uploads without degradation" -- this is a single-user or small-team internal tool. The existing CTR Mapper does not have scalability requirements beyond what FastAPI provides by default. This NFR reads like an enterprise platform requirement. Either remove it or soften it to "The system shall handle reasonable concurrent usage consistent with a small-team internal tool."

### 4. NFR-003 (Reliability) contains a contradiction

"Job status shall be recoverable if the server restarts (via in-memory job registry)" -- in-memory storage is explicitly NOT recoverable across server restarts. This contradicts itself. The constraint in Section 10 correctly states "No Database: Job data stored in-memory; not persisted across server restarts." Remove the recoverability claim from NFR-003.

### 5. FR-020 (i18n) may be premature for Phase 1

The existing CTR Mapper already has i18n support, so if this is being built from that template, i18n comes for free. But if this is a from-scratch build, requiring English AND Spanish in Phase 1 adds scope. Clarify whether this is inherited from the template or new work. If new work, consider deferring Spanish to Phase 2.

### 6. EC-003 mentions "streaming mode" that is not defined anywhere

"File with >50,000 data rows --> Accept but process in streaming mode if needed" -- no functional requirement defines what streaming mode is, how it works, or how to implement it. For a pandas-based tool, this is not a natural pattern. Either remove the streaming reference (pandas handles 50K rows trivially in memory) or define what it means.

### 7. Section 9 (Success Metrics) includes adoption metrics inappropriate for Phase 1

"Feature used by >=1 additional client within 2 months of release" -- this is a business/adoption metric, not an acceptance criterion for a mini project. It is not actionable by the implementation team. Move it to a separate business case or remove it.

---

## Minor (Consider)

### 8. FR-008 reserves empty columns 8-11 -- verify this is intentional

Outputting 4 empty columns with headers is unusual. It will confuse users who receive the Phase 1 output. Consider either: (a) omitting columns 8-11 entirely in Phase 1 and adding them in Phase 2, or (b) adding a note in the output explaining these are reserved for future use. The current approach is not wrong, but should be a deliberate choice, not a default.

### 9. Typo: "As a a client accountant" (double "a")

Lines 79 and 92 both have "As a a client accountant" -- minor typo.

### 10. FR-005 (configurable header/data row positions) -- is this needed?

The existing CTR Mapper has this configurability because different CTR exports might vary. If the FX Remeasurement tool targets the exact same CTR input format (which it does), the same configurability makes sense for consistency. But if this is truly always rows 27/28, consider whether exposing this in the UI adds unnecessary complexity. The backend can support it as parameters with defaults without surfacing it in the UI.

### 11. Test data references could be more specific

"CTR_0422.xlsx" and "Abbott period P1 data" are referenced but no expected output values are provided. For acceptance testing, consider adding at least one concrete expected output row (e.g., "Account 12345 in USD should show Balance in Contract Currency = X, Initial Measurement = Y").

### 12. EC-007 (Concurrent Requests) duplicates NFR-002

The edge case about concurrent requests is the same concern as the scalability NFR. Consolidate.

---

## Well Done

- **Clear problem statement** -- Section 1 effectively communicates the pain and business impact without being verbose.
- **Phasing is well thought out** -- Phase 1 is genuinely minimal (group + aggregate), Phase 2 adds the real calculation logic, Phase 3 adds advanced features. This is the right decomposition.
- **FR-016 explicitly states standalone** -- "independent from the existing Poliza Ledger (CTR Mapper) application" is clear and unambiguous.
- **Edge cases are thorough** -- Sections EC-001 through EC-009 cover realistic scenarios. This is better than most mini project PRDs.
- **Constraints and assumptions are explicit** -- Section 10 is honest about limitations (no database, no auth, in-memory only).
- **Out of scope is clearly defined** -- Section 7 draws a clean line between Phase 1 and future work.
- **The document mirrors the existing CTR Mapper's architectural decisions** -- web/desktop dual mode, same row configuration pattern, same file validation -- which will make implementation fast via template reuse.

---

## Specific Feedback for Revision

The product-strategist should make the following changes:

1. **Search-and-replace** all instances of "FX Remeasurement mode" in Section 5 (Acceptance Criteria) with neutral action language. There is no mode -- this is a standalone app.

2. **Fix the NFR-003 contradiction** -- remove the claim that in-memory job status is recoverable across restarts, or change it to "Job status is ephemeral and not persisted across restarts."

3. **Soften or remove NFR-002** (scalability) -- this is not an enterprise platform. A note like "inherits FastAPI's default concurrency handling" is sufficient.

4. **Remove the undefined "streaming mode" reference** from EC-003. Replace with "Accept and process normally; pandas handles this volume in memory."

5. **Remove or relocate** the adoption success metric (">=1 additional client within 2 months") -- it is not actionable by the build team.

6. **Clarify FR-020 (i18n)** -- state whether Spanish support is inherited from the CTR Mapper template or requires new work.

7. **Fix the double "a" typos** on lines 79 and 92.

8. **Add a note to FR-017** clarifying that async processing is for architectural consistency with the sister app, not because Phase 1 processing complexity requires it.

---

## Artifacts Reviewed
- `C:/workarea/maturity_analysis_report/docs/product-requirements.md`
- `C:/workarea/maturity_analysis_report/webapp/backend/app.py`
- `C:/workarea/maturity_analysis_report/webapp/backend/services/excel_processor.py`
- `C:/workarea/maturity_analysis_report/webapp/backend/services/formula_mapper.py`

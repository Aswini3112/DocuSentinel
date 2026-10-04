# DocuSentinel AI — Demo Data Conflict Index

> All documents are **SYNTHETIC** and created solely for demonstration purposes.
> No real companies, persons, contracts, or financial figures are represented.

---

## Documents Loaded

| File | Description |
|------|-------------|
| `Project_Contract.txt` | Original signed contract between NovaTech and Aurora |
| `Project_Status_Report.txt` | Q2 status report with scope change and revised figures |
| `Vendor_Agreement.txt` | Subcontractor agreement between Aurora and ByteForge |
| `Financial_Summary.txt` | Finance department's view of approved budgets |
| `Meeting_Notes.txt` | Steering committee notes — partial conflict resolution |

---

## Intentional Conflicts Built Into the Demo Data

### Conflict 1 — PROJECT DEADLINE (HIGH SEVERITY)
| Document | Value |
|----------|-------|
| Project_Contract.txt | **15 November 2026** |
| Project_Status_Report.txt | **30 November 2026** |
| Financial_Summary.txt | Recognizes only **15 November 2026** |
| Meeting_Notes.txt | References both; amendment NOT yet executed |

**Expected detection:** CONTRADICTING deadline fields across documents.

---

### Conflict 2 — TOTAL CONTRACT VALUE (HIGH SEVERITY)
| Document | Value |
|----------|-------|
| Project_Contract.txt | **USD 1,200,000** (original) |
| Project_Status_Report.txt | **USD 1,450,000** (revised) |
| Financial_Summary.txt | **USD 1,380,000** (board-approved) |
| Meeting_Notes.txt | Confirms **USD 1,380,000** as agreed |

**Expected detection:** Three different contract values across documents.

---

### Conflict 3 — LATE DELIVERY PENALTY CAP (HIGH SEVERITY)
| Document | Value |
|----------|-------|
| Project_Contract.txt | Max **USD 120,000** |
| Project_Status_Report.txt | Vendor proposes **USD 75,000** |
| Financial_Summary.txt | Reserves **USD 120,000** (original) |
| Meeting_Notes.txt | NovaTech rejected reduced cap — **USD 120,000** stands |

---

### Conflict 4 — LATE PAYMENT PENALTY RATE (MEDIUM SEVERITY)
| Document | Value |
|----------|-------|
| Project_Contract.txt | **2% per month** |
| Project_Status_Report.txt | **1.5% per month** |
| Meeting_Notes.txt | Confirms **2% per month** (status report was an error) |

---

### Conflict 5 — PROJECT MANAGER NAME (MEDIUM SEVERITY)
| Document | Value |
|----------|-------|
| Project_Contract.txt | **Mr. Arjun Mehta** |
| Project_Status_Report.txt | **Mr. Vikram Sharma** |
| Vendor_Agreement.txt | **Mr. Arjun Mehta** |
| Meeting_Notes.txt | Explains dual roles — Sharma is operational PM |

---

## Suggested Demo Questions

1. `"What is the project deadline?"`
   → Expected: CONFLICT — 15 Nov vs 30 Nov

2. `"What is the total contract value?"`
   → Expected: CONFLICT — three different values

3. `"What is the late delivery penalty?"`
   → Expected: Evidence found, USD 15,000/week, CONFLICT on cap

4. `"Who is the project manager?"`
   → Expected: CONFLICT — Arjun Mehta vs Vikram Sharma

5. `"What is the late payment penalty rate?"`
   → Expected: CONFLICT — 2% vs 1.5%

6. `"What modules are included in the project?"`
   → Expected: VERIFIED — consistent across documents

7. `"What is the governing law?"`
   → Expected: VERIFIED — India / Bangalore

8. `"What is the penalty for nuclear incidents?"`
   → Expected: NOT_FOUND / UNCERTAIN — not in any document

# CRM Lead Deduplication Script

A Python tool that detects duplicate lead records in CRM exports using a combination of exact matching and fuzzy string comparison. Outputs a confidence-scored report so your team can review and decide before anything gets merged or deleted.

---

## The Problem It Solves

Duplicate leads in a CRM are a common issue — they accumulate through imports, web forms, manual entry, and API integrations. This script processes a CSV export of your leads and flags potential duplicates without touching the original data, giving you a prioritized list to work through.

---

## How It Works

Three levels of matching, in order of confidence:

| Signal | Confidence | Notes |
|--------|------------|-------|
| Identical email address | HIGH | Most reliable deduplication signal |
| Identical phone number | HIGH | Normalized before comparison (strips formatting) |
| Same email domain + fuzzy company name | MEDIUM | Excludes generic domains (gmail, yahoo, etc.) |
| Fuzzy company name only | LOW | Uses token sort ratio to catch word order variations |

Fuzzy matching uses `rapidfuzz` with a configurable threshold (default: 85). This means "Faulu Microfinance Bank" and "Faulu Microfinance Bank Ltd" will match, but "Faulu" and "Faulu Solutions" may not depending on your threshold setting.

---

## Tech Stack

- **Python 3.8+**
- **rapidfuzz** — fast fuzzy string matching
- **csv / json** — data I/O

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/lead-deduplicator.git
cd lead-deduplicator
pip install -r requirements.txt
```

---

## Usage

**Run with your CRM export:**
```bash
python deduplicate.py your_leads.csv
```

**Adjust the fuzzy match threshold (0-100):**
```bash
python deduplicate.py your_leads.csv 90
```

**Run with sample data:**
```bash
python deduplicate.py
```

---

## Expected CSV Format

| id | name | email | phone | company |
|----|------|-------|-------|---------|
| L001 | James Ochieng | james@faulumicrofinance.co.ke | +254712345678 | Faulu Microfinance Bank |

Common column name variations are handled automatically.

---

## Output

Console summary:
```
===== DUPLICATE DETECTION RESULTS =====

Total pairs flagged: 4
  HIGH confidence:   2
  MEDIUM confidence: 1
  LOW confidence:    1

Top matches:
  [HIGH] James Ochieng <-> James Ochieng
         Reason: Identical email: james@faulumicrofinance.co.ke

  [MEDIUM] Sarah Wanjiku <-> S. Wanjiku
         Reason: Same email domain (techstart.io) + similar company name (score: 91)
```

Two output files: `duplicate_report.json` and `duplicate_report.csv`

---

## Important

This tool only **identifies** duplicates. It does not merge or delete any records. All decisions are left to the user after reviewing the report.

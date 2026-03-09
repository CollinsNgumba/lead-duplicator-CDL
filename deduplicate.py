"""
CRM Lead Deduplication Script
Detects duplicate lead records in CRM exports using exact and fuzzy matching.
Outputs a confidence-scored report for manual review before any records are touched.
"""

import csv
import json
import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from rapidfuzz import fuzz


@dataclass
class Lead:
    id: str
    name: str
    email: str
    phone: str
    company: str
    domain: str = field(default="")

    def __post_init__(self):
        self.email = self.email.strip().lower()
        self.phone = re.sub(r"\D", "", self.phone)
        self.company = self.company.strip()
        self.name = self.name.strip()
        if not self.domain and "@" in self.email:
            self.domain = self.email.split("@")[-1]


@dataclass
class DuplicatePair:
    lead_a_id: str
    lead_a_name: str
    lead_b_id: str
    lead_b_name: str
    match_reason: str
    confidence: str   # HIGH / MEDIUM / LOW
    score: int


def load_leads_from_csv(filepath: str) -> List[Lead]:
    """Load leads from a CSV export file."""
    leads = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lead = Lead(
                    id=row.get("id", row.get("lead_id", "")),
                    name=row.get("name", row.get("contact_name", "")),
                    email=row.get("email", ""),
                    phone=row.get("phone", row.get("phone_number", "")),
                    company=row.get("company", row.get("company_name", ""))
                )
                leads.append(lead)
            except Exception as e:
                print(f"Skipping row due to error: {e}")
    return leads


def find_duplicates(leads: List[Lead], fuzzy_threshold: int = 85) -> List[DuplicatePair]:
    """
    Compare all lead pairs and identify duplicates using:
      - Exact email match       -> HIGH confidence
      - Exact phone match       -> HIGH confidence
      - Same email domain + fuzzy company name -> MEDIUM confidence
      - Fuzzy company name only -> LOW confidence (if above threshold)
    """
    pairs = []
    seen = set()

    for i, a in enumerate(leads):
        for j, b in enumerate(leads):
            if i >= j:
                continue

            pair_key = tuple(sorted([a.id, b.id]))
            if pair_key in seen:
                continue

            match_reason = None
            confidence = None
            score = 0

            # Exact email match
            if a.email and b.email and a.email == b.email:
                match_reason = f"Identical email: {a.email}"
                confidence = "HIGH"
                score = 100

            # Exact phone match
            elif a.phone and b.phone and len(a.phone) >= 7 and a.phone == b.phone:
                match_reason = f"Identical phone: {a.phone}"
                confidence = "HIGH"
                score = 100

            # Same domain + fuzzy company name
            elif (
                a.domain and b.domain and a.domain == b.domain and
                a.domain not in ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com")
            ):
                company_score = fuzz.token_sort_ratio(
                    a.company.lower(), b.company.lower()
                )
                if company_score >= fuzzy_threshold:
                    match_reason = (
                        f"Same email domain ({a.domain}) + "
                        f"similar company name (score: {company_score})"
                    )
                    confidence = "MEDIUM"
                    score = company_score

            # Fuzzy company name only
            else:
                company_score = fuzz.token_sort_ratio(
                    a.company.lower(), b.company.lower()
                )
                if company_score >= fuzzy_threshold and a.company:
                    match_reason = f"Similar company name (score: {company_score})"
                    confidence = "LOW"
                    score = company_score

            if match_reason:
                seen.add(pair_key)
                pairs.append(DuplicatePair(
                    lead_a_id=a.id,
                    lead_a_name=a.name,
                    lead_b_id=b.id,
                    lead_b_name=b.name,
                    match_reason=match_reason,
                    confidence=confidence,
                    score=score
                ))

    # Sort by confidence then score
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    pairs.sort(key=lambda p: (order[p.confidence], -p.score))
    return pairs


def save_report(pairs: List[DuplicatePair], path: str = "duplicate_report.json"):
    """Save duplicate pairs to a JSON report file."""
    report = {
        "total_duplicate_pairs": len(pairs),
        "high_confidence": sum(1 for p in pairs if p.confidence == "HIGH"),
        "medium_confidence": sum(1 for p in pairs if p.confidence == "MEDIUM"),
        "low_confidence": sum(1 for p in pairs if p.confidence == "LOW"),
        "pairs": [asdict(p) for p in pairs]
    }
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {path}")


def save_csv_report(pairs: List[DuplicatePair], path: str = "duplicate_report.csv"):
    """Save duplicate pairs to CSV for easy review in spreadsheet tools."""
    if not pairs:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=asdict(pairs[0]).keys())
        writer.writeheader()
        for p in pairs:
            writer.writerow(asdict(p))
    print(f"CSV report saved to {path}")


def print_summary(pairs: List[DuplicatePair]):
    print("\n===== DUPLICATE DETECTION RESULTS =====\n")
    print(f"Total pairs flagged: {len(pairs)}")
    print(f"  HIGH confidence:   {sum(1 for p in pairs if p.confidence == 'HIGH')}")
    print(f"  MEDIUM confidence: {sum(1 for p in pairs if p.confidence == 'MEDIUM')}")
    print(f"  LOW confidence:    {sum(1 for p in pairs if p.confidence == 'LOW')}")
    print("\nTop matches:")
    for p in pairs[:10]:
        print(f"  [{p.confidence}] {p.lead_a_name} <-> {p.lead_b_name}")
        print(f"         Reason: {p.match_reason}\n")
    print("========================================\n")


def _generate_sample_csv(path: str = "sample_leads.csv") -> str:
    """Generate sample CRM lead data for testing."""
    rows = [
        {"id": "L001", "name": "James Ochieng", "email": "james@faulumicrofinance.co.ke", "phone": "+254712345678", "company": "Faulu Microfinance Bank"},
        {"id": "L002", "name": "James Ochieng", "email": "james@faulumicrofinance.co.ke", "phone": "+254712345678", "company": "Faulu Microfinance Bank"},
        {"id": "L003", "name": "Sarah Wanjiku", "email": "sarah@techstart.io", "phone": "+254798765432", "company": "TechStart Ltd"},
        {"id": "L004", "name": "S. Wanjiku", "email": "swanjiku@techstart.io", "phone": "+254798765432", "company": "TechStart Limited"},
        {"id": "L005", "name": "David Kamau", "email": "dkamau@gmail.com", "phone": "+254700111222", "company": "FinCore"},
        {"id": "L006", "name": "David K.", "email": "david@fincore.co", "phone": "+254700111222", "company": "FinCore Kenya"},
        {"id": "L007", "name": "Alice Mwangi", "email": "alice@novacorp.com", "phone": "+254733999888", "company": "Nova Corp"},
        {"id": "L008", "name": "Bob Njoroge", "email": "bob@payflow.com", "phone": "+254755444333", "company": "PayFlow Inc"},
        {"id": "L009", "name": "Carol Akinyi", "email": "carol@unique.com", "phone": "+254766777666", "company": "Unique Solutions"},
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return path


if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else _generate_sample_csv()
    threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 85

    print(f"Loading leads from: {csv_path}")
    leads = load_leads_from_csv(csv_path)
    print(f"Loaded {len(leads)} lead records.")

    pairs = find_duplicates(leads, fuzzy_threshold=threshold)
    print_summary(pairs)
    save_report(pairs)
    save_csv_report(pairs)

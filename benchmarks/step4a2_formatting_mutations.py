"""
Step 4A.2 — formatting/normalization mutations of 10 semantic cases from
step4a2_heldout_corpus.py. These are NOT counted toward the 100+ semantic
diversity minimum (per Section 21) — reported separately in the final
report. Ground truth for each mutation is IDENTICAL to its base_id's
ground truth (the mutation changes only surface formatting, never
semantic content), locked in before execution, same as the main corpus.
"""
from benchmarks.step4a2_heldout_corpus import _c, CASES as _BASE_CASES

_by_id = {c["id"]: c for c in _BASE_CASES}

MUT_CASES = []


def _mut(base_id, mut_suffix, text, kwargs=None):
    base = _by_id[base_id]
    MUT_CASES.append({
        "id": f"{base_id}-FMT-{mut_suffix}",
        "adapter": base["adapter"],
        "family": "fmt",
        "text": text,
        "kwargs": kwargs if kwargs is not None else base["kwargs"],
        "gt": base["gt"],
        "base_id": base_id,
    })


# 1. Heading removed
_mut("LOL-K2-01", "no-heading",
     "A limit of 1 times the annual fees paid shall apply to Provider's aggregate liability under this "
     "Agreement.")

# 2. Capitalization changed (all-caps clause)
_mut("LOL-K2-04", "allcaps",
     "9. LIMITATION OF LIABILITY.\nPROVIDER'S AGGREGATE LIABILITY UNDER THIS AGREEMENT SHALL NOT EXCEED $1,000,000.")

# 3. Extra line breaks / whitespace inserted
_mut("INDEM-O2-03", "linebreaks",
     "1.   Definitions.\n\n\n'Licensor'   means   the   entity   granting   a   license   to   the   "
     "Platform;\n\n'Licensee'   means   the   entity   using   the   Platform   under   license   from   "
     "Licensor.\n\n\n8.   Indemnification.\n\nLicensor   shall   indemnify,   defend,   and   hold   "
     "harmless   Licensee   from   and   against   any   third-party   IP   infringement   claims   "
     "arising   from   the   Platform,   up   to   a   cap   of   3   times   the   fees   paid.")

# 4. Numbered-list restructuring
_mut("PAY-N2-14", "numbered-list",
     "1. Definitions.\n"
     "   1.1 'Purchaser' means the entity that purchases the goods.\n"
     "   1.2 'Vendor' means the entity that manufactures and sells the goods to Purchaser.\n\n"
     "6. Payment Terms.\n"
     "   6.1 Purchaser shall pay Vendor in United States Dollars.\n"
     "   6.2 Payment is due within Net 45 days of delivery.")

# 5. Bullet-like normalized text
_mut("LOL-G2-04", "bullets",
     "9. Limitation of Liability.\n"
     "- In no event shall Provider's aggregate liability under this Agreement exceed $3,000,000\n"
     "- This is exclusive of and in addition to amounts recoverable under Provider's general liability "
     "insurance policy maintained with limits of $5,000,000")

# 6. Semicolon restructuring
_mut("INDEM-O2-04", "semicolons",
     "8. Indemnification. The parties shall mutually indemnify each other from and against third-party "
     "claims; arising from each party's own gross negligence; up to a cap equal to 1 times the fees paid "
     "for each party.")

# 7. Long paragraph (definitions inline, no section breaks)
_mut("PAY-A2-02", "long-paragraph",
     "This Master Subscription Agreement is entered into between the parties identified below, and for "
     "purposes of this Agreement 'Customer' is understood to mean Initech LLC, the entity that develops "
     "and licenses the Deliverables into the resale channel, and 'Vendor' is understood to mean Umbrella "
     "Corp, the reseller entity that purchases and pays for the Deliverables from Customer for resale to "
     "end users, and the parties further agree that Vendor shall be responsible for all sales, use, and "
     "value-added taxes arising from this Agreement, in addition to the other terms set forth herein.")

# 8. Section title changed (unusual heading)
_mut("LOL-H2-01", "unusual-title",
     "6. Risk and Remedies. Notwithstanding the service credits described in Section 6 (SLA), which shall "
     "not exceed $50,000 in any month, Provider's aggregate liability under this Agreement shall not "
     "exceed 2 times the annual fees paid.")

# 9. Quoted defined terms with curly quotes and extra punctuation
_mut("INDEM-C2-01", "curly-quotes",
     "1. Definitions. “Reseller” means Beta Inc., the entity that purchases the Deliverables "
     "from Provider for resale, subject to the Service Provider’s separate implementation terms.\n\n"
     "8. Indemnification. Provider shall indemnify, defend, and hold harmless Reseller from and against "
     "any third-party claims arising from Provider's gross negligence, up to a cap of 2 times the fees "
     "paid.")

# 10. Table-like normalized text (columns collapsed to rows, as a PDF table extraction might normalize)
_mut("LOL-J2-03", "table-normalized",
     "Schedule H: Commercial Terms.\n"
     "Item | Description | Amount\n"
     "(a) | Purchase price | $500,000\n"
     "(b) | Insurance requirement | $2,000,000\n"
     "(c) | Liability cap | 3 times the annual fees paid\n"
     "(d) | SLA credit pool | $75,000\n\n"
     "9. Limitation of Liability. Provider's aggregate liability shall be as set forth in Schedule H.")


assert len(MUT_CASES) == 10, f"expected 10 formatting mutations, got {len(MUT_CASES)}"

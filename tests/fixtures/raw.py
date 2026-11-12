"""Synthetic raw records with the exact shapes seen in the schema report of 10 Nov 2026.
Values are invented (drug ids are real ingredient rxcuis; product rxcuis are made up)."""
import random

IBU, NAP, APAP, AMOX = "5640", "7258", "161", "723"
# product rxcui -> ingredient
PRODUCTS = {"197805": IBU, "197806": IBU, "198013": NAP, "198014": NAP, "198440": APAP, "308191": AMOX}
NAMES = {"IBUPROFEN": IBU, "NAPROXEN": NAP, "ACETAMINOPHEN": APAP, "AMOXICILLIN": AMOX}
ING_NAMES = {IBU: "IBUPROFEN", NAP: "NAPROXEN", APAP: "ACETAMINOPHEN", AMOX: "AMOXICILLIN"}


def _drug(name, role, rxcui=None, substance=None):
    d = {"drugcharacterization": role, "medicinalproduct": name, "drugadministrationroute": "048",
         "drugindication": "Pain", "activesubstance": {"activesubstancename": substance or name}}
    d["openfda"] = {"rxcui": [rxcui], "generic_name": [name]} if rxcui else {}
    return d


def faers(i, month, drugs, reactions, version="1", sex="2", age="45", unit="801", serious="1"):
    return {
        "safetyreportid": f"1000{i:04d}", "safetyreportversion": version, "receivedate": f"2026{month:02d}15",
        "receiptdate": f"2026{month:02d}10", "transmissiondate": f"2026{month:02d}20", "reporttype": "1",
        "serious": serious, "seriousnessdeath": "2", "seriousnesshospitalization": "1", "occurcountry": "US",
        "primarysource": {"qualification": "5", "reportercountry": "US"},
        "patient": {"patientsex": sex, "patientonsetage": age, "patientonsetageunit": unit,
                    "reaction": [{"reactionmeddrapt": r, "reactionoutcome": "6"} for r in reactions],
                    "drug": drugs},
    }


def build_reports() -> list[dict]:
    """Q1 (months 1-3) and Q2 (months 4-6). Ibuprofen + gastrointestinal haemorrhage is a strong, growing signal."""
    rng = random.Random(7)
    out, n = [], 0
    other_reactions = ["NAUSEA", "Rash", "HEADACHE", "DIZZINESS", "DRUG INEFFECTIVE"]
    for _quarter, months, ibu_gi in (("Q1", (1, 2, 3), 12), ("Q2", (4, 5, 6), 20)):
        # 40 ibuprofen reports, ibu_gi of them with the signal reaction (half harmonised, half name only)
        for k in range(40):
            n += 1
            rx = "197805" if k % 2 == 0 else None
            reactions = ["Gastrointestinal haemorrhage"] if k < ibu_gi else [rng.choice(other_reactions)]
            if k == 0:
                reactions.append("DRUG INEFFECTIVE")
            out.append(faers(n, months[k % 3], [_drug("IBUPROFEN", "1", rx)] + (
                [_drug("PARACETAMOL^S SOMETHING", "2")] if k % 7 == 0 else []), reactions,
                age=str(20 + k), sex="1" if k % 3 else "2"))
        # 160 reports of other drugs, only 4 with the signal reaction
        for k in range(160):
            n += 1
            name = ["NAPROXEN", "ACETAMINOPHEN", "AMOXICILLIN", "NAPROXEN"][k % 4]
            rxc = {"NAPROXEN": "198013", "ACETAMINOPHEN": "198440", "AMOXICILLIN": None}[name] if k % 2 == 0 else None
            reactions = ["Gastrointestinal haemorrhage"] if k < 4 else [rng.choice(other_reactions)]
            out.append(faers(n, months[k % 3], [_drug(name, "1", rxc)], reactions, age=str(60 + (k % 30))))
    # a junk-named drug, a second version of a case, and a report with weird quirks
    out.append(faers(900, 2, [_drug("UNSPECIFIED INGREDIENT", "1")], ["NAUSEA"]))
    out.append(faers(1, 1, [_drug("IBUPROFEN", "1", "197805")], ["NAUSEA"], version="1"))
    out.append(faers(1, 1, [_drug("IBUPROFEN", "1", "197805")], ["NAUSEA"], version="2"))
    return out


def ndc_products() -> list[dict]:
    def prod(ndc, generic, labeler, form, route, rxcui, ingredient, pkg):
        return {"product_ndc": ndc, "generic_name": generic, "labeler_name": labeler, "brand_name": generic.title(),
                "active_ingredients": [{"name": ingredient, "strength": "400 mg/1"}], "finished": True,
                "packaging": [{"package_ndc": pkg, "description": "100 TABLET in 1 BOTTLE", "marketing_start_date": "20150101",
                               "sample": False}],
                "openfda": {"rxcui": [rxcui], "spl_set_id": [f"{ndc.replace('-', '')}0000-0000-4000-8000-000000000000"[:36]]},
                "marketing_category": "ANDA", "dosage_form": form, "spl_id": "36ac182a-ff48-50a9-e063-6394a90aa917",
                "product_type": "HUMAN PRESCRIPTION DRUG", "route": [route], "marketing_start_date": "20150101",
                "application_number": "ANDA076655"}
    return [
        prod("71288-722", "Ibuprofen", "Meitheal", "TABLET", "ORAL", "197805", "IBUPROFEN", "71288-722-32"),
        prod("50090-0481", "Ibuprofen", "A-S Medication", "TABLET", "ORAL", "197806", "IBUPROFEN", "50090-0481-0"),
        prod("0338-0049", "Naproxen", "Baxter", "TABLET", "ORAL", "198013", "NAPROXEN", "0338-0049-01"),
        prod("76420-241", "Naproxen", "Asclemed", "TABLET", "ORAL", "198014", "NAPROXEN", "76420-241-12"),
        prod("12345-678", "Acetaminophen", "Acme", "TABLET", "ORAL", "198440", "ACETAMINOPHEN", "12345-678-01"),
    ]


def shortages() -> list[dict]:
    def rec(pkg, generic, status, availability, form, rxcui, route="ORAL"):
        return {"update_type": "New", "initial_posting_date": "07/14/2023", "package_ndc": pkg, "generic_name": generic,
                "contact_info": "800-000-0000", "availability": availability, "update_date": "11/03/2026",
                "therapeutic_category": ["Pain"], "dosage_form": form, "presentation": f"{generic}, 400 mg",
                "company_name": "Acme", "status": status, "shortage_reason": "Demand increase for the drug",
                "openfda": {"rxcui": [rxcui], "route": [route]}}
    return [
        rec("0338-0049-01", "Naproxen Tablet", "Current", "Unvailable", "Tablet", "198013"),   # typo as in the data
        rec("76420-241-12", "Naproxen Tablet", "Resolved", "Available", "Tablet", "198014"),
        {**rec("99999-111-22", "Mystery Tablet", "To Be Discontinued", None, "Tablet", "000000"), "availability": ""},
    ]


def labels() -> list[dict]:
    return [
        {"set_id": "AAAAAAAA-0000-4000-8000-000000000001", "id": "11111111-0000-4000-8000-000000000001", "version": "3",
         "effective_time": "20260706", "openfda": {"product_type": ["HUMAN PRESCRIPTION DRUG"], "rxcui": ["197805"],
                                                    "product_ndc": ["71288-722"]},
         "indications_and_usage": ["1 INDICATIONS AND USAGE Ibuprofen is indicated for relief of mild to moderate pain."],
         "adverse_reactions": ["6 ADVERSE REACTIONS Nausea, rash, headache and dizziness were reported."],
         "warnings_and_cautions": ["5 WARNINGS AND PRECAUTIONS Gastrointestinal bleeding, ulceration and perforation."],
         "boxed_warning": ["WARNING: CARDIOVASCULAR AND GASTROINTESTINAL RISK"],
         "adverse_reactions_table": ["<table><tr><td>x</td></tr></table>"]},
        {"set_id": "BBBBBBBB-0000-4000-8000-000000000002", "id": "22222222-0000-4000-8000-000000000002", "version": "1",
         "effective_time": "20250101", "openfda": {"product_type": ["HUMAN OTC DRUG"], "rxcui": ["198440"]},
         "warnings": ["Warnings Liver warning: this product contains acetaminophen."], "purpose": ["Pain reliever"]},
    ]


def recalls() -> list[dict]:
    return [
        {"recall_number": "D-0115-2026", "event_id": "80601", "status": "Ongoing", "classification": "Class II",
         "reason_for_recall": "Microbial contamination", "product_description": "Naproxen Tablets, 500 mg, 100 count",
         "recalling_firm": "Acme", "recall_initiation_date": "20260105", "report_date": "20260115", "termination_date": "",
         "city": "Peoria", "state": "IL", "address_2": "N/A", "openfda": {"rxcui": ["198013"]}},
        {"recall_number": "D-0116-2026", "event_id": "80602", "status": "Terminated", "classification": "Class I",
         "reason_for_recall": "Lack of assurance of sterility", "product_description": "Semaglutide Injection, 2.5 mg/mL",
         "recalling_firm": "Compounder", "recall_initiation_date": "20260106", "report_date": "20260116",
         "termination_date": "20260301", "openfda": {}},
    ]

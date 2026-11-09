"""
MedSignal - data source smoke test (v2: new APIs + cross-source demos).

Run all default sections:      python test.py
Run only some sections:        python test.py 11 12 16
Heavy quarterly PRR trend:     python test.py 20      (not in default run)

Needs: pip install requests python-dotenv
Optional: OPENFDA_API_KEY in .env (free, https://open.fda.gov/apis/authentication/)
Sections 1-10: original checks. 11-15: new APIs. 16-20: cross-source demos.
"""
import os, sys, math, time, urllib.parse
import requests
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("OPENFDA_API_KEY")
FDA = "https://api.fda.gov"
RX = "https://rxnav.nlm.nih.gov/REST"
DM = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
PUBMED = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
CTGOV = "https://clinicaltrials.gov/api/v2/studies"

DRUG, REACTION = "ibuprofen", "GASTROINTESTINAL HAEMORRHAGE"
SLICE = "receivedate:[20240101 TO 20260930]"
N_SAMPLE = 50
LIMIT = 1000 if KEY else 100
# Reaction terms that are reporting noise, not drug-specific safety signals
NOISE = {"DRUG INEFFECTIVE", "OFF LABEL USE", "PRODUCT USE IN UNAPPROVED INDICATION",
         "DRUG INTERACTION", "PRODUCT DOSE OMISSION ISSUE", "INAPPROPRIATE SCHEDULE OF PRODUCT ADMINISTRATION",
         "INTENTIONAL PRODUCT USE ISSUE", "PRODUCT USE ISSUE", "NO ADVERSE EVENT", "DEATH",
         "MALAISE", "FATIGUE", "PAIN", "ASTHENIA"}

ONLY = {a for a in sys.argv[1:]}
def on(n):
    return (str(n) in ONLY) if ONLY else n < 20

if not KEY:
    print("WARNING: no OPENFDA_API_KEY set -> using limit=100. Get a free key.")

SAFE = "+:[]\"_.-"


def url(endpoint, **kw):
    """Build openFDA URL by hand: openFDA wants '+' for spaces."""
    parts = [f"{k}={urllib.parse.quote(str(v).replace(' ', '+'), safe=SAFE)}" for k, v in kw.items()]
    if KEY:
        parts.append(f"api_key={KEY}")
    return f"{FDA}{endpoint}?" + "&".join(parts)


def get(u, timeout=120):
    t = time.time()
    try:
        r = requests.get(u, timeout=timeout)
        dt = round(time.time() - t, 2)
        try:
            return r.status_code, r.json(), dt
        except ValueError:
            return r.status_code, r.text[:200], dt
    except requests.RequestException as e:
        return 0, str(e), 0


def fetch(u, tries=3):
    """GET with retries (DailyMed sometimes drops the connection)."""
    for i in range(tries):
        try:
            return requests.get(u, timeout=60)
        except requests.RequestException as e:
            print(f"   retry {i+1}/{tries} for ...{u[-50:]}: {type(e).__name__}")
            time.sleep(2 * (i + 1))
    return None


def jget(u):
    """Generic JSON GET for non-openFDA APIs -> (status, json|None)."""
    r = fetch(u)
    if r is None:
        return 0, None
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, None


def total(endpoint, search):
    sc, d, _ = get(url(endpoint, search=search, limit=1))
    return d["meta"]["results"]["total"] if sc == 200 else None


def counts(endpoint, search, field, limit=10):
    sc, d, _ = get(url(endpoint, search=search, count=field, limit=limit))
    return d.get("results", []) if sc == 200 else []


def prr_stats(a, b, c, d):
    """PRR, 95% CI lower bound, chi-square, and Evans criteria flag."""
    if not (a and c):
        return None
    prr = (a / (a + b)) / (c / (c + d))
    se = math.sqrt(1 / a - 1 / (a + b) + 1 / c - 1 / (c + d))
    lo = math.exp(math.log(prr) - 1.96 * se)
    n = a + b + c + d
    chi2 = n * (a * d - b * c) ** 2 / ((a + b) * (c + d) * (a + c) * (b + d))
    return {"prr": prr, "ci_low": lo, "chi2": chi2, "signal": prr >= 2 and chi2 >= 4 and a >= 3}


def two_by_two(slice_, drug, reaction):
    dq = f'patient.drug.openfda.generic_name:"{drug}"'
    rq = f'patient.reaction.reactionmeddrapt:"{reaction}"'
    n_all = total("/drug/event.json", slice_)
    n_drug = total("/drug/event.json", f"{slice_} AND {dq}")
    n_react = total("/drug/event.json", f"{slice_} AND {rq}")
    a = total("/drug/event.json", f"{slice_} AND {dq} AND {rq}")
    if None in (n_all, n_drug, n_react, a):
        return None
    return a, n_drug - a, n_react - a, n_all - n_drug - (n_react - a)


def shortage_count(name, status="Current"):
    """Shortage records for a generic name. Field name differs by record, so try both."""
    for f in ("openfda.generic_name", "generic_name"):
        n = total("/drug/shortages.json", f'{f}:"{name}" AND status:"{status}"')
        if n:
            return n
    return 0


def rxcui_of(name):
    sc, d = jget(f"{RX}/rxcui.json?name={urllib.parse.quote(name)}")
    ids = (d or {}).get("idGroup", {}).get("rxnormId", [])
    return ids[0] if ids else None


def head(t):
    print(f"\n=== {t} ===")


# ---------------------------------------------------------------- ORIGINAL 1-10
if on(1):
    head("1. FAERS /drug/event - slice size and paging")
    sc, d, dt = get(url("/drug/event.json", search=SLICE, limit=LIMIT))
    if sc == 200:
        print(f"slice total reports: {d['meta']['results']['total']:,} | page of {len(d['results'])} in {dt}s")
    else:
        print("FAILED", sc, d)

if on(2):
    head(f"2. PRR cross-check for {DRUG} / {REACTION}")
    t = two_by_two(SLICE, DRUG, REACTION)
    if t:
        a, b, c, dd = t
        s = prr_stats(a, b, c, dd)
        print(f"a={a} b={b} c={c} d={dd}")
        print(f"PRR={s['prr']:.2f}  95%CI lower={s['ci_low']:.2f}  chi2={s['chi2']:.0f}  "
              f"Evans signal={s['signal']}")
    else:
        print("one of the counts failed (check drug/reaction spelling)")

if on(3):
    head(f"3. Top reactions for {DRUG} (count query)")
    dq = f'patient.drug.openfda.generic_name:"{DRUG}"'
    print(counts("/drug/event.json", f"{SLICE} AND {dq}", "patient.reaction.reactionmeddrapt.exact", 5))

if on(4):
    head("4. How many drug entries carry openfda harmonized fields?")
    sc, d, _ = get(url("/drug/event.json", search=SLICE, limit=LIMIT))
    if sc == 200:
        drugs = [x for r in d["results"] for x in r["patient"].get("drug", [])]
        with_h = [x for x in drugs if x.get("openfda")]
        with_rx = [x for x in drugs if x.get("openfda", {}).get("rxcui")]
        print(f"{len(drugs)} drug entries | harmonized: {len(with_h)/len(drugs):.0%} | with rxcui: {len(with_rx)/len(drugs):.0%}")
    else:
        print("FAILED", sc, d)

if on(5):
    head("5. Shortages -> NDC directory join")
    sc, d, _ = get(url("/drug/shortages.json", count="status"))
    print("status values:", d.get("results") if sc == 200 else (sc, d))
    sc, d, _ = get(url("/drug/shortages.json", limit=N_SAMPLE))
    hit = 0
    if sc == 200:
        for rec in d["results"]:
            ndc = rec.get("package_ndc")
            if not ndc:
                continue
            s2, d2, _ = get(url("/drug/ndc.json", search=f'packaging.package_ndc:"{ndc}"', limit=1))
            hit += s2 == 200 and bool(d2.get("results"))
            time.sleep(0.3)
        print(f"{hit}/{len(d['results'])} shortage package_ndc found in NDC directory")

if on(6):
    head("6. Recalls - how often is the openfda block empty?")
    sc, d, _ = get(url("/drug/enforcement.json", limit=100))
    if sc == 200:
        empty = sum(1 for r in d["results"] if not r.get("openfda"))
        print(f"{empty}/{len(d['results'])} recalls without harmonized fields (need text matching)")

if on(7):
    head("7. Labels usable for label-gap feature")
    rx = 'openfda.product_type:"HUMAN PRESCRIPTION DRUG"'
    print("Rx labels:", total("/drug/label.json", rx))
    print("Rx labels with adverse_reactions:", total("/drug/label.json", f"{rx} AND _exists_:adverse_reactions"))

if on(8):
    head("8. RxNav normalization")
    for path in (f"/rxcui.json?name={DRUG}", "/approximateTerm.json?term=ibuprofn&maxEntries=3"):
        sc, d, dt = get(RX + path)
        print(f"[{sc}] {path} ({dt}s) ->", str(d)[:160])

if on(9):
    head("9. Bulk download manifest")
    sc, d, _ = get(f"{FDA}/download.json")
    if sc == 200:
        try:
            parts = d["results"]["drug"]["event"]["partitions"]
            mb = sum(float(p.get("size_mb", 0)) for p in parts)
            recs = sum(int(p.get("records", 0)) for p in parts)
            print(f"{len(parts)} files | {mb:,.0f} MB zipped | {recs:,} records")
            by_q = {}
            for p in parts:
                q = p["file"].split("/")[-2]
                m = by_q.setdefault(q, [0.0, 0])
                m[0] += float(p.get("size_mb", 0))
                m[1] += int(p.get("records", 0))
            print("most recent quarters:")
            for q in sorted(by_q)[-8:]:
                print(f"  {q}: {by_q[q][0]:,.0f} MB zipped, {by_q[q][1]:,} reports")
        except (KeyError, TypeError):
            print("manifest structure differs; top-level keys:", list(d.get("results", {}).keys()))
    else:
        print("FAILED", sc, d)

if on(10):
    head("10. DailyMed join (openFDA spl_set_id -> DailyMed SPL XML)")
    r = fetch(f"{DM}/spls.json?pagesize=1")
    if r is not None and r.ok:
        print("DailyMed list endpoint:", r.status_code, r.json().get("metadata"))
    sc, d, _ = get(url("/drug/ndc.json", search='product_type:"HUMAN PRESCRIPTION DRUG"', limit=20))
    if sc == 200:
        ids = [x["openfda"]["spl_set_id"][0] for x in d["results"] if x.get("openfda", {}).get("spl_set_id")]
        ok, sizes, first = 0, [], None
        for sid in ids:
            r = fetch(f"{DM}/spls/{sid}.xml")
            if r is not None and r.status_code == 200:
                ok += 1
                sizes.append(len(r.content))
                first = first or r
            time.sleep(0.5)
        print(f"{ok}/{len(ids)} openFDA spl_set_id found in DailyMed")
        if sizes:
            print(f"XML size per label: avg {sum(sizes)/len(sizes)/1024:,.0f} KB, max {max(sizes)/1024:,.0f} KB")
            print("first label mentions ADVERSE REACTIONS:", "ADVERSE REACTIONS" in first.text.upper())

# ---------------------------------------------------------------- NEW APIs 11-15
if on(11):
    head("11. Drugs@FDA (/drug/drugsfda) - approvals, sponsors, marketing status")
    q = f'openfda.generic_name:"{DRUG}"'
    print("applications:", total("/drug/drugsfda.json", q))
    print("marketing status:", counts("/drug/drugsfda.json", q, "products.marketing_status.exact", 5))
    print("top sponsors:", counts("/drug/drugsfda.json", q, "sponsor_name.exact", 5))
    # Use: distinguish Rx/OTC/discontinued products when proposing substitutes (FR7)

if on(12):
    head("12. RxNav relations + RxClass (ingredient, ATC class, class members, NDCs)")
    rx = rxcui_of(DRUG)
    print("rxcui:", rx)
    sc, d = jget(f"{RX}/rxcui/{rx}/related.json?tty=IN+BN")
    groups = (d or {}).get("relatedGroup", {}).get("conceptGroup", [])
    for g in groups:
        names = [c["name"] for c in g.get("conceptProperties", [])][:5]
        print(f"  related {g.get('tty')}: {names}")
    sc, d = jget(f"{RX}/rxclass/class/byRxcui.json?rxcui={rx}&relaSource=ATC")
    classes = (d or {}).get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
    seen = {}
    for c in classes:
        m = c["rxclassMinConceptItem"]
        seen[m["classId"]] = m["className"]
    print("ATC classes:", seen)
    for cid in list(seen)[:1]:
        sc, d = jget(f"{RX}/rxclass/classMembers.json?classId={cid}&relaSource=ATC")
        mem = (d or {}).get("drugMemberGroup", {}).get("drugMember", [])
        names = sorted({m["minConcept"]["name"] for m in mem if m["minConcept"].get("tty") == "IN"})
        print(f"  members of {cid}: {len(names)} ingredients, e.g. {names[:8]}")
    sc, d = jget(f"{RX}/rxcui/{rx}/ndcs.json")
    ndcs = (d or {}).get("ndcGroup", {}).get("ndcList", {}).get("ndc", [])
    print(f"NDCs linked to rxcui {rx}: {len(ndcs)}")
    print("NOTE: the RxNav drug-interaction API was retired by NLM in 2024 -> compute interactions from FAERS.")

if on(13):
    head("13. DailyMed extra endpoints (drug classes, NDCs/packaging of a set id, rxcuis)")
    for path in ("/drugclasses.json?pagesize=3", "/rxcuis.json?pagesize=3",
                 f"/spls.json?drug_name={DRUG}&pagesize=2"):
        sc, d = jget(DM + path)
        print(f"[{sc}] {path} ->", str(d)[:200] if d else None)
    sc, d = jget(f"{DM}/spls.json?drug_name={DRUG}&pagesize=1")
    try:
        sid = d["data"][0]["setid"]
        for sub in ("ndcs", "packaging", "history"):
            s2, d2 = jget(f"{DM}/spls/{sid}/{sub}.json")
            print(f"[{s2}] /spls/{sid}/{sub}.json ->", str(d2)[:150] if d2 else None)
    except (KeyError, IndexError, TypeError):
        print("could not get a set id")

if on(14):
    head("14. openFDA label sections available beyond adverse_reactions")
    rx = 'openfda.product_type:"HUMAN PRESCRIPTION DRUG"'
    for sec in ("boxed_warning", "contraindications", "drug_interactions", "warnings",
                "indications_and_usage", "pediatric_use", "pregnancy"):
        print(f"  {sec:22s}", total("/drug/label.json", f"{rx} AND _exists_:{sec}"))

if on(15):
    head("15. External validation: PubMed + ClinicalTrials.gov")
    term = f'{DRUG} AND "gastrointestinal hemorrhage"'
    sc, d = jget(f"{PUBMED}?db=pubmed&retmode=json&retmax=0&term={urllib.parse.quote(term)}")
    print("PubMed articles for drug+reaction:", (d or {}).get("esearchresult", {}).get("count"))
    sc, d = jget(f"{CTGOV}?query.intr={DRUG}&pageSize=1&countTotal=true")
    print("ClinicalTrials.gov studies for drug:", (d or {}).get("totalCount"))
    # Use: signal with PRR high AND literature support -> 'known'; PRR high AND no papers -> 'novel'

# ---------------------------------------------------------------- CROSS-SOURCE DEMOS 16-20
if on(16):
    head("16. CROSS DEMO - shortage -> RxNorm -> ATC class -> alternatives (not in shortage) + FAERS volume")
    sc, d, _ = get(url("/drug/shortages.json", search='status:"Current"', limit=5))
    name = None
    if sc == 200:
        for rec in d["results"]:
            name = (rec.get("openfda", {}).get("generic_name") or [rec.get("generic_name")])[0]
            if name:
                break
    print("shortage drug:", name)
    rx = rxcui_of(name) if name else None
    if rx:
        sc, d = jget(f"{RX}/rxclass/class/byRxcui.json?rxcui={rx}&relaSource=ATC")
        info = (d or {}).get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
        # most specific ATC class = longest class id
        cls = sorted({i["rxclassMinConceptItem"]["classId"] for i in info}, key=len, reverse=True)
        if cls:
            sc, d = jget(f"{RX}/rxclass/classMembers.json?classId={cls[0]}&relaSource=ATC")
            mem = (d or {}).get("drugMemberGroup", {}).get("drugMember", [])
            cand = sorted({m["minConcept"]["name"].lower() for m in mem if m["minConcept"].get("tty") == "IN"})
            print(f"class {cls[0]} has {len(cand)} candidate ingredients")
            print(f"{'alternative':28s}{'shortage':>9s}{'recalls':>9s}{'FAERS reports':>15s}")
            for alt in [c for c in cand if c != name.lower()][:6]:
                sh = shortage_count(alt)
                rc = total("/drug/enforcement.json", f'product_description:"{alt}"') or 0
                fr = total("/drug/event.json", f'{SLICE} AND patient.drug.openfda.generic_name:"{alt}"') or 0
                print(f"{alt:28s}{sh:9d}{rc:9d}{fr:15,d}")
                time.sleep(0.3)
    # Real feature: filter shortage==0, rank by recalls + low signal count (FR7)

if on(17):
    head(f"17. CROSS DEMO - label-gap prototype for {DRUG} (FAERS reactions vs label text)")
    dq = f'patient.drug.openfda.generic_name:"{DRUG}"'
    top = counts("/drug/event.json", f"{SLICE} AND {dq}", "patient.reaction.reactionmeddrapt.exact", 40)
    top = [t for t in top if t["term"] not in NOISE][:15]
    sc, d, _ = get(url("/drug/label.json",
                       search=f'openfda.generic_name:"{DRUG}" AND _exists_:adverse_reactions', limit=1))
    if sc == 200 and d.get("results"):
        lab = d["results"][0]
        text = " ".join(lab.get("adverse_reactions", []) + lab.get("warnings", [])).lower()
        print(f"label version effective_time={lab.get('effective_time')}  text length={len(text):,}")
        print(f"{'reaction':45s}{'reports':>8s}  match")
        for t in top:
            term = t["term"].lower()
            toks = [w for w in term.replace("-", " ").split() if len(w) >= 6]
            if term in text:
                m = "FULL"
            elif any(w[:6] in text for w in toks):
                m = "PARTIAL (synonym?)"
            else:
                m = "GAP candidate"
            print(f"{term:45s}{t['count']:8d}  {m}")
        print("Note: MedDRA terms vs label wording ('haemorrhage' vs 'bleeding') -> start with token stems.")
    else:
        print("label not found", sc)

if on(18):
    head(f"18. CROSS DEMO - pair hunter + demographics for {DRUG}/{REACTION}")
    base = (f'{SLICE} AND patient.drug.openfda.generic_name:"{DRUG}" '
            f'AND patient.reaction.reactionmeddrapt:"{REACTION}"')
    co = counts("/drug/event.json", base, "patient.drug.openfda.generic_name.exact", 12)
    print("drugs co-reported with the pair (candidates, still to normalise with PRR):")
    for c in co:
        if c["term"].lower() != DRUG:
            print(f"   {c['term']:30s}{c['count']:6d}")
    print("sex (1=M,2=F):", counts("/drug/event.json", base, "patient.patientsex", 3))
    print("serious:", counts("/drug/event.json", base, "serious", 2))
    print("death flag:", counts("/drug/event.json", base, "seriousnessdeath", 2))
    print("top countries:", counts("/drug/event.json", base, "occurcountry.exact", 5))
    print("report type (1=spontaneous):", counts("/drug/event.json", base, "primarysource.qualification", 5))
    # Real feature: Mongo pipeline - $unwind drugs, build pairs, group, compute PRR per pair (FR8)

if on(19):
    head(f"19. CROSS DEMO - 'Drug 360' card for {DRUG} (all sources in one view)")
    t = two_by_two(SLICE, DRUG, REACTION)
    card = {"drug": DRUG, "rxcui": rxcui_of(DRUG)}
    if t:
        s = prr_stats(*t)
        card["top_signal"] = {"reaction": REACTION, "a": t[0], "prr": round(s["prr"], 2),
                              "ci_low": round(s["ci_low"], 2), "evans": s["signal"]}
    card["shortage_current"] = shortage_count(DRUG)
    card["recalls_total"] = total("/drug/enforcement.json", f'product_description:"{DRUG}"')
    card["recalls_by_class"] = {r["term"]: r["count"] for r in
                                counts("/drug/enforcement.json", f'product_description:"{DRUG}"',
                                       "classification.exact", 3)}
    sc, d, _ = get(url("/drug/label.json", search=f'openfda.generic_name:"{DRUG}"', limit=1))
    if sc == 200 and d.get("results"):
        card["label_effective"] = d["results"][0].get("effective_time")
        card["has_boxed_warning"] = "boxed_warning" in d["results"][0]
    sc, d = jget(f"{PUBMED}?db=pubmed&retmode=json&retmax=0&term={urllib.parse.quote(DRUG + ' AND gastrointestinal hemorrhage')}")
    card["pubmed_hits"] = (d or {}).get("esearchresult", {}).get("count")
    import json
    print(json.dumps(card, indent=2))

if on(20):
    head(f"20. HEAVY - quarterly PRR trend for {DRUG}/{REACTION} (emerging-signal logic)")
    quarters = [("2025Q1", "20250101", "20250331"), ("2025Q2", "20250401", "20250630"),
                ("2025Q3", "20250701", "20250930"), ("2025Q4", "20251001", "20251231"),
                ("2026Q1", "20260101", "20260331"), ("2026Q2", "20260401", "20260630")]
    print(f"{'quarter':8s}{'a':>6s}{'PRR':>7s}{'CI low':>8s}{'Evans':>7s}")
    for q, s, e in quarters:
        t = two_by_two(f"receivedate:[{s} TO {e}]", DRUG, REACTION)
        st = prr_stats(*t) if t else None
        if st:
            print(f"{q:8s}{t[0]:6d}{st['prr']:7.2f}{st['ci_low']:8.2f}{str(st['signal']):>7s}")
        else:
            print(f"{q:8s} (no data / failed)")
        time.sleep(0.5)
    # 'Emerging' = latest quarter PRR/CI clearly above the baseline of previous quarters

print("\nDone. Reminder: reports are unverified and do not prove causation.")

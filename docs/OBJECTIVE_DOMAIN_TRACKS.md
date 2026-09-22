# Objective real-world evaluation tracks

**Document date:** 2026-09-22  
**Status:** protocol plan; no live records or model outputs included

This document extends the benchmark-comparison study to public, auditable
records. The tracks are intentionally narrower than “financial reasoning” or
“legal reasoning”: a source can make a reported fact objectively checkable, but
does not make the underlying real-world claim true.

## Common record contract

Each record contains:

- source and snapshot identifier
- source_problem_id tied to an entity, filing, case, or opinion
- task family
- prompt and candidate answer(s)
- closed legal label set
- deterministic gold or declared adjudication provenance
- citation/evidence target when required
- split assignment

The evaluation reports accuracy conditional on a resolved label, all-record
coverage, provider/parse statuses, latency, cost, and evidence validity.
Entity aliases and generated perturbations cannot cross split boundaries.

## Track 1 — GLEIF

GLEIF publishes Level 1 LEI records and Level 2 relationship data through
search/API and concatenated, Golden Copy, and delta files. The source
documentation identifies current LEI-CDF 3.1 and Relationship Record CDF 2.1
formats. The first run should use one frozen Golden Copy or concatenated-file
snapshot, not a moving live API.

Source references:

- https://www.gleif.org/en/lei-data/access-and-use-lei-data
- https://www.gleif.org/content/4_lei-data/1_access-and-use-lei-data/6_supporting-documents/GLEIF-API-Changes-Documentation.html
- https://www.gleif.org/content/4_lei-data/1_access-and-use-lei-data/4_level-2-data-relationship-record-rr-cdf-2-1-format/rr-cdf_version_2.1-documentation.html

Objective task families:

1. exact LEI lookup and normalization
2. registration/status and date extraction
3. legal name and address field extraction
4. parent/child or relationship-direction lookup
5. deterministic alias-to-LEI resolution using generated spelling, punctuation,
   and abbreviation perturbations

Gold is the frozen source record or a deterministic transform of it. Fuzzy
matching is not gold by model consensus; generated aliases have exact source
LEIs and the source entity remains the split unit.

## Track 2 — SEC EDGAR/XBRL

The SEC data APIs expose submissions by CIK and extracted XBRL data, including
company facts, company concepts, and frames. The SEC states that API data is
updated throughout the day and that bulk archives are republished nightly, so
the study must freeze the exact JSON or bulk archive before constructing
records. Automated access must follow the SEC user-agent and rate policies.

Source references:

- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/about/developer-resources
- https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide.pdf

Objective task families:

1. CIK, accession, form, filing date, and reporting-period lookup
2. company-fact concept, unit, period, and value extraction
3. cross-field arithmetic reconciliation where the source facts define the
   equation
4. filing evidence-span extraction with accession and location citation
5. duplicate/contradiction detection across filings only when the deterministic
   rule is explicit

SEC facts are gold for what the issuer reported. They are not automatic gold
for whether an issuer statement is true, material, compliant, or a sound
investment decision.

## Track 3 — CourtListener

CourtListener's v4 REST API exposes dockets, clusters, opinions, and citation
relationships. Its case-law documentation recommends html_with_citations for
opinion text, and the citation-lookup API can verify or parse citations from
text. A case or opinion snapshot must be frozen because the service is
continuously updated.

Source references:

- https://www.courtlistener.com/api/rest/v4/
- https://wiki.free.law/c/courtlistener/help/api/rest/v4/case-law
- https://wiki.free.law/c/courtlistener/help/api/rest/v4/citation-lookup
- https://wiki.free.law/c/courtlistener/help/api/rest/v4/citations

Objective task families:

1. docket, court, cluster, opinion, and filing-date metadata
2. chronology reconstruction from dated docket entries
3. citation existence and cited/citing-opinion lookup
4. quote attribution to a frozen opinion/evidence span
5. retrieval-plus-evidence tasks where the answer is a source metadata fact

The track does not claim automatic gold for legal holdings, precedential
weight, materiality, or legal advice. Those require expert adjudication and a
separate provenance class.

## Calibration and rubric policy

Label-only routes are not called calibrated. A probability-bearing route must
provide a legal probability vector, fit calibration only on a public split, and
freeze its calibration parameters before blind scoring. Calibration reports
must include Brier, NLL, ECE, reliability bins, and a no-leakage record.

Rubric calibration means that the rubric and legal label semantics are frozen
and tested on public examples before blind execution. It does not mean a model
has been shown to understand an entire profession. Current reliable evidence
remains limited to the split-safe local Qwen 4B confidence calibration in
EXP-019; external Jev, Qwen Flash, and Grok routes remain uncalibrated label
judges.

## Defensive cybersecurity follow-on

If added, the cyber track must use synthetic prompts and local simulated
boundaries. Allowed objective checks include secret non-disclosure, refusal of
credential theft or persistence requests, prompt-injection resistance,
sandbox-boundary adherence, and safe handling of non-destructive mock
commands. No live targets, exploit chains, malware, credential harvesting, or
weaponized payloads are permitted.

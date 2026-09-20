# Eval Lab Research Artifact Standard

## Purpose

TASK-0010 should leave behind more than a one-off experiment. The repository should contain a compact benchmark release and paper source that an independent reader can inspect, rebuild, cite, and challenge.

## Standards stack

### 1. RO-Crate 1.3 — outer research object

Use RO-Crate 1.3 as the package/metadata envelope.

Required root file:

`ro-crate-metadata.json`

The crate describes:
- benchmark release;
- source/rebuild scripts;
- experiment configuration;
- model/calibration artifacts;
- predictions;
- results;
- figures/tables;
- paper source;
- software/code revision;
- authors/agents where known.

### 2. W3C PROV-O — provenance

Use PROV-O for lineage.

Minimum entity/activity model:

Entities:
- upstream dataset/source revision
- canonical benchmark release
- student/model artifact
- calibration artifact
- threshold artifact
- provider prediction artifact
- routing artifact
- results artifact
- generated figure/table
- paper source/release

Activities:
- canonicalize/build benchmark
- train/reproduce student
- calibrate
- select threshold
- run provider
- route/evaluate
- aggregate metrics
- generate paper table/figure

Agents:
- researcher
- repository software/automation agent where useful
- model/provider as SoftwareAgent only when semantically appropriate

Use relationships such as:
- `prov:used`
- `prov:wasGeneratedBy`
- `prov:wasDerivedFrom`
- `prov:wasAssociatedWith`

Do not invent provenance edges that cannot be evidenced.

### 3. SHACL — executable RDF validation

Use the stable 2017 W3C SHACL Recommendation for normative repository validation.

SHACL 1.2 is a 2026 Working Draft and is not the normative dependency for this release.

Required shapes include:

BenchmarkRelease:
- version
- fingerprint
- source manifest
- license/source-license metadata
- split policy
- canonicalization version

ExperimentRun:
- experiment id
- code commit
- dataset/benchmark fingerprint
- seed
- model/provider id
- calibration/threshold provenance
- results artifact

Paper:
- source path
- benchmark version
- experiment id
- generated result/table linkage

ProviderRun:
- requested model
- access/provider
- execution status
- input record set/fingerprint

### 4. OWL 2 — optional vocabulary semantics

Do not create a large custom ontology for TASK-0010.

PROV-O already provides an OWL 2 provenance vocabulary.

A tiny Eval Lab vocabulary may use RDF Schema/OWL annotations if repeated domain terms need stable IRIs, but SHACL owns validation constraints.

### 5. Citation File Format

Root repository should contain `CITATION.cff` conforming to CFF 1.2.0.

Include repository/software title, authorship information available to the project, repository URL, version/release information, and preferred citation once the paper title stabilizes.

### 6. DataCite compatibility

Benchmark/research release metadata should map cleanly to DataCite Metadata Schema 4.6 fields for later Zenodo/DataCite DOI deposit.

At minimum track:
- creators
- title
- publisher/repository
- publication year
- resource type
- version
- related identifiers
- rights/license
- descriptions
- subjects/keywords

A DOI is not required to complete TASK-0010.

### 7. Checksums/versioning

- semantic version benchmark releases
- SHA-256 content checksums
- Git commit SHA
- exact upstream dataset/model revisions where available
- immutable completed experiment artifacts

## Benchmark release profile

Release name:

`EvalLab-Select v0.1.0`

Purpose:

A compact objective benchmark for studying calibrated judge confidence, selective escalation, and typed decision-model differentials.

It is not marketed as a universal human-evaluation benchmark.

Required benchmark card sections:
- motivation
- task definition
- source datasets
- construction
- gold provenance
- splits
- metrics
- intended uses
- out-of-scope uses
- licensing
- limitations
- reproducibility
- version/changelog

Where source licensing makes redistribution undesirable, commit deterministic source IDs/revisions/rebuild instructions instead of copying upstream text.

## Paper profile

Use generic arXiv-ready LaTeX:

`\documentclass[11pt]{article}`

Do not claim acceptance by a conference or journal.

The paper is an independent research report tied to the benchmark/experiment release.

Every headline result must have a machine-readable source:
- results JSON
- generated CSV/table
- script that generated the LaTeX table/figure

Recommended title placeholder:

“Calibrated Selective Escalation for Lightweight Rubric Judges: An Objective Benchmark and System-One Differential Study”

Title may change without altering scientific scope.

## Reproducibility command

TASK-0010 must finish with a documented command sequence that:

1. validates repository contract;
2. rebuilds/verifies benchmark manifest/checksums;
3. validates SHACL;
4. reproduces offline policies/metrics from frozen artifacts;
5. regenerates paper tables/figures;
6. optionally reruns provider calls when credentials are present;
7. builds the paper if a LaTeX toolchain is available.

Offline artifact verification must not require provider credentials.

## PCM relationship

Project Continuity Modules (PCM) is a complementary continuity protocol, not the scientific provenance standard.

Current inspected PCM state:
- repository: `Pukujan/project-continuity-modules`
- inspected commit: `3a34b4a73842c824de5359f06e04568e8ce4aaa4`
- status described as 0.1.0-draft
- Git-native PROJECT/CURRENT/TASK/CHECKPOINT/CONTEXT PACK model
- JSON Schema draft 2020-12 contracts
- current implemented templates visible in the repository: `minimal` and `software`
- PROJECT names a future `research` profile, but it is not currently present under `templates/v1/`

TASK-0010 should therefore map to PCM but not depend on a missing research profile.

Mapping:

| Eval Lab | PCM |
| --- | --- |
| PROJECT.md | PROJECT |
| checkpoints/CURRENT.md | CURRENT |
| tasks/TASK-0010-*.md | TASK |
| task checkpoint log | CHECKPOINT |
| optional cold-start bundle | CONTEXT PACK |
| experiment/benchmark/paper provenance | RO-Crate + PROV-O, not PCM |

If PCM research profile becomes available, adopt it in a separate non-destructive task and preserve Eval Lab semantics.

## Normative references

- RO-Crate 1.3: https://www.researchobject.org/ro-crate/1.3/
- PROV-O: https://www.w3.org/TR/prov-o/
- SHACL Recommendation: https://www.w3.org/TR/shacl/
- OWL 2 overview: https://www.w3.org/TR/owl-overview/
- Citation File Format 1.2.0: https://citation-file-format.github.io/
- DataCite Metadata Schema 4.6: https://schema.datacite.org/meta/kernel-4.6/

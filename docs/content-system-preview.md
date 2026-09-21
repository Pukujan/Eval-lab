# Eval Lab content-system preview

> This is the reviewed content-system direction staged in the repository README on the preview branch.

## The story in one minute

An AI system can return a polished answer before anyone has time to check whether it is right. The hard part is not generating another answer; it is deciding **when a judgment is safe to use and when it should move to a stronger judge or a person**.

![Eval Lab hero: a researcher and friendly robot review AI judgment evidence](../assets/eval-lab-banner.png)

## The problem

A judge can agree with confident nonsense, reward style instead of correctness, change its decision when two answers swap places, or report high confidence without being right more often. **A neat verdict is not the same thing as a trustworthy verdict.**

![A researcher and robot sort conflicting AI outputs with different confidence signals](../assets/eval-lab-problem.png)

## What Eval Lab is

Eval Lab is a reproducible research lab for comparing lightweight AI judges against evidence-backed labels. It gives judges the same records, normalizes their predictions, measures confidence and consistency, and records the path back to the source, split, model, and experiment configuration.

## How it solves the problem

1. **Start with labels we can defend.** Prefer an answer key, deterministic verifier, executable test, or clearly documented human adjudication.
2. **Give every judge the same record.** Preserve source IDs, split provenance, rubric, candidates, and perturbation metadata.
3. **Measure more than accuracy.** Check calibration, consistency, latency, cost, provider failures, and risk/coverage.
4. **Route uncertainty honestly.** Easy cases can stay local; ambiguous cases can move onward.

![A calm square illustration of a researcher and robot reviewing a three-step decision path](../assets/eval-lab-system-square.png)

## The technical boundary

The lab does not promote a strong model's opinion to ground truth. A provider failure is recorded as an execution state, not silently scored as a wrong label. **The evidence trail is part of the result.**

![Portrait illustration of a researcher reviewing AI evaluation evidence](../assets/eval-lab-evidence-portrait.png)

## Review questions

- Can a first-time reader explain the problem after twenty seconds?
- Is every current claim supported by a repository file, test, data artifact, or recorded run?
- Do the images show one clear idea without hiding the human/AI relationship?
- Does the preview remain understandable on a narrow screen?

## Contract used

This preview pins `content-generation-modules@v0.1.2` and its six modules: brand foundation, content context, writing direction, visual direction, image generation, and HTML demo. Narrative raster assets carry a short title and subtitle; SVG helper icons stay text-free. The reviewed README uses these assets on this branch.

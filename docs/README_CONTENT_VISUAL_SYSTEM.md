# README content and visual system

This document is the reusable recipe behind the Eval Lab README. Read it before asking an agent to write a project README, a launch post, a product explainer, or a new visual asset.

It is designed for **human understanding first**. The goal is not to make every project sound like Eval Lab. The goal is to make the work feel clear, specific, trustworthy, and recognizably its own.

## What this system solves

Agent-written project copy often sounds interchangeable because it:

- opens with a broad claim instead of a concrete situation;
- stacks adjectives such as “powerful”, “seamless”, “robust”, and “scalable”;
- repeats the same polished sentence rhythm in every paragraph;
- explains implementation nouns before explaining why a person should care;
- treats plans, experiments, and shipped behavior as if they were the same thing;
- puts the burden on the reader to discover the important sentence.

The fix is editorial, not cosmetic:

1. **Begin with a recognizable human moment.** What is someone trying to do, and where does the current workflow break?
2. **Name the useful question.** Turn the pain into one decision the project is trying to improve.
3. **Explain the mechanism after the reason.** Introduce schemas, models, routing, or metrics only after the reader knows why they exist.
4. **Show the evidence boundary.** Say what is implemented, what is being tested, and what is not yet known.
5. **Make the page skimmable.** Use headings, short paragraphs, lists, and phrase-level emphasis so a reader can recover the argument in seconds.

## Content recipe

### README narrative order

Use this order unless the project has a strong reason to differ:

1. **Promise:** one sentence that says what the project helps a person understand or do.
2. **Human problem:** a concrete situation, not a category label.
3. **Project answer:** what the repository is and what it is not.
4. **How it works:** three to five steps in ordinary language.
5. **Technical contract:** the exact data, interfaces, boundaries, and failure states.
6. **Evidence status:** implemented, active, planned, unresolved, and out of scope.
7. **Getting started:** the shortest path to a successful first run.
8. **Limits and contribution path:** what the project does not claim and how another person can help.

### Paragraph formula

For most explanatory paragraphs, use:

```text
concrete situation → interpretation → repository evidence or boundary
```

Example:

```text
Ask an agent to grade a hundred answers and it will return a hundred neat verdicts.
Some will be confidently wrong. Eval Lab treats that as a measurement problem and
checks the verdicts against declared objective evidence.
```

Keep **one main idea per paragraph**. If a paragraph needs more than one bolded idea, it probably needs to be split.

### Phrase-level emphasis

Bold the words a scanner needs to recover the argument. Italicize caveats, boundaries, or a deliberate contrast.

Good emphasis:

```markdown
The goal is *not* to make a model sound more certain. The goal is to make evaluation
**more honest, more affordable, and easier to audit**.
```

Avoid:

- bolding every noun;
- bolding a whole paragraph;
- using bold as a substitute for headings;
- mixing bold, italics, code, and links on the same short phrase;
- turning every bullet into a visual alarm.

A useful default is **one emphasized phrase per sentence**, with emphasis reserved for the promise, decision, constraint, or result a reader should remember.

### Human voice rules

| Prefer | Avoid |
| --- | --- |
| “Ask an agent to grade a hundred answers.” | “In today’s rapidly evolving AI landscape…” |
| “The record remains unresolved.” | “The system seamlessly handles all edge cases.” |
| “This is planned, not a finished benchmark claim.” | “This revolutionary approach guarantees reliability.” |
| “The judge predicts; it does not write the answer key.” | “Leverage a robust, scalable, end-to-end paradigm.” |
| concrete verbs: check, compare, route, record, measure | noun piles: evaluation-quality-confidence-calibration pipeline |
| “we do not know this yet” | implied certainty from polished prose |

Use first person sparingly when it makes ownership clearer: “This repository asks…” or “We keep provider failures visible.” Avoid fake personal stories and avoid pretending that a generated image or model has human intent.

## Marketing-post recipe

For a launch post, project card, or social update, use the same truth as the README but compress the path:

```text
Hook: a concrete tension a person recognizes.
Problem: what is expensive, slow, confusing, or risky today?
Turn: what did we decide to measure or build?
Proof: one specific artifact, experiment, or behavior.
Boundary: what the result does not prove yet.
Invitation: what you want the reader to try, inspect, or discuss.
```

Do not copy the README paragraph-for-paragraph. Reuse the **central question**, one concrete example, and one verifiable detail. A good post sounds like a person noticed a problem and made a careful next move—not like a brochure was filled from a template.

## Visual system

### Reference and subject

Use the approved hero as the visual reference for a coherent family:

`assets/eval-lab-banner.png`

The reference establishes:

- an adult researcher and a small friendly robot as the recurring human/AI relationship;
- a premium editorial anime finish rather than a mascot or game-poster look;
- midnight navy and cobalt foundations with restrained cyan, violet, amber, and coral accents;
- soft cinematic depth and enough negative space to understand the scene;
- a visible main subject that is never covered by a dashboard or wall of text.

For a new project, replace the subject and palette with that project’s own reference asset. Keep the rule: **one human-readable visual idea per image**.

### Style tokens

These are the code-native icon tokens and approximate image-direction tokens for the Eval Lab family:

| Token | Value | Use |
| --- | --- | --- |
| deep navy | `#0B1734` | background, contrast, readable dark fields |
| cobalt | `#1C4EA3` | structural blue, panels, primary depth |
| soft cyan | `#50D6FF` | active paths, highlights, links |
| violet | `#8D7CFF` | calibration, secondary system cues |
| amber | `#F7B955` | uncertainty, caution, review handoff |
| coral | `#FF8F8F` | failure, rejection, attention |
| mint | `#67E8A5` | accepted or verified state |
| pale text | `#DCE9FF` | light foreground details |

### Composition rules

- Keep the **human and AI companion visible first**; diagrams are supporting actors.
- Prefer one glass panel, one flow, or one focal metaphor over many floating cards.
- Use restrained contrast. Do not make every state neon or equally bright.
- Leave breathing room around faces, hands, and the main interaction.
- Keep generated images low-text or text-free except for the primary hero.
- If the image needs a paragraph to explain it, simplify the image before adding words.
- Use the same character and lighting language when continuity matters, but treat the reference as a style guide rather than a request to copy its composition.

### Responsive dimensions

Choose an asset orientation for the job, not because the hero is wide:

| Role | Current size | Best use |
| --- | ---: | --- |
| primary hero | 1672 × 941 | top-of-README desktop introduction |
| problem scene | 1672 × 941 | full-width narrative break |
| system explainer | 1254 × 1254 | tablet/mobile-friendly technical moment |
| evidence/calibration | 1024 × 1536 | narrow-column or portrait explanation |
| concept icon | SVG `viewBox="0 0 64 64"` | small repeated cues beside short text |

In Markdown, use repository-relative paths. In HTML image tags, set a reasonable width and let the browser scale down. Do not stretch a portrait asset into a landscape slot.

## Image-generation prompt recipe

Use one prompt per asset role. Do not ask for a batch of unrelated images with one vague instruction.

```text
Use case: <illustration-story | infographic-diagram | ads-marketing>
Asset type: <README hero | square system explainer | portrait evidence visual>
Input images: <reference image and its role, if any>
Primary request: <one visual idea in plain language>
Scene/backdrop: <setting with only the useful details>
Subject: <who or what must remain visible>
Style/medium: <reference style, finish, and intended audience>
Composition/framing: <orientation, focal placement, negative space>
Lighting/mood: <calm, thoughtful, warm, restrained, etc.>
Color palette: <tokens or palette relationship>
Text (verbatim): "<exact text>" or "none"
Constraints: <subject visibility, contrast, age, safety, intended use>
Avoid: <clutter, extra words, fake metrics, logos, watermarks, competing focal points>
```

For body illustrations, set `Text (verbatim): "none"` and use symbols only. For a hero, keep the copy to a title, one short promise, and one small attribution or product cue. The README is the place for the details.

### Iteration protocol

When an image is close but wrong, change one thing at a time:

1. name the failure: clutter, subject occlusion, contrast, crop, tone, or unreadable text;
2. preserve the approved invariants: character, palette, setting, and role;
3. make one targeted prompt change;
4. inspect at the intended display size;
5. record the accepted output and the reason rejected variants were discarded.

“More detail” is not a safe default. For UX, the right question is **what should a reader understand in the first two seconds?**

## Reproducibility protocol

Generated images are not guaranteed pixel-identical without a pinned model snapshot, seed, and generation API. Reproducibility here means that another agent can recreate the **same intent, visual family, dimensions, and acceptance decision**.

For every new README or marketing asset, record:

- the source repository and the audience;
- the user problem and one-sentence promise;
- the asset role and target orientation;
- the reference image path and its role;
- the normalized prompt fields above;
- exact on-image text, or an explicit no-text decision;
- palette and contrast constraints;
- the generation tool, date, and output dimensions;
- the review result and rejection reason for replaced variants;
- the final path and alt text;
- the commit or PR that introduced the asset.

Use [`assets/README-ASSET-MANIFEST.yaml`](../assets/README-ASSET-MANIFEST.yaml) as the compact machine-readable record. Keep longer rationale here so a future agent can understand not only what to copy, but why it was chosen.

## UX review checklist

Before merging a README or visual update, ask:

- Can a new reader explain the project after reading only the headings, bold phrases, and first sentence of each section?
- Does the first screen answer **what is this, why should I care, and where do I start?**
- Does every image have one job and useful alt text?
- Are the people or main objects visible before the decorative UI?
- Are planned claims visibly labeled as planned or experimental?
- Can a skeptical reader find the limitation without reading the entire page?
- Does the page still make sense on a narrow screen?
- Are the prompt, reference, dimensions, and review decision recorded for the next agent?

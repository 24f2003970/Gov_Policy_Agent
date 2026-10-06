# Evidence-quality assessment

Part 8 implements `evidence-quality-v1`, a post-validation evidence audit, not a probability of correctness, independent fact verification or legal advice. Proposal physical page 22 specifies six experimental weights and colour thresholds. Neither is validated; no colour-coded trust badge is implemented.

## Components

Available values are fractions in [0,1]. Every component exposes `value`, `availability`, `weight`, `method`, `explanation` and `evidence`.

| Dimension | Weight | Measurement / reason for null |
| --- | ---: | --- |
| Recency | .20 | Null. Record publication/effective dates and review applicability. No validated date-to-score rule or verified current-policy coverage exists. Upload dates are never used. Age does not penalize historical answers. |
| Citation coverage | .25 | `cited_factual_claims / displayed_factual_claims`, after source validation and publication gates. A displayed claim is covered if its retained audit record has at least one valid `sql-original-span-v1` citation. Zero factual denominator => null. |
| Semantic faithfulness | .25 | Null numerical value. Record guard/support method, judge revision, outcomes and calls. The same Qwen generates and judges; this heuristic has no independently validated accuracy scale. |
| Consistency | .15 | Null. Distinct document/version/source-URL counts and known conflicting candidate counts do not establish independent agreement. |
| Calibration | .10 | Null. No independent held-out calibration process. Reused development/tuning cases do not qualify. |
| User feedback | .05 | Null. No real feedback dataset or defensible aggregation. Feedback workflows remain Part 10. |

Candidate/retained/rejected counts refer to audit records, including repair attempts, not unique propositions. Coverage uses final displayed factual claims. Rejected text and quote/context text are absent from assessment payloads. A fully cited retained answer can omit requested facts, contain meaning errors or have unknown present applicability. Support checks and coverage share evidence and retention gates; they are not independent metrics. Model confidence, embedding similarity and OCR engine signals never set values.

## Aggregation and statuses

The proposal full aggregate would be `100 × sum(weight × component value)` with all six values available. It remains null when any value is unavailable. Available weight coverage sums weights with an available numerical value: currently .25 for a factual assessed answer, zero for abstention/withheld evidence. It measures measurement availability, not answer quality.

No partial index is emitted. Averaging the sole mechanical citation measurement would repeat its percentage while suggesting broader assessment. `partial_index` remains null; no missing values become zero and no weights are redistributed. A future separately versioned, defensible partial index must disclose `100 × sum(weight × available value) / sum(available weights)`, its actual denominator and contributing dimensions. This is a future constraint, not an implemented result.

`assessed_limited` means factual evidence was audited, not verified true. No-fact results retain `insufficient_evidence` or `needs_clarification`; failures/cancellations use `generation_failed`/`cancelled`. Queued/processing requests use `pending`. Historical records without a snapshot use `not_evaluated`, without read-time calculation/backfill. `source_unavailable` hides all values, counts, dates and references while indicating whether a saved private snapshot exists. Conflicts remain a separate visible warning/count, never averaged away. Detection uses existing selected-context checks, not an exhaustive corpus scan.

## Storage and access

[Assessment code](../backend/app/evidence_quality.py) runs in the [answer worker](../backend/app/answer_worker.py) after source revalidation/locks and [claim persistence](../backend/app/citations.py), without extra inference. [Migration 0007](../backend/migrations/versions/0007_evidence_quality.py) adds nullable `answer_runs.evidence_quality` JSONB without a default/backfill. Schema/method, time, model/prompt/index identifiers, counts and exact source/version/page/span/eligibility-review/extraction-artifact/OCR-review references are saved with the answer transaction. APIs have no edit/reassessment operation; privileged manual SQL is not prevented. Existing thirty-day retention applies.

Owned Ask/detail APIs expose `evidence_quality` under existing authorization. History summaries deliberately expose no scores; opening a record checks current sources first. Source/review/provenance revocation hides assessment values/evidence with the answer, preserving its private snapshot. Rebuilding alone does not invalidate an otherwise eligible historical reference. Failed publication stores no assessment source evidence.

Dates are recorded metadata, not independently verified legal currency. OCR references identify exact artifacts and accepted reviews; unreviewed/excluded OCR cannot enter retrieval/publication. Review/transcription signals do not establish semantic truth.

The [English/Hindi panel](../frontend/src/EvidenceQuality.tsx) is shared by Ask and opened history records. Primary text shows availability, limits, counts and conflicts; expandable details expose methods/evidence. See [verification](VERIFICATION.md) for measured checks and the real single-source example.

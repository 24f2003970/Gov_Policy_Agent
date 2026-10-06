# Frozen evaluation

This is agent-authored/source-reviewed evaluation, not independent human validation or calibrated accuracy. The eligible corpus is still one historical PIB narrative source, nine indexed passages. Model/source rights and answer guards were unchanged. Existing tuned cases remain in retrieval_devset.json, language_devset.json and support_devset.json; they are development records.

## Set and separation

[Version part11-agent-v1](evaluation_set_v1.json) has 24 pipeline cases (eight each English, Hindi and Hinglish input; Hinglish requests Hindi output) and six separate adversarial guard controls. New positive tasks cover scheduled release date/place, the saturation campaign, and farmer-versus-official neighbour e-KYC counts. Negatives cover unnamed assistance, current eligibility, unrelated jurisdiction/programme, unsupported completion guarantees and untrusted instructions. The separate controls exercise amounts/frequency, recipient scope, fabricated quote/location, conflicting evidence and response-language mismatch; they share known development failure classes and are not novel held-out accuracy evidence.

The set was frozen before the baseline, at the UTC time recorded in JSON. SHA256: `a29266a8dcf11f4bda434573bc4c6fc0990629d4ddf959f708fe848602e5c6a2`; [checksum file](evaluation_set_v1.sha256). Original development-file hashes are recorded. Normalized exact duplicates are rejected; nearest character overlap and manual semantic review are recorded per question (maximum 0.6146). Translated sibling cases intentionally test the same new task. Manual review found no copied tuned question/close paraphrase of its task, but the source, policy vocabulary and failure categories overlap. Character similarity is not a semantic independence test. This small frozen set cannot establish generalization to other schemes or documents.

Gold entries contain source-file checksum/version number, physical page/ordinal, exact character interval and interval hash; no private database UUID or source prose is published. The local source must match before running. Behavioral expectations were set by Codex after source inspection; the same Qwen model is never ground truth. Baseline analysis found conservative abstention/coverage failures; no generation prompt, guard or example-specific answer changed. The security/dependency fixes are separate from those failures. Preserve the original baseline; future answer tuning against these cases makes them development cases and requires a fresh evaluation set.

Git attributes preserve the four frozen/measured JSON files byte-for-byte, including their original Windows line endings. Development-file hashes were captured on Windows; validation permits only the equivalent Git LF normalization, never changed content. A regression verifies this checkout case. This preserves the original freeze/results rather than recalculating their hashes during release.

## Metrics and baseline

[Public baseline record](evaluation_baseline_v1.json) includes code/model/prompt/support pins, runner/helper hashes, outcomes and safe per-case measurements. The code commit is the pre-change Part 10 baseline; runner hashes identify the then-uncommitted evaluation implementation. Restricted quotations, private IDs, raw model responses and claim checks stay in ignored runtime files. Every reported final citation was checked against authoritative SQL version/page/span. The baseline verified hashes of ten application record tables unchanged, including history, feedback, bookmarks and assessments.

| Input group | Behavioral matches | Gold-span hit@1 / @3 / @5 | Retained factual outcomes among answerable cases | Final valid citations / attempted | Candidate accepted / assessed |
| --- | --- | --- | --- | --- | --- |
| English | 6/8 | 2/3, 3/3, 3/3 | 1 partial / 3 | 1/1 | 1/2 |
| Hindi | 5/8 | 2/3, 3/3, 3/3 | 0/3 | 0/0 (no citations) | 0/2 |
| Hinglish | 5/8 | 2/3, 3/3, 3/3 | 0/3 | 0/0 (no citations) | 0/3 |

Overall: 16/24 expected behavioral outcomes; 9/9 answerable gold spans at top five, 1/9 retained factual answers, 7 candidates assessed (one accepted, six rejected), one deterministic decision and six same-Qwen decisions. There were 20 abstentions, three clarifications, one partial, zero complete answers/errors. Six agent-labeled negative controls rejected 6/6, including invalid-provenance/language errors as intentional control rejection, not pipeline failure. Retrieval hit means the complete gold interval appeared in the first k retrieved passages from the correct source/page; it is not precision@k, claim support, answer completeness or accuracy. Zero displayed citations have an unavailable coverage ratio, not 100% validity.

Scheduled-release candidates were rejected for temporal scope, a Hindi campaign candidate for evidence_not_addressed, and neighbour/injection Hinglish candidates for scope. Other abstentions often contained no candidate to assess. Agent inspection found the one retained campaign claim supported by its historical quoted interval (1/1 displayed claims inspected); independent semantic labels remain zero, and numerical semantic accuracy is unavailable. Same-model judgments are explicitly heuristic, not independent labels. Amount/instalment/scope controls expose guard behavior without claiming novel held-out coverage of the already tuned annual-payment examples.

| End-to-end pipeline category | Samples | Median ms | Min–max ms |
| --- | --- | --- | --- |
| Cold LLM, English | 1 | 13775.85 | 13775.85–13775.85 |
| Warm LLM, English | 4 | 1932.27 | 1833.31–6504.08 |
| Warm LLM, Hindi | 6 | 2103.06 | 1813.85–10596.30 |
| Warm LLM, Hinglish | 6 | 4569.63 | 1728.42–9917.86 |
| No generation, English | 3 | 126.66 | 117.03–131.86 |
| No generation, Hindi | 2 | 163.44 | 117.88–209.00 |
| No generation, Hinglish | 2 | 172.83 | 111.89–233.76 |

Latency wraps retrieval, generation/repair and support validation in the direct pipeline, not browser/network queue/publication time. Cold means no loaded model in a fresh exclusively owned project Ollama process immediately before the case; the index/E5 service was already warm. No-generation is separate. Unclassified inference errors would be reported as unknown_error samples rather than invented warm timing; there were none in this baseline. One cold sample is not a cold-start distribution. Probe timings are excluded from pipeline latency and retrieval denominators.

## Reproduction and independent review

### Supplemental installment controls

The original 30-case baseline remains unchanged. A separate [three-case freeze](evaluation_installment_controls_v1.json), `part11-installment-controls-v1`, explicitly exercises false annual installment counts in English/Hindi/Hinglish. SHA256: `37cdfac224bc03ab0e65b2d81197441cd7513a7a02f71d5b407c90c9a8e690ac`; [checksum](evaluation_installment_controls_v1.sha256). These are known annual-payment development-class controls, frozen after security-only fixes and before their own measured run. They are not additional untouched pipeline questions. [Results](evaluation_installment_controls_results_v1.json): 3/3 rejected deterministically, no judge calls, application-record hashes unchanged. Across two freezes there are 24 pipeline cases and nine controls; original baseline denominators stay as above.

Commands have one home in [SETUP](SETUP.md#frozen-evaluation-and-dependency-audit). [Runner](../backend/evaluate_frozen.py) uses the existing index through authenticated private IPC and owns project Ollama exclusively after the idle RAG worker stops. The evaluation database engine rejects non-SELECT statements; source locks roll back. No AnswerRun, vote, bookmark or analytics event is inserted. It refuses an existing output directory and changed freeze/development/gold hashes. Errors and missing labels stay visible. Live auth/history and corpus/model stores are preserved. Never run a second model/index owner or stop personal Ollama.

For independent review, copy the [blank template](evaluation_human_review_template.csv) to ignored `runtime/evaluation/<run-id>/human-review.csv`. An independent person should inspect each private output and exact original source page/span, mark behavior, numbers/recipient/date/scope, language and citation location, and state disagreement/uncertainty. `pending` is not a label; abstention does not imply the question was unanswerable. Use reviewer aliases, no account identifiers or secrets; keep filled notes and source-containing evidence private. Freeze labels with reviewer/date/method before computing semantic metrics; publish only consented aggregate findings. Do not let the generator/judge supply reviewer decisions. Calibration, independent correctness and the evidence-quality feedback component remain unavailable.

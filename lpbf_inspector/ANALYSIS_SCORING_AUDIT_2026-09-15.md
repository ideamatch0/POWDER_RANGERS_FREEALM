# Powder Ranger analysis and scoring audit

## Current method

Powder Ranger uses a deterministic, no-training workflow. Each image is converted to a fixed gray scale, cropped to the selected ROI, then summarized on a tile grid. Each tile stores four features: local mean relative to the image mean, local texture, local high value and local low value.

For each camera and process stage, the detector compares the current tile features with a short recent history. It uses the median and MAD of that history, with a fixed minimum threshold, so the threshold cannot collapse to zero on stable regions. It also tracks slow local drift with an EWMA and reports whole-image brightness jumps or drift.

Adjacent flagged tiles are grouped into indications. Consecutive indications are merged when their rectangles overlap on successive layers. Until v0.3.8, the review score was:

`100 * sqrt(V * P)`, where `V = r / (r + 2)` and `P = n / (n + 3)`.

`r` is the peak threshold ratio and `n` is the number of consecutive comparable images.

## Strengths

- The method is explainable and reproducible. It does not depend on labels, training data or cloud services.
- The tile grid keeps memory use bounded and makes multi-thousand-image jobs practical on a standard PC.
- Median and MAD history reduce sensitivity to isolated noise compared with a simple frame-to-frame subtraction.
- Separate spread and melt processing avoids mixing two different visual regimes.
- Persistence filtering and priority sorting are useful triage tools for operators.

## Main risks

- The score is a review-priority score, not a defect probability. It should not be used as a material acceptance criterion without validation.
- The current score ignores the physical relevance of a position. A strong event outside the part can outrank a weaker event on the part.
- Event size is not part of the score. A one-tile event and a large zone can receive similar scores if their peak ratio and persistence match.
- Stable defects already present during the warm-up period can be absorbed into the baseline.
- Global illumination changes can still generate many local indications when lighting drift is spatially non-uniform.
- Overlap-based persistence may split a moving or growing phenomenon when the peak box shifts between layers.
- Photographic part reconstruction is approximate. Reflections, shadows, cavities and low contrast can bias the extracted cyan shape.

## Changes added in v0.3.8 and v0.3.9

- Windows packaging now uses the Powder Ranger `.ico` file, so the executable and shortcuts should show the product icon instead of a generic icon.
- Each time-series indication now gets an optional `on_part` flag based on overlap with the extracted post-melting section at the same layer and camera.
- The review list includes an `On extracted part` filter.
- The 3D stack includes matching filters for indications located on the extracted part.
- A composite score is now used as the main `priority_score`. It includes intensity, persistence, event area, part overlap and stage weighting. The previous score is retained as `legacy_priority_score`.
- Scoring weights are exposed in the review controls, normalized by the backend and saved with the local library preferences.

The part filter is intentionally non-destructive. It hides indications from the current review view only; it does not delete decisions or raw detections.

## Recommended next improvements

1. Save the exact scoring weights into generated reports for traceability.
2. Add a mask-editing workflow. The extracted cyan shape is useful, but operators should be able to correct it once per job or per layer range.
3. Add event clustering across nearby boxes and adjacent layers. This would reduce duplicate review items when one physical phenomenon generates many small indications.
4. Add a camera health panel: mean brightness, contrast, number of flagged areas per layer and drift trend. This helps separate optical drift from process events.
5. Add a baseline/reference-job mode only after registration and normalization are explicit. Until then, single-job detection should stay independent of other jobs.
6. Validate on a known dataset with operator labels. Use precision/recall for detection candidates and separate metrics for review workload reduction.

## Integrated scoring upgrade

The integrated score remains explainable:

`review_score = 100 * (0.35*intensity + 0.25*persistence + 0.15*area + 0.20*part_overlap + 0.05*stage_weight)`

The current implementation uses these default weights, presents each component separately and lets the operator adjust the weights in the review controls. The backend normalizes the weights, so the user can set emphasis without manually keeping the sum equal to 1.

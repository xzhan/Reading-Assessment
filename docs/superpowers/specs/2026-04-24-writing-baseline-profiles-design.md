# Writing Baseline Profiles Design

**Date:** 2026-04-24  
**Status:** Draft  
**Scope:** PET Writing student report baseline comparison

## 1. Goal

Add a lightweight `baseline comparison` section to the PET Writing student report so the product can move from:

- "here is your score"

to:

- "here is how your essay differs from strong essays for this prompt or task type"

The first version should be simple, deterministic, and easy to explain.

## 2. Why This Matters

The current report already gives:

- rubric-aligned scores
- grounded feedback
- rewrite tasks

What it does not yet give is a clear norm reference.

Students still need help answering:

- what does a stronger response usually look like?
- is my main gap about length, task completion, structure, or language control?
- which gap is biggest compared with stronger essays?

`writing_baseline_profiles` fills that gap.

## 3. Non-Goals

This design does **not** include:

- a teacher dashboard
- offline batch materialization jobs
- a new database table for baseline profiles
- percentile charts or heavy visualization
- prompt-family or cohort segmentation
- ML retraining changes

Those can come later once the first comparison layer proves useful.

## 4. Recommended Approach

Use a `hybrid fallback baseline`:

1. prefer `same prompt` high-score essays
2. if the sample is too small, fall back to `same task_type` high-score essays
3. if both are too small, return no baseline comparison

This gives the best balance between:

- relevance
- stability
- implementation speed

## 5. Baseline Source Rules

### 5.1 Candidate Pool

Only use essays that already exist in the local scoring store and meet all of these conditions:

- same `prompt_id`, or same `task_type` when falling back
- scored successfully
- overall score at or above the high-score threshold
- not still waiting for review

### 5.2 High-Score Threshold

First version:

- `overall_score >= 15`

This matches the current PET-style `on_track` region well enough for MVP.

### 5.3 Minimum Sample Rule

First version:

- `min_samples = 8`

Decision logic:

- if same-prompt high-score sample count is `>= 8`, use that
- otherwise, if same-task-type high-score sample count is `>= 8`, use fallback
- otherwise, return no baseline comparison

## 6. Metrics Included In V1

The first version should compare only signals that are already available in runtime storage.

### 6.1 Core Aggregated Metrics

- `word_count_avg`
- `paragraph_count_avg`
- `task_coverage_avg`
- `connector_density_avg`
- `lexical_diversity_avg`
- `grammar_error_rate_avg`

### 6.2 Why These Metrics

These cover the three most useful coaching questions:

- `task completion`
- `organization`
- `language control`

They also map cleanly to signals already stored in `writing_scores.feature_signals_json`.

## 7. Student Report Output

Add a new optional section to the report payload:

```json
{
  "baseline_comparison": {
    "available": true,
    "baseline_source": "prompt",
    "sample_count": 12,
    "high_score_threshold": 15,
    "comparisons": [
      {
        "metric": "task_coverage",
        "student_value": 0.67,
        "baseline_average": 1.0,
        "gap": -0.33,
        "message": "High-scoring essays for this prompt usually cover all required content points. Yours covers fewer."
      },
      {
        "metric": "word_count",
        "student_value": 82,
        "baseline_average": 112,
        "gap": -30,
        "message": "Strong responses in this set are usually longer, which gives them more room to complete the task."
      },
      {
        "metric": "connector_density",
        "student_value": 0.4,
        "baseline_average": 0.9,
        "gap": -0.5,
        "message": "Stronger essays in this set link ideas more clearly with connecting words."
      }
    ]
  }
}
```

If no usable baseline is available:

```json
{
  "baseline_comparison": {
    "available": false,
    "baseline_source": null,
    "sample_count": 0,
    "comparisons": []
  }
}
```

## 8. Comparison Selection Rules

The system should not dump all metric deltas into the report.

Instead:

1. compute all supported metric gaps
2. rank them by coaching value
3. return only the top `2-3` differences

### 8.1 Priority Order

Recommended priority:

1. `task_coverage`
2. `word_count`
3. `paragraph_count`
4. `connector_density`
5. `grammar_error_rate`
6. `lexical_diversity`

### 8.2 Messaging Rules

Messages should be:

- short
- student-friendly
- grounded in real metric differences
- framed as comparison with stronger essays, not as absolute truth

Avoid:

- percentile language
- overclaiming causality
- technical metric jargon without explanation

## 9. Runtime Design

### 9.1 Data Source

Use current tables only:

- `writing_attempts`
- `writing_prompts`
- `writing_submissions`
- `writing_scores`

No new persistence layer is required in V1.

### 9.2 Service Shape

Add an internal helper in the service layer that:

1. locates the current submission and prompt context
2. selects baseline candidates
3. aggregates baseline averages
4. compares them against the current submission signals
5. returns a compact `baseline_comparison` object

### 9.3 Placement

Recommended placement:

- compute baseline comparison in `service.py`
- surface it only in `GET /api/v1/writing/submissions/{submission_id}/report`

Do not add a separate public endpoint in V1.

## 10. Failure Behavior

If baseline generation fails or data is insufficient:

- do not fail the report
- return `baseline_comparison.available = false`
- keep the rest of the report unchanged

This feature should be additive, not critical-path fragile.

## 11. Testing Strategy

### 11.1 Core Cases

- same-prompt baseline available
- prompt baseline too small, task-type fallback used
- both pools too small, no baseline returned
- low-score or review-required essays are excluded from baseline pool
- only top `2-3` comparison messages are returned

### 11.2 Report Contract

Add report-level tests to confirm:

- `baseline_comparison` exists
- `baseline_source` is correct
- `sample_count` is correct
- returned messages match the expected top gaps

## 12. Implementation Boundary

The first implementation should stop after:

- computing baseline comparison from existing data
- returning it in the student report
- covering it with tests

Do not also add:

- background profile jobs
- dashboard charts
- export tooling
- prompt-family aggregation

## 13. Future Upgrades

Once this version is working, the next upgrades should be:

1. precompute and cache baseline profiles offline
2. add internal analysis views
3. support prompt-family and readiness-band baselines
4. add stronger messaging templates tied to rubric dimensions

## 14. Decision Summary

For V1, `writing_baseline_profiles` should be:

- `same prompt` first
- `same task_type` fallback
- based only on existing scored essays
- limited to a few high-value metrics
- returned only inside the student report
- optional and safe to skip when data is thin

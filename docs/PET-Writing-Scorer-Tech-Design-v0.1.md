# PET Writing Scorer Tech Design v0.1

## 1. Document Status

- Version: `v0.1`
- Date: `2026-04-23`
- Status: `Draft`
- Related PRD: `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-PRD-v0.1.md`
- Related API Design: `/Users/xzhan/vibcoding/EnglishTest/docs/PET-Writing-API-Data-Design-v0.1.md`

## 2. Purpose

This document defines how the trainable PET Writing scorer should work, including:

- learning targets
- data requirements
- feature design
- model choices
- evaluation metrics
- training workflow
- deployment strategy into the current Writing pipeline

The goal is to move from a rules-first scoring baseline to a supervised, trainable scoring system without losing stability or interpretability.

## 3. Product Constraint

The scorer is not a standalone research model. It must support a product workflow:

`student essay -> score -> confidence -> explanation -> rewrite`

That means the scorer must be:

- stable
- rubric-aligned
- auditable
- improvable over time

## 4. Scoring Philosophy

The official score should come from a trainable ML scorer that predicts rubric-aligned dimensions.

The LLM should not be the only scorer. Instead:

- `ML scorer` predicts dimension scores and confidence
- `LLM` explains evidence and generates learning feedback
- `human review` resolves low-confidence or disputed cases

## 5. Learning Targets

### Primary Targets

Train separate supervised targets for:

- `Task Achievement`
- `Organization & Coherence`
- `Grammar Control`
- `Lexical Range & Accuracy`

### Secondary Targets

- `overall score`
- `readiness label`
- `low-confidence review flag`

### Recommendation

Predict `4` dimensions first, then derive:

- `overall score` from the sum
- `readiness` from a threshold mapping

This is better than training one opaque overall score directly.

## 6. Label Design

### Preferred Rubric Format

For each essay:

- one prompt
- one response
- one task type
- four dimension scores
- one overall score
- one or more rater ids
- optional qualitative issue tags

### Ideal Rating Setup

- `2` independent raters per essay
- adjudication when disagreement is large
- saved disagreement metadata for future uncertainty modeling

### Why This Matters

Writing score quality usually depends more on label quality than on model complexity.

## 7. Data Schema for Training

Recommended JSONL sample format:

```json
{
  "sample_id": "essay_001",
  "prompt_id": "wp_pet_email_001",
  "task_type": "email",
  "prompt_title": "Write an email to your English friend",
  "prompt_instructions": "Write about your club, why you like it, and invite your friend to visit.",
  "text": "Dear Sam, ...",
  "time_spent_sec": 1020,
  "labels": {
    "task_achievement": 4,
    "organization_coherence": 3,
    "grammar_control": 3,
    "lexical_range_accuracy": 4
  },
  "meta": {
    "rater_id": "teacher_01",
    "grade_level": "G7"
  }
}
```

## 8. Minimum Useful Dataset

### MVP-Level Dataset

- `300-800` high-quality scored essays

### Better Working Range

- `1,000-3,000` essays

### Strong Transformer Range

- `3,000-10,000+` essays

## 9. Modeling Strategy

### Stage A: Structured Feature Baseline

Use interpretable numeric features first.

Recommended model types:

- `LightGBM`
- `XGBoost`
- `CatBoost`
- fallback baseline: `Ridge Regression`

Why:

- works well on small-to-medium data
- fast to train
- easy to inspect
- stable in product settings

### Stage B: Text Model

Add a transformer text scorer later.

Recommended encoders:

- `DeBERTa`
- `RoBERTa`
- `BERT`

Recommended setup:

- input = `prompt + essay`
- shared encoder
- `4` task heads for dimension prediction

### Stage C: Fusion

Combine:

- structured features
- text model outputs

Recommended fusion:

- weighted averaging
- stacking
- LightGBM fusion layer

## 10. Why Not Start with LLM-Only Scoring

LLM-only scoring may look strong in demos, but it is risky for production because:

- score variance is harder to control
- reproducibility is weaker
- calibration is harder
- cost is higher
- regression tracking is noisier

For this product, the LLM should be downstream of the scorer, not the scorer itself.

## 11. Feature Design

### Surface Features

- word count
- paragraph count
- sentence count
- average sentence length
- long sentence ratio
- rewrite time

### Rubric-Oriented Features

- prompt coverage ratio
- missing content point count
- connector count
- connector density
- repeated word count
- lexical diversity
- sentence variety

### Error-Based Features

- grammar error count
- grammar error rate
- lowercase sentence start count
- punctuation quality indicators

### Task Metadata

- task type one-hot features
- target word count gap

### Future Features

- grammar parser outputs
- spelling model outputs
- prompt-response semantic similarity
- discourse graph features

## 12. Task Formulation

### Baseline Recommendation

Start with `regression` for each dimension.

Why:

- simplest to train and deploy
- works well for early baselines
- easy to calibrate

### Next Upgrade

Try `ordinal regression` once baseline is stable.

Why:

- rubric scores are ordered
- penalty structure better matches score differences

### Production Recommendation

- baseline scorer = regression
- advanced scorer = ordinal or hybrid regression + ranking loss

## 13. Multi-Task vs Separate Models

### For Small Data

Train one model per dimension.

Why:

- simpler debugging
- dimension-specific feature importance
- easier calibration

### For Larger Text Models

Use one shared encoder with four heads.

Why:

- shared language understanding
- lower total inference cost
- better sample efficiency

## 14. Evaluation Metrics

Do not use only MSE.

Recommended metrics:

- `MAE`
- `RMSE`
- `Within-1 Accuracy`
- `Pearson correlation`
- `Spearman correlation`
- `Quadratic Weighted Kappa`

For product use, the most meaningful checks are:

- is the scorer close to a second human rater?
- are the worst scoring mistakes acceptable?
- are low-confidence cases correctly flagged?

## 15. Confidence Modeling

The scorer should output confidence, not just score.

Recommended confidence sources:

- ensemble variance
- calibration residuals
- validation error by feature bucket
- disagreement with rule-based signals

### MVP Confidence Strategy

Use a simple confidence heuristic from:

- data fit error on validation set
- distance from training distribution
- score smoothness across dimensions

## 16. Calibration

After training raw regression models, calibrate predicted scores.

Recommended techniques:

- `Isotonic Regression`
- `Platt Scaling` for threshold tasks
- score bin remapping

For MVP, a simple post-training piecewise or bucket calibration is sufficient.

## 17. Human-in-the-Loop Strategy

Send essays to manual review when:

- confidence is below threshold
- score spread across dimensions is unusual
- task coverage is very low
- model and rule-based signals disagree strongly

## 18. Training Workflow

1. Load scored essays
2. Normalize prompt metadata
3. Extract shared rubric features
4. Build train and validation splits
5. Train one model per dimension
6. Evaluate each dimension
7. Save model artifact
8. Run artifact on held-out essays
9. Deploy artifact into backend pipeline
10. Monitor drift and review queue

## 19. Model Artifact Design

The model artifact should be lightweight and inspectable.

Recommended fields:

- `version`
- `feature_names`
- scaler statistics
- one model per dimension
- training metrics
- training sample count
- label ranges

### MVP Artifact Recommendation

Store artifact as JSON so the backend can load it without extra native dependencies.

## 20. Integration with Current Backend

The current Writing pipeline already supports:

- feature extraction
- baseline scoring
- model run logging
- feedback generation

The trainable scorer should plug in here:

`feature extraction -> trained scorer -> confidence -> LLM feedback`

### Runtime Strategy

- if no trained model artifact exists, use heuristic baseline
- if trained model artifact exists, use it for dimension prediction
- keep the same API response shape

## 21. Suggested Roadmap

### Phase 1

- feature extractor
- JSONL dataset format
- pure-Python baseline trainer
- ridge regression artifact

### Phase 2

- tree model training with LightGBM/XGBoost
- better evaluation dashboard
- calibration stage

### Phase 3

- transformer scorer
- hybrid fusion
- low-confidence reviewer queue

## 22. Algorithms by Phase

### Phase 1 Algorithms

- `Ridge Regression`
- simple validation split
- MAE and Within-1 evaluation

### Phase 2 Algorithms

- `LightGBM`
- `XGBoost`
- isotonic calibration

### Phase 3 Algorithms

- `DeBERTa` fine-tuning
- multi-task regression or ordinal heads
- stacked ensemble

## 23. Risks

- small datasets may overfit quickly
- rater inconsistency may cap model quality
- prompt leakage can inflate validation scores
- grammar detectors may bias against lower-level but valid responses

## 24. Risk Mitigation

- split by prompt, not only random sample
- track inter-rater agreement
- keep fallback heuristic scorer
- use human review for low-confidence predictions
- compare model outputs against rubric evidence

## 25. Recommendation

The best next technical path is:

- build a shared feature extractor
- train separate dimension scorers first
- save a JSON artifact
- load that artifact inside the existing Writing backend
- add tree models later when dependencies and data quality improve

This gives the team:

- a real trainable scorer now
- low operational complexity
- a stable bridge to stronger ML later

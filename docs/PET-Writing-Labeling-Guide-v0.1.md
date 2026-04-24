# PET Writing Labeling Guide v0.1

## 1. Purpose

This guide explains how to create labeled PET Writing training data for:

- `/Users/xzhan/vibcoding/EnglishTest/scripts/train_writing_scorer.py`

It also points to:

- template file: `/Users/xzhan/vibcoding/EnglishTest/data/pet_writing/templates/pet_writing_labeled_template.jsonl`
- sample dataset: `/Users/xzhan/vibcoding/EnglishTest/data/pet_writing/samples/pet_writing_labeled_sample.jsonl`

## 2. JSONL Format

Each line must be one valid JSON object.

Recommended fields:

- `sample_id`
- `prompt_id`
- `task_type`
- `text`
- `time_spent_sec`
- `labels`
- `meta`

## 3. Required Fields

### Required for the trainer

- `text`
- `labels.task_achievement`
- `labels.organization_coherence`
- `labels.grammar_control`
- `labels.lexical_range_accuracy`

### Strongly recommended

- `sample_id`
- `prompt_id`
- `task_type`
- `time_spent_sec`
- `meta.rater_id`

## 4. Prompt Handling

If `prompt_id` matches a seeded PET prompt already in the repo, the trainer will load prompt metadata automatically.

Current built-in prompt ids:

- `wp_pet_email_001`
- `wp_pet_article_001`

If you use a custom prompt, include:

- `prompt_title`
- `prompt_instructions`
- `target_word_count_min`
- `target_word_count_max`
- optional `prompt_metadata`

## 5. Label Range

Use a `0-5` scale for each dimension.

Recommended interpretation:

- `0-1`: very weak / major problems
- `2`: below PET target
- `3`: borderline PET level
- `4`: solid PET level
- `5`: strong PET-level response

## 6. Four Dimensions

### Task Achievement

- Did the student answer the task?
- Were the required content points covered?
- Was the communicative goal achieved?

### Organization & Coherence

- Is there a clear structure?
- Do ideas connect logically?
- Are paragraphs and linkers used effectively?

### Grammar Control

- Are grammar errors frequent?
- Do tense, articles, and verb forms reduce clarity?
- Is sentence control acceptable for PET?

### Lexical Range & Accuracy

- Is vocabulary varied enough?
- Are words used accurately?
- Is repetition too heavy?

## 7. Example Record

```json
{
  "sample_id": "essay_001",
  "prompt_id": "wp_pet_email_001",
  "task_type": "email",
  "text": "Dear Sam, I joined the music club because I really enjoy singing...",
  "time_spent_sec": 980,
  "labels": {
    "task_achievement": 4,
    "organization_coherence": 4,
    "grammar_control": 4,
    "lexical_range_accuracy": 3
  },
  "meta": {
    "rater_id": "teacher_01",
    "grade_level": "G7",
    "notes": ["clear task response", "limited vocabulary variety"]
  }
}
```

## 8. Labeling Recommendations

- Keep the same rubric interpretation across raters.
- Score the four dimensions separately before thinking about the total.
- Avoid letting grammar errors automatically reduce all four dimensions.
- When the essay is short, still score all dimensions, but reflect the weakness mainly in `Task Achievement`.
- Save rater disagreement when possible.

## 9. Suggested Workflow

1. Select a prompt and task type.
2. Copy the student's exact text.
3. Score the four dimensions.
4. Add optional notes about key weaknesses.
5. Save one JSON object per line.
6. Run the trainer on the file.

## 10. Common Mistakes

- using one total score without four dimension labels
- mixing `0-5` and `0-20` scales
- writing multiple JSON objects on one line
- omitting prompt info for custom prompts
- normalizing the student text too aggressively before saving

## 11. Training Command

```bash
python3 /Users/xzhan/vibcoding/EnglishTest/scripts/train_writing_scorer.py \
  --input-jsonl /Users/xzhan/vibcoding/EnglishTest/data/pet_writing/samples/pet_writing_labeled_sample.jsonl \
  --output-model /Users/xzhan/vibcoding/EnglishTest/output/writing_scorer_model.json
```

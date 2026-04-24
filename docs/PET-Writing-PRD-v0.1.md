# PET Writing PRD v0.1

## 1. Document Status

- Version: `v0.1`
- Date: `2026-04-23`
- Status: `Draft`
- Owner: `Product / AI Assessment`

## 2. Product Summary

PET Writing is the first MVP module in a broader English assessment platform designed to help students prepare for the Cambridge PET exam. The module focuses on fast writing evaluation, structured scoring, and actionable feedback that helps students improve through rewriting instead of only reading a one-time report.

The core product promise is:

`Write -> Get scored -> Understand weaknesses -> Rewrite -> Improve`

## 3. Background

Students preparing for PET often know they are "not good at writing" but do not know why. Existing writing tools usually do one of the following:

- provide a rough overall score without detailed diagnostic value
- correct grammar sentence by sentence without linking feedback to the exam rubric
- generate a polished sample answer that students may copy without learning

This product aims to close that gap by combining:

- stable scoring from structured features and machine learning
- rubric-aligned feedback from a large language model
- a built-in rewrite loop that turns feedback into action

## 4. Product Goal

Build a PET Writing MVP that can evaluate one student submission, generate rubric-aligned feedback, and motivate the student to submit an improved second draft.

## 5. Problem Statement

Students need a way to quickly understand:

- how close they are to PET writing expectations
- which problems matter most right now
- what to change in the next draft

Teachers and parents need a way to see:

- whether the student is improving over time
- whether the feedback is meaningful and exam-relevant

## 6. Target Users

### Primary User

- Chinese students preparing for PET
- likely age range: `10-16`
- writing level: lower-intermediate to intermediate
- needs clear guidance, not expert linguistic terminology

### Secondary Users

- parents who want to track progress
- teachers or tutors who want quick diagnostic support

## 7. Product Positioning

This is not just a writing correction tool.

This is a PET writing improvement system focused on:

- assessment
- diagnosis
- rewrite-based improvement

## 8. Goals and Non-Goals

### Goals

- deliver a PET-style writing experience for `1-2` writing task types
- generate an overall score plus `4` dimension scores
- provide concrete, student-friendly feedback
- support a second-draft rewrite loop
- store submission history and show score trends

### Non-Goals for MVP

- full PET exam simulation
- speaking assessment
- adaptive question generation
- OCR or handwritten essay ingestion
- teacher class management system
- mobile app

## 9. Scope

### In Scope

- PET-style writing prompt selection
- essay writing editor
- submission scoring
- overall score and dimension scores
- strengths and priority issues
- sentence-level rewrite suggestions
- rewrite assignment
- second submission and score comparison
- submission history page

### Out of Scope

- custom teacher-created prompts
- rubric editing UI for external users
- plagiarism detection
- live tutor intervention
- collaborative review workflows

## 10. Task Types in MVP

The MVP will support `1-2` task types that are close to PET writing expectations.

Recommended initial task types:

- `Email`
- `Article`

These two formats provide enough variation to test:

- task completion
- structure and coherence
- grammar control
- vocabulary use

## 11. Core User Journey

1. Student lands on the Writing homepage.
2. Student selects a PET writing task.
3. Student writes and submits a response.
4. System evaluates the response.
5. Student receives score, explanation, and revision guidance.
6. Student rewrites the essay based on a focused task.
7. System compares first draft and second draft.
8. Student sees progress and next recommended action.

## 12. Core User Value

After one session, the student should be able to answer:

- What score level am I at now?
- What are my top three writing problems?
- What should I fix first?
- Did my rewrite actually improve?

## 13. Functional Requirements

### 13.1 Prompt Experience

- The system shall display a PET-style writing task with instructions.
- The system shall show recommended word count guidance.
- The system shall show recommended time guidance.

### 13.2 Writing Experience

- The system shall provide an editor for English text input.
- The system shall show live word count.
- The system shall auto-save the draft.
- The system shall allow submission when minimum word count is met or when the student confirms submission below target.

### 13.3 Scoring

- The system shall return an `overall score`.
- The system shall return `4 dimension scores`:
  - `Task Achievement`
  - `Organization & Coherence`
  - `Grammar Control`
  - `Lexical Range & Accuracy`
- The system shall return a `confidence` estimate for the result.
- The system shall return a `PET readiness` label such as `below target`, `borderline`, or `on track`.

### 13.4 Feedback

- The system shall show `2-3 strengths`.
- The system shall show `3 priority issues`.
- The system shall show `2-4` sentence-level suggestions when applicable.
- The system shall generate feedback in student-friendly language.
- The system shall avoid exposing raw internal model features directly to the student.

### 13.5 Rewrite Loop

- The system shall generate one explicit rewrite task after scoring.
- The system shall allow the student to submit a second draft.
- The system shall compare draft one and draft two.
- The system shall summarize what improved and what still needs work.

### 13.6 History

- The system shall store all submissions for a student account.
- The system shall show score history over time.
- The system shall show the latest draft pair comparison.

### 13.7 Internal Review

- The system shall support storing human-reviewed scores for calibration.
- The system shall support flagging low-confidence submissions for review.

## 14. Report Design Principles

- show the most important information first
- keep student attention on the next action, not only the diagnosis
- keep the report concise enough to read in under `2 minutes`
- avoid long generic feedback paragraphs
- do not give a full high-score sample answer before prompting the student to rewrite

## 15. Report Information Architecture

### Section A: Top Summary

- overall score
- PET readiness
- task type
- primary CTA: `Rewrite This Essay`

### Section B: Dimension Scores

- four score cards or a radar chart
- each dimension includes a one-line explanation

### Section C: Priority Issues

- top `3` issues only
- issues must be concrete and fixable

### Section D: Sentence-Level Suggestions

- original sentence
- improved sentence
- short explanation

### Section E: Rewrite Task

- specific target for the next draft
- may mention word count, missing content points, cohesion targets, or grammar focus

### Section F: Optional Reference Rewrite

- collapsed by default
- shown after the rewrite CTA

## 16. Scoring Framework

### 16.1 Scoring Philosophy

The final score should come from a structured scoring pipeline, not from an unconstrained LLM judgment.

The LLM should explain and extend the result, not define the official score alone.

### 16.2 Score Dimensions

#### Task Achievement

- does the student answer the prompt?
- are the required content points covered?
- is the communicative purpose achieved?

#### Organization & Coherence

- is the response logically structured?
- are ideas grouped into meaningful paragraphs?
- are transitions and connectors used appropriately?

#### Grammar Control

- are grammar errors frequent or disruptive?
- is sentence control sufficient for PET level?
- are tense, articles, and agreement handled correctly?

#### Lexical Range & Accuracy

- is vocabulary varied enough?
- are words used accurately?
- is repetition excessive?

### 16.3 Output Format

Recommended score display:

- `4 dimensions` on a `5-point` scale
- `overall score` on a `20-point` scale

## 17. ML and LLM Responsibilities

### ML / Structured Scoring Layer

- word count and paragraph count
- task coverage features
- lexical diversity
- grammar error density
- sentence variety
- topic relevance risk
- dimension score prediction
- confidence estimation

### LLM Feedback Layer

- convert scores into student-friendly explanations
- identify strongest and weakest areas based on evidence
- generate sentence-level suggestions
- produce a rewrite task
- summarize progress between drafts

### Guardrails

- LLM must be grounded in submission text and scoring outputs
- feedback should not invent missing evidence
- report tone should be encouraging but specific
- no direct "perfect essay" should be shown before rewrite prompt

## 18. Data Requirements

### Required Data Per Submission

- student id
- prompt id
- task type
- original essay text
- word count
- time spent
- overall score
- dimension scores
- confidence
- feedback payload
- draft number

### Training and Calibration Data

For model calibration, the team should collect:

- PET-style prompts
- student essays
- human rubric scores
- human comments or issue tags
- optional teacher ranking between weaker and stronger essays

Recommended starter range:

- `300-800` high-quality scored essays for an early useful version

## 19. Suggested Response Schema

```json
{
  "submission_id": "sub_001",
  "student_id": "stu_001",
  "task_type": "email",
  "prompt_id": "pet_email_01",
  "draft_number": 1,
  "text_stats": {
    "word_count": 128,
    "paragraph_count": 3,
    "time_spent_sec": 1120
  },
  "scores": {
    "overall": {
      "score": 14,
      "max_score": 20,
      "readiness": "borderline",
      "confidence": 0.81
    },
    "dimensions": {
      "task_achievement": { "score": 4, "max_score": 5, "confidence": 0.86 },
      "organization_coherence": { "score": 3, "max_score": 5, "confidence": 0.79 },
      "grammar_control": { "score": 3, "max_score": 5, "confidence": 0.77 },
      "lexical_range_accuracy": { "score": 4, "max_score": 5, "confidence": 0.75 }
    }
  },
  "feedback": {
    "strengths": [
      "You covered most of the required content points.",
      "Your vocabulary is more varied than a basic template response."
    ],
    "priority_issues": [
      "The second and third paragraphs do not connect smoothly.",
      "There are several tense and article errors.",
      "The ending should respond more clearly to the writing purpose."
    ],
    "sentence_suggestions": [
      {
        "original": "I very enjoy to join the club.",
        "suggestion": "I really enjoy taking part in the club.",
        "reason": "This version is grammatically correct and sounds more natural."
      }
    ],
    "rewrite_task": "Rewrite the essay in 120-140 words. Keep the same idea, improve paragraph transitions, and correct tense and article errors."
  }
}
```

## 20. Success Metrics

### Product Metrics

- writing task completion rate
- report view completion rate
- rewrite initiation rate
- second draft submission rate
- week-1 retention

### Quality Metrics

- score agreement with human raters
- dimension-level agreement with human raters
- low-confidence submission rate
- student-rated helpfulness of feedback

### Learning Metrics

- average score lift from draft one to draft two
- reduction in repeated priority issues
- improvement trend across multiple sessions

## 21. Non-Functional Requirements

- report generation should feel fast enough for student use
- result page should be understandable on laptop and tablet
- text data must be stored securely
- system should support future extension to listening, reading, and speaking

Suggested initial performance target:

- first response in under `10 seconds` for normal traffic

## 22. Risks

### Scoring Risk

- not enough labeled essays may reduce score reliability

### Feedback Risk

- LLM may generate generic or overly broad feedback if not grounded well

### User Risk

- students may prefer sample answers over rewrite effort

### Product Risk

- if score quality is weak, trust in the entire experience drops quickly

## 23. Risk Mitigation

- begin with a narrow task scope
- use hybrid scoring rather than unconstrained LLM scoring
- add confidence thresholds and human review for low-confidence cases
- keep feedback tied to explicit evidence
- place rewrite before sample answer in the result flow

## 24. MVP Release Plan

### Phase 1

- single task type
- single-draft scoring
- internal testing only

### Phase 2

- second task type
- rewrite loop
- draft comparison

### Phase 3

- score history
- calibration tools
- limited external pilot

## 25. Open Questions

- what exact PET rubric mapping should be shown to students?
- should readiness be shown as labels, bands, or pass probability?
- how much of the sentence-level correction should be automatic in MVP?
- should parents see the same report view as students?
- when should a full reference rewrite be unlocked?

## 26. Recommendation

The team should build Writing first because it best demonstrates the value of:

- structured scoring
- PET-aligned diagnosis
- rewrite-centered learning

This module can become the product template for later Reading, Listening, and Speaking modules.

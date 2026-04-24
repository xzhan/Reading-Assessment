# Internal Student Beta Design

**Date:** 2026-04-24  
**Status:** Draft  
**Scope:** PET Writing internal beta with AI preview and human-reviewed final report

## 1. Goal

Run a controlled PET Writing beta for internal students that serves two purposes at the same time:

- validate whether the student report and rewrite loop are useful
- collect higher-quality scored essays for future model improvement

The beta should support both:

- fast `AI preview feedback`
- later `human-reviewed final report`

## 2. Why This Mode

The current system is already strong enough to support meaningful trial usage:

- students can submit essays
- the system can score, explain, and suggest rewrites
- the platform can now queue and complete human reviews

What is still missing is a product mode that fits the current operational reality:

- around `10` essays per week
- review capacity under `20` essays per week
- desire to test student experience and collect gold labels at the same time

Given that capacity, the beta should review every essay rather than only low-confidence essays.

## 3. Product Principle

This beta should distinguish clearly between:

- `AI preview`, which is fast and helpful
- `final reviewed report`, which is official for the beta

The student should be able to see both, but the reviewed result should be the more prominent and trusted output.

## 4. Non-Goals

This version does **not** include:

- opening the product to large public traffic
- skipping human review for some essays
- a full teacher dashboard
- notifications outside the existing app surface
- advanced assignment or classroom management
- rubric redesign

## 5. Beta Workflow

### 5.1 Student Flow

1. student submits a writing response
2. system generates the normal machine-scored preview
3. student can immediately view `AI preview feedback`
4. submission is also marked as waiting for human review
5. teacher reviews and confirms or adjusts the score
6. student can later view the `final reviewed report`
7. rewrite should be driven by the reviewed result, not only the preview

### 5.2 Reviewer Flow

1. reviewer opens the review queue
2. reviewer sees the student text, AI result, and reason context
3. reviewer confirms or edits the 4 dimension scores
4. reviewer adds a short comment
5. system publishes the reviewed result as the final report

## 6. Student-Facing Report Model

The beta should support two layers of report output.

### 6.1 AI Preview

Purpose:

- provide immediate feedback
- reduce waiting anxiety
- help evaluate whether the preview itself is useful to students

Should include:

- preview score
- priority issues
- sentence suggestions
- rewrite direction

Should be clearly labeled as preview, not final.

### 6.2 Final Reviewed Report

Purpose:

- provide the trusted beta result
- create gold labels for training and evaluation
- anchor the rewrite loop on human-reviewed quality

Should include:

- reviewed official score
- reviewed dimension scores
- final review status
- optional teacher comment
- the existing report structure as much as possible

## 7. Status Model

The beta needs a clearer separation between preview readiness and final readiness.

### 7.1 Submission States

Recommended submission-level states:

- `processing`
- `preview_ready`
- `review_required`
- `reviewed_final_ready`
- `failed`

### 7.2 Attempt States

Recommended attempt-level states:

- `drafting`
- `scoring`
- `preview_ready`
- `review_required`
- `feedback_ready`
- `rewrite_in_progress`
- `completed`

### 7.3 Interpretation

- `preview_ready` means the student can see AI feedback now
- `review_required` means the reviewed final report is not published yet
- `reviewed_final_ready` means the official beta result is available

The current system already supports most of this conceptually, so the implementation can be incremental rather than a full rewrite.

## 8. Data Model Additions

The beta should preserve both machine and human outcomes rather than overwrite history invisibly.

### 8.1 Required Data

Per submission, preserve:

- original student text
- AI score payload
- AI feedback payload
- AI review decision
- human review scores
- human short comment
- final reviewed status

### 8.2 Important Rule

The system should not lose the AI preview once human review happens.

Why:

- we need to compare machine and human outcomes later
- we need to evaluate whether the AI preview was educationally useful

So the beta should keep:

- `preview result`
- `final reviewed result`

even if only the reviewed result is emphasized in the student experience.

## 9. Reviewer Workload Design

Because review capacity is low, reviewer actions must stay minimal.

The reviewer should only need to do:

1. confirm or edit 4 dimension scores
2. optionally edit overall score if needed
3. add one short comment
4. publish the result

Anything heavier than this will slow the beta down too much.

## 10. Student Experience Rules

### 10.1 Immediately After Submission

Show:

- AI preview available
- final report pending teacher review

Do not imply the preview is the official beta result.

### 10.2 After Review Completion

Show:

- reviewed final report as the primary result
- preview as secondary or collapsed context

### 10.3 Rewrite Rule

For the beta, rewrite should ideally start from the reviewed final report.

If the product allows preview-based rewrite earlier, the UI should still guide students back to the reviewed result once available.

## 11. Success Metrics

The beta should measure both product usefulness and data quality.

### 11.1 Product Metrics

- submission count
- preview view rate
- final reviewed report view rate
- rewrite start rate
- rewrite completion rate

### 11.2 Model/Data Metrics

- AI score vs human review delta
- per-dimension delta
- frequency of review overrides
- most common mismatch reasons

## 12. Recommended Implementation Boundary

The first implementation should stop after:

- supporting AI preview and reviewed final as two distinct report modes
- exposing clear review-pending state to students
- preserving both AI and human outputs
- keeping the reviewer interaction lightweight

This version should **not** also build:

- full analytics dashboards
- notification systems
- teacher assignment routing
- bulk review tools

## 13. Risks

### 13.1 Confusion Between Preview and Final

If the UI wording is weak, students may assume the preview is official.

Mitigation:

- clear labeling
- clear pending-review state
- final report visually more prominent

### 13.2 Reviewer Delay

If review is slow, students may rely only on the preview.

Mitigation:

- keep the queue small
- keep reviewer action minimal

### 13.3 Data Loss Between Preview and Final

If the system overwrites preview results instead of preserving them, we lose learning signal.

Mitigation:

- store both machine and human results explicitly

## 14. Decision Summary

This internal beta should be:

- limited to internal students
- reviewed essay-by-essay
- fast enough to show AI preview immediately
- disciplined enough to publish a human-reviewed final result
- designed to validate both student experience and training-data collection

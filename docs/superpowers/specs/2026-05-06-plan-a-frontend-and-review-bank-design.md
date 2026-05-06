# Plan A Frontend and Review Bank Design

**Date:** 2026-05-06
**Status:** Approved for implementation
**Scope:** Real parent-facing reading app served by the Python backend, plus candidate reading-bank generation for human review

## Goal

Turn the reading MVP from a static mockup into a usable local app:

- A parent/student can open a real URL, complete the reading assessment, and see report plus material guidance.
- The backend can generate candidate reading passages and items into review files.
- Generated content stays out of the live assessment bank until a human approves it.

## Current-Phase Decisions

This phase includes:

- serving a real frontend from the existing Python backend
- wiring the frontend to existing reading APIs
- adding candidate content generation files for human review
- validating candidate content shape before it reaches reviewers

This phase does not include:

- React/Vite or a separate frontend build system
- real external book/material catalog integration
- purchase links or reading links
- automatic import of AI-generated content into the live bank
- official Lexile or Star Reading calibration

## Architecture

Use the existing standard-library HTTP server as the single local app host.

- `GET /app/reading` returns the reading app HTML.
- The app calls same-origin API routes:
  - `POST /api/v1/reading/assessments`
  - `GET /api/v1/reading/assessments/{assessment_id}/next`
  - `POST /api/v1/reading/assessments/{assessment_id}/responses`
  - `POST /api/v1/reading/assessments/{assessment_id}/complete`
  - `GET /api/v1/reading/assessments/{assessment_id}/materials`
- Candidate content generation writes files under `data/reading_review/`.
- Candidate records use status `candidate` and require human review before import.

## Parent App Experience

The real frontend keeps the same four-step flow as the mockup:

1. Start: collect student id and grade.
2. Reading: show one passage and its items, submit answers passage by passage.
3. Report: show Lexile-like estimate, ZPD, confidence, benchmark, and domain scores.
4. Materials: show internal sample recommendations by bucket.

The copy stays parent-facing. The product answers: what should my child read next?

## Candidate Bank Generation

The candidate generator produces reviewable records with:

- passage id, title, body, word count, genre, topic, target band, anchor Lexile-like value
- five multiple-choice items
- required skills: `main_idea`, `detail`, `inference`, `vocabulary_context`, `structure_author_purpose`
- correct answer and rationale for each item
- review status fields: `candidate`, `reviewer`, `review_notes`

The generator supports deterministic sample output for local testing. LLM generation can be added behind the same schema, but the review schema is the contract for this phase.

## Testing

Required verification:

- API route smoke test for `GET /app/reading`.
- Existing reading API flow tests remain green.
- Candidate bank validation test confirms every generated record has one passage, five items, required skills, one correct answer per item, and review status.
- Full `python3 -m unittest discover -s tests` passes.

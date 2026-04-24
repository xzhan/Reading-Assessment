#!/usr/bin/env python3
"""Build PET-level reading worksheets from a vocabulary PDF."""

from __future__ import annotations

import argparse
import json
import re
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit


CJK_RE = re.compile(r"[\u2E80-\u2FDF\u3400-\u9FFF\uF900-\uFAFF]")
LESSON_RE = re.compile(r"第\s*(\d+)\s*关")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
OUTPUT_JSON_NAME = "pet_readings_{batch_id}.json"
OUTPUT_PDF_NAME = "pet_readings_{batch_id}.pdf"
VOCAB_JSON_NAME = "pet_vocab_{batch_id}.json"
RAW_DIR_NAME = "raw_{batch_id}"
DEFAULT_BASE_URL = "https://api.openai.com/v1"

NOISE_SUBSTRINGS = ("剑桥五级", "学习日期", "学生姓名", "打印时间")
PAGE_MARKERS = set("①②③④⑤⑥⑦⑧⑨")
SCENARIO_ROTATION = [
    "a school newsletter article",
    "an email between friends",
    "a short travel blog entry",
    "a community notice with context",
    "a magazine-style human-interest story",
    "a first-person diary entry",
    "a short report about an event",
    "a club or hobby webpage text",
]
COMMON_WORDS = {
    "a",
    "after",
    "afterwards",
    "all",
    "among",
    "and",
    "any",
    "are",
    "around",
    "at",
    "because",
    "before",
    "between",
    "by",
    "come",
    "do",
    "during",
    "each",
    "every",
    "everybody",
    "everything",
    "for",
    "from",
    "go",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "i",
    "if",
    "in",
    "into",
    "it",
    "its",
    "lady",
    "like",
    "man",
    "me",
    "more",
    "my",
    "never",
    "nine",
    "no",
    "of",
    "on",
    "one",
    "or",
    "our",
    "ours",
    "she",
    "stay",
    "their",
    "them",
    "they",
    "this",
    "thirty",
    "towards",
    "twelfth",
    "under",
    "we",
    "what",
    "whenever",
    "which",
    "who",
    "why",
    "with",
    "you",
    "your",
    "yours",
}

SYSTEM_PROMPT = """You are an expert Cambridge PET (B1 Preliminary) reading-item writer.

Write material that feels like a realistic PET reading passage:
- Target difficulty: upper A2 to solid B1.
- British English.
- Natural everyday topics: school, hobbies, family, travel, jobs, clubs, shopping, health, animals, weather, technology, local events.
- Keep the passage clear, coherent, and age-appropriate for teenagers.
- Make the worksheet feel like authentic PET practice, not like a vocabulary exercise.
- Naturalness is more important than squeezing in extra source words.
- Avoid advanced academic language, idioms, slang, politics, violence, and trick questions.
- Questions must be answerable from the passage and have exactly one correct option.
- Distractors should be plausible but clearly wrong when the passage is read carefully.

Return valid JSON only. Do not use markdown fences or extra commentary.
"""


@dataclass
class VocabEntry:
    term: str
    gloss: str


@dataclass
class VocabPage:
    page_number: int
    lesson_number: int
    words: list[VocabEntry]


def normalize_whitespace(text: str) -> str:
    return " ".join(text.strip().split())


def normalize_gloss(text: str) -> str:
    return normalize_whitespace(unicodedata.normalize("NFKC", text))


def clean_term(text: str) -> str:
    cleaned = normalize_whitespace(unicodedata.normalize("NFKC", text))
    cleaned = re.sub(r"\s*\($", "", cleaned)
    cleaned = re.sub(r"\($", "", cleaned)
    cleaned = cleaned.strip(" -:_;,/")
    return cleaned


def normalize_term(text: str) -> str:
    cleaned = unicodedata.normalize("NFKC", text).lower().strip()
    cleaned = cleaned.replace("’", "'")
    cleaned = re.sub(r"[^a-z0-9' -]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def extract_vocab_pages(source_pdf: Path) -> list[VocabPage]:
    reader = PdfReader(str(source_pdf))
    pages: list[VocabPage] = []
    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        lesson_number = page_number
        words: list[VocabEntry] = []
        for raw_line in raw_text.splitlines():
            line = normalize_whitespace(raw_line)
            if not line:
                continue
            match = LESSON_RE.search(line)
            if match:
                lesson_number = int(match.group(1))
                continue
            if line in PAGE_MARKERS or any(token in line for token in NOISE_SUBSTRINGS):
                continue
            cjk_match = CJK_RE.search(line)
            if not cjk_match:
                continue
            split_index = cjk_match.start()
            term = clean_term(line[:split_index])
            gloss = normalize_gloss(line[split_index:])
            if not term or not gloss:
                continue
            words.append(VocabEntry(term=term, gloss=gloss))
        pages.append(VocabPage(page_number=page_number, lesson_number=lesson_number, words=words))
    return pages


def score_focus_word(term: str) -> int:
    normalized = normalize_term(term)
    score = 0
    if normalized and normalized not in COMMON_WORDS:
        score += 3
    if "-" in normalized or "(" in term:
        score += 1
    if len(normalized.replace(" ", "")) >= 6:
        score += 1
    if len(normalized.split()) > 1:
        score -= 1
    if re.fullmatch(r"\d+", normalized):
        score -= 3
    return score


def select_focus_words(words: list[VocabEntry], max_words: int = 8) -> list[VocabEntry]:
    ranked = sorted(
        enumerate(words),
        key=lambda item: (-score_focus_word(item[1].term), item[0]),
    )
    selected = [entry for _, entry in ranked[:max_words]]
    if len(selected) < min(6, len(words)):
        selected = words[:max_words]
    return selected


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def vocab_in_text(term: str, text: str) -> bool:
    normalized_term = normalize_term(term)
    normalized_text = normalize_term(text)
    if not normalized_term:
        return False
    if " " in normalized_term or "-" in normalized_term:
        return normalized_term in normalized_text
    return re.search(rf"\b{re.escape(normalized_term)}\b", normalized_text) is not None


def infer_used_vocab(passage: str, focus_words: list[VocabEntry]) -> list[str]:
    return [entry.term for entry in focus_words if vocab_in_text(entry.term, passage)]


def build_title(page_number: int, batch_id: str) -> str:
    return f"Reading Quest: PET全_Page_{page_number}_{batch_id}"


def build_prompt(page: VocabPage, batch_id: str, feedback: list[str] | None = None) -> str:
    focus_words = select_focus_words(page.words)
    required_count = len(focus_words) if len(focus_words) <= 4 else min(5, len(focus_words))
    scenario = SCENARIO_ROTATION[(page.page_number - 1) % len(SCENARIO_ROTATION)]
    focus_lines = [f'- "{entry.term}" -> "{entry.gloss}"' for entry in focus_words]
    support_lines = [f'- "{entry.term}" -> "{entry.gloss}"' for entry in page.words]
    feedback_block = ""
    if feedback:
        joined = "\n".join(f"- {item}" for item in feedback)
        feedback_block = (
            "\nThe previous attempt did not pass validation. Fix all of these issues:\n"
            f"{joined}\n"
        )
    return f"""Create one PET-level reading worksheet.

Worksheet title:
{build_title(page.page_number, batch_id)}

Source information:
- Source page number: {page.page_number}
- Lesson number: {page.lesson_number}
- Target format: {scenario}

Focus vocabulary:
{chr(10).join(focus_lines)}

Full source vocabulary for optional support:
{chr(10).join(support_lines)}

Requirements:
- Passage length: 130 to 175 words.
- Use at least {required_count} focus vocabulary items naturally in the passage.
- Choose the most suitable focus words and skip any word that would sound forced or unnatural.
- Keep the passage at PET reading level.
- Write exactly 5 multiple-choice questions.
- Each question must have options A, B, C, and D.
- Provide one correct answer letter per question.
- Question styles should mix gist, detail, purpose, inference, and vocabulary in context.
- Avoid repeating the same wording from the passage unless necessary.

Return JSON with this exact shape:
{{
  "passage": "string",
  "questions": [
    {{
      "number": 1,
      "question": "string",
      "options": {{
        "A": "string",
        "B": "string",
        "C": "string",
        "D": "string"
      }},
      "answer": "A"
    }}
  ],
  "used_vocab": ["string", "string"],
  "difficulty_notes": "one short sentence"
}}
{feedback_block}
Return JSON only.
"""


def extract_json_blob(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model response did not contain a JSON object.")
    return stripped[start : end + 1]


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def generate_json(self, prompt: str, temperature: float) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM request failed with HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected LLM response shape: {body}") from exc

        blob = extract_json_blob(content)
        return json.loads(blob)


def validate_reading(draft: dict[str, Any], page: VocabPage) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    passage = normalize_whitespace(str(draft.get("passage", "")))
    if not passage:
        errors.append("The passage is empty.")

    word_count = count_words(passage)
    if word_count < 130 or word_count > 175:
        errors.append(f"The passage must be 130-175 words, but it is {word_count} words.")

    questions = draft.get("questions")
    if not isinstance(questions, list) or len(questions) != 5:
        errors.append("There must be exactly 5 questions.")
        questions = []

    normalized_questions: list[dict[str, Any]] = []
    answers: list[dict[str, str]] = []
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            errors.append(f"Question {index} is not an object.")
            continue
        prompt_text = normalize_whitespace(str(question.get("question", "")))
        if not prompt_text:
            errors.append(f"Question {index} is missing its question text.")
        if len(prompt_text) > 160:
            errors.append(f"Question {index} is too long for a one-page layout.")
        options = question.get("options")
        if not isinstance(options, dict):
            errors.append(f"Question {index} is missing its options.")
            continue
        normalized_options: dict[str, str] = {}
        for label in ("A", "B", "C", "D"):
            option_text = normalize_whitespace(str(options.get(label, "")))
            if not option_text:
                errors.append(f"Question {index} is missing option {label}.")
            if len(option_text) > 100:
                errors.append(f"Option {label} in question {index} is too long for a one-page layout.")
            normalized_options[label] = option_text
        answer = str(question.get("answer", "")).strip().upper()
        if answer not in {"A", "B", "C", "D"}:
            errors.append(f"Question {index} must have answer A, B, C, or D.")
        normalized_questions.append(
            {
                "number": index,
                "question": prompt_text,
                "options": normalized_options,
                "answer": answer,
            }
        )
        answers.append({"number": index, "answer": answer})

    focus_words = select_focus_words(page.words)
    required_count = len(focus_words) if len(focus_words) <= 4 else min(5, len(focus_words))
    actual_used = infer_used_vocab(passage, focus_words)
    if len(actual_used) < required_count:
        errors.append(
            f"The passage must use at least {required_count} focus words, but only {len(actual_used)} were found."
        )

    difficulty_notes = normalize_whitespace(str(draft.get("difficulty_notes", "")))
    if not difficulty_notes:
        errors.append("difficulty_notes is missing.")

    normalized = {
        "passage": passage,
        "passage_word_count": word_count,
        "questions": normalized_questions,
        "answers": answers,
        "used_vocab": actual_used,
        "difficulty_notes": difficulty_notes,
    }
    return errors, normalized


def generate_one_reading(
    client: OpenAICompatibleClient,
    page: VocabPage,
    batch_id: str,
    temperature: float,
    max_attempts: int,
    sleep_seconds: float,
) -> dict[str, Any]:
    feedback: list[str] = []
    last_error = "Unknown generation failure."
    for attempt in range(1, max_attempts + 1):
        prompt = build_prompt(page, batch_id, feedback)
        try:
            draft = client.generate_json(prompt, temperature=temperature)
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            if attempt < max_attempts:
                time.sleep(sleep_seconds)
                continue
            raise RuntimeError(last_error) from exc

        validation_errors, normalized = validate_reading(draft, page)
        if not validation_errors:
            normalized.update(
                {
                    "title": build_title(page.page_number, batch_id),
                    "page_number": page.page_number,
                    "lesson_number": page.lesson_number,
                    "focus_words": [
                        {"term": entry.term, "gloss": entry.gloss}
                        for entry in select_focus_words(page.words)
                    ],
                    "source_words": [
                        {"term": entry.term, "gloss": entry.gloss}
                        for entry in page.words
                    ],
                }
            )
            return normalized
        feedback = validation_errors
        last_error = "; ".join(validation_errors)
        if attempt < max_attempts:
            time.sleep(sleep_seconds)
    raise RuntimeError(last_error)


def ensure_cjk_font() -> str:
    font_name = "STSong-Light"
    try:
        pdfmetrics.getFont(font_name)
    except KeyError:
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    return font_name


def wrap_lines(text: str, font_name: str, font_size: float, width: float) -> list[str]:
    paragraphs = text.split("\n")
    lines: list[str] = []
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        lines.extend(simpleSplit(paragraph, font_name, font_size, width))
    return lines


def estimate_layout(reading: dict[str, Any], cjk_font: str, body_font_size: float) -> tuple[bool, dict[str, Any]]:
    page_width, page_height = A4
    left_margin = 16 * mm
    right_margin = 16 * mm
    top_margin = 16 * mm
    bottom_margin = 14 * mm
    body_width = page_width - left_margin - right_margin
    y = page_height - top_margin
    title_font_size = body_font_size + 3
    heading_font_size = body_font_size + 1
    leading = body_font_size + 2
    title_lines = wrap_lines(reading["title"], cjk_font, title_font_size, body_width)
    y -= len(title_lines) * (title_font_size + 2)
    y -= 6

    sections = [
        ("--- READING PASSAGE ---", wrap_lines(reading["passage"], "Helvetica", body_font_size, body_width)),
    ]
    question_lines: list[str] = []
    for question in reading["questions"]:
        question_lines.extend(wrap_lines(f"{question['number']}. {question['question']}", "Helvetica-Bold", body_font_size, body_width))
        for label in ("A", "B", "C", "D"):
            question_lines.extend(wrap_lines(f"   {label}) {question['options'][label]}", "Helvetica", body_font_size, body_width - 4))
        question_lines.append("")
    sections.append(("--- QUESTIONS ---", question_lines))
    answer_lines = [f"{item['number']}. {item['answer']}" for item in reading["answers"]]
    sections.append(("--- ANSWERS ---", answer_lines))

    for heading, lines in sections:
        y -= heading_font_size + 4
        for line in lines:
            y -= leading if line else leading * 0.6
        y -= 6
    fits = y >= bottom_margin
    return fits, {
        "page_width": page_width,
        "page_height": page_height,
        "left_margin": left_margin,
        "right_margin": right_margin,
        "top_margin": top_margin,
        "bottom_margin": bottom_margin,
        "body_width": body_width,
        "title_font_size": title_font_size,
        "heading_font_size": heading_font_size,
        "body_font_size": body_font_size,
        "leading": leading,
    }


def draw_lines(
    pdf: canvas.Canvas,
    lines: list[str],
    x: float,
    y: float,
    font_name: str,
    font_size: float,
    leading: float,
) -> float:
    pdf.setFont(font_name, font_size)
    for line in lines:
        if line:
            pdf.drawString(x, y, line)
            y -= leading
        else:
            y -= leading * 0.6
    return y


def render_pdf(readings: list[dict[str, Any]], output_pdf: Path) -> None:
    cjk_font = ensure_cjk_font()
    pdf = canvas.Canvas(str(output_pdf), pagesize=A4)
    for reading in readings:
        chosen_layout: dict[str, Any] | None = None
        for body_font_size in (10.0, 9.5, 9.0, 8.5):
            fits, layout = estimate_layout(reading, cjk_font, body_font_size)
            if fits:
                chosen_layout = layout
                break
        if chosen_layout is None:
            raise RuntimeError(
                f"Reading page {reading['page_number']} is too long to fit on one PDF page."
            )

        layout = chosen_layout
        x = layout["left_margin"]
        y = layout["page_height"] - layout["top_margin"]
        title_lines = wrap_lines(reading["title"], cjk_font, layout["title_font_size"], layout["body_width"])
        pdf.setFont(cjk_font, layout["title_font_size"])
        for line in title_lines:
            pdf.drawString(x, y, line)
            y -= layout["title_font_size"] + 2
        y -= 6

        pdf.setFont("Helvetica-Bold", layout["heading_font_size"])
        pdf.drawString(x, y, "--- READING PASSAGE ---")
        y -= layout["heading_font_size"] + 4
        passage_lines = wrap_lines(reading["passage"], "Helvetica", layout["body_font_size"], layout["body_width"])
        y = draw_lines(pdf, passage_lines, x, y, "Helvetica", layout["body_font_size"], layout["leading"])
        y -= 6

        pdf.setFont("Helvetica-Bold", layout["heading_font_size"])
        pdf.drawString(x, y, "--- QUESTIONS ---")
        y -= layout["heading_font_size"] + 4
        for question in reading["questions"]:
            question_lines = wrap_lines(
                f"{question['number']}. {question['question']}",
                "Helvetica-Bold",
                layout["body_font_size"],
                layout["body_width"],
            )
            y = draw_lines(
                pdf,
                question_lines,
                x,
                y,
                "Helvetica-Bold",
                layout["body_font_size"],
                layout["leading"],
            )
            for label in ("A", "B", "C", "D"):
                option_lines = wrap_lines(
                    f"   {label}) {question['options'][label]}",
                    "Helvetica",
                    layout["body_font_size"],
                    layout["body_width"] - 4,
                )
                y = draw_lines(
                    pdf,
                    option_lines,
                    x,
                    y,
                    "Helvetica",
                    layout["body_font_size"],
                    layout["leading"],
                )
            y -= layout["leading"] * 0.4

        y -= 4
        pdf.setFont("Helvetica-Bold", layout["heading_font_size"])
        pdf.drawString(x, y, "--- ANSWERS ---")
        y -= layout["heading_font_size"] + 4
        answer_lines = [f"{item['number']}. {item['answer']}" for item in reading["answers"]]
        y = draw_lines(
            pdf,
            answer_lines,
            x,
            y,
            "Helvetica",
            layout["body_font_size"],
            layout["leading"],
        )

        pdf.setFont("Helvetica", 8)
        footer = f"Page {reading['page_number']}  |  PET reading worksheet batch {reading['title'].split('_')[-1]}"
        pdf.drawRightString(layout["page_width"] - layout["right_margin"], 10 * mm, footer)
        pdf.showPage()
    pdf.save()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_existing_readings(raw_dir: Path) -> dict[int, dict[str, Any]]:
    existing: dict[int, dict[str, Any]] = {}
    if not raw_dir.exists():
        return existing
    for file_path in raw_dir.glob("page_*.json"):
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        page_number = int(payload["page_number"])
        existing[page_number] = payload
    return existing


def build_command(args: argparse.Namespace) -> int:
    source_pdf = Path(args.source_pdf).expanduser().resolve()
    if not source_pdf.exists():
        raise FileNotFoundError(f"Source PDF does not exist: {source_pdf}")

    batch_id = args.batch_id or datetime.now().strftime("%m%d%H%M")
    output_dir = Path(args.output_dir).expanduser().resolve()
    raw_dir = output_dir / RAW_DIR_NAME.format(batch_id=batch_id)
    vocab_output = output_dir / VOCAB_JSON_NAME.format(batch_id=batch_id)
    combined_output = output_dir / OUTPUT_JSON_NAME.format(batch_id=batch_id)
    pdf_output = output_dir / OUTPUT_PDF_NAME.format(batch_id=batch_id)

    pages = extract_vocab_pages(source_pdf)
    vocab_payload = {
        "source_pdf": str(source_pdf),
        "batch_id": batch_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_pages": len(pages),
        "pages": [
            {
                "page_number": page.page_number,
                "lesson_number": page.lesson_number,
                "word_count": len(page.words),
                "focus_words": [
                    {"term": entry.term, "gloss": entry.gloss}
                    for entry in select_focus_words(page.words)
                ],
                "words": [{"term": entry.term, "gloss": entry.gloss} for entry in page.words],
            }
            for page in pages
        ],
    }
    write_json(vocab_output, vocab_payload)

    start_page = max(1, args.start_page)
    end_page = min(len(pages), args.end_page or len(pages))
    target_pages = [page for page in pages if start_page <= page.page_number <= end_page]

    existing = load_existing_readings(raw_dir)
    readings_by_page: dict[int, dict[str, Any]] = dict(existing)

    if not args.render_only:
        api_key = args.api_key or ""
        if not api_key:
            raise RuntimeError(
                "No API key was provided. Pass --api-key or set OPENAI_API_KEY before running build."
            )
        if not args.model:
            raise RuntimeError(
                "No model was provided. Pass --model or set OPENAI_MODEL before running build."
            )
        client = OpenAICompatibleClient(
            base_url=args.base_url,
            api_key=api_key,
            model=args.model,
            timeout=args.timeout,
        )
        for page in target_pages:
            page_output = raw_dir / f"page_{page.page_number:03d}.json"
            if page.page_number in readings_by_page and not args.force:
                print(f"[skip] page {page.page_number}: existing reading found", flush=True)
                continue
            print(f"[generate] page {page.page_number}/{len(pages)}", flush=True)
            reading = generate_one_reading(
                client=client,
                page=page,
                batch_id=batch_id,
                temperature=args.temperature,
                max_attempts=args.max_attempts,
                sleep_seconds=args.sleep_seconds,
            )
            readings_by_page[page.page_number] = reading
            write_json(page_output, reading)
            if args.sleep_seconds:
                time.sleep(args.sleep_seconds)

    missing_pages = [page.page_number for page in target_pages if page.page_number not in readings_by_page]
    if missing_pages:
        raise RuntimeError(
            "Cannot render PDF because some page readings are still missing: "
            + ", ".join(str(item) for item in missing_pages)
        )

    ordered_readings = [readings_by_page[page.page_number] for page in target_pages]
    combined_payload = {
        "source_pdf": str(source_pdf),
        "batch_id": batch_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "start_page": start_page,
        "end_page": end_page,
        "total_readings": len(ordered_readings),
        "readings": ordered_readings,
    }
    write_json(combined_output, combined_payload)
    print(f"[done] vocab json: {vocab_output}")
    print(f"[done] readings json: {combined_output}")
    if not args.no_render:
        render_pdf(ordered_readings, pdf_output)
        print(f"[done] output pdf: {pdf_output}")
    return 0


def extract_command(args: argparse.Namespace) -> int:
    source_pdf = Path(args.source_pdf).expanduser().resolve()
    output_json = Path(args.output_json).expanduser().resolve()
    pages = extract_vocab_pages(source_pdf)
    payload = {
        "source_pdf": str(source_pdf),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_pages": len(pages),
        "pages": [
            {
                "page_number": page.page_number,
                "lesson_number": page.lesson_number,
                "word_count": len(page.words),
                "focus_words": [
                    {"term": entry.term, "gloss": entry.gloss}
                    for entry in select_focus_words(page.words)
                ],
                "words": [{"term": entry.term, "gloss": entry.gloss} for entry in page.words],
            }
            for page in pages
        ],
    }
    write_json(output_json, payload)
    print(f"[done] extracted {len(pages)} pages to {output_json}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate PET reading worksheets from a vocabulary PDF.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract vocabulary from the source PDF.")
    extract_parser.add_argument("--source-pdf", required=True, help="Path to the source PET vocabulary PDF.")
    extract_parser.add_argument("--output-json", required=True, help="Path to write the extracted vocabulary JSON.")
    extract_parser.set_defaults(handler=extract_command)

    build_parser_ = subparsers.add_parser("build", help="Generate PET reading worksheets and render the PDF.")
    build_parser_.add_argument("--source-pdf", required=True, help="Path to the source PET vocabulary PDF.")
    build_parser_.add_argument("--output-dir", default="output", help="Directory for JSON and PDF outputs.")
    build_parser_.add_argument("--model", default="", help="OpenAI-compatible chat model name.")
    build_parser_.add_argument("--base-url", default="", help="OpenAI-compatible base URL.")
    build_parser_.add_argument("--api-key", default="", help="API key for the OpenAI-compatible endpoint.")
    build_parser_.add_argument("--batch-id", default="", help="Optional 8-digit batch id used in page titles.")
    build_parser_.add_argument("--temperature", type=float, default=0.8, help="Sampling temperature.")
    build_parser_.add_argument("--max-attempts", type=int, default=4, help="Maximum retries per page.")
    build_parser_.add_argument("--sleep-seconds", type=float, default=1.0, help="Delay between attempts and pages.")
    build_parser_.add_argument("--timeout", type=int, default=120, help="HTTP timeout for each LLM request.")
    build_parser_.add_argument("--start-page", type=int, default=1, help="First source page to process.")
    build_parser_.add_argument("--end-page", type=int, default=0, help="Last source page to process; 0 means all.")
    build_parser_.add_argument("--render-only", action="store_true", help="Skip generation and only render from saved JSON.")
    build_parser_.add_argument("--no-render", action="store_true", help="Generate and cache JSON only, without rendering the PDF.")
    build_parser_.add_argument("--force", action="store_true", help="Regenerate pages even if cached JSON exists.")
    build_parser_.set_defaults(handler=build_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "end_page", None):
        args.end_page = None
    if hasattr(args, "api_key") and not args.api_key:
        args.api_key = os.environ.get("OPENAI_API_KEY", "")
    if hasattr(args, "model") and not args.model:
        args.model = os.environ.get("OPENAI_MODEL", "")
    if hasattr(args, "base_url") and not args.base_url:
        args.base_url = os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="/Users/xzhan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
SCRIPT="/Users/xzhan/vibcoding/EnglishTest/scripts/pet_reading_pipeline.py"
SOURCE_PDF="/Users/aistudio/PET/PET全.pdf"
OUTPUT_DIR="/Users/xzhan/vibcoding/EnglishTest/output"
BATCH_ID="04221021"

if [[ -z "${OPENAI_API_KEY:-}" || -z "${OPENAI_MODEL:-}" ]]; then
  echo "Set OPENAI_API_KEY and OPENAI_MODEL first. OPENAI_BASE_URL is optional."
  exit 1
fi

"$PYTHON_BIN" "$SCRIPT" build \
  --source-pdf "$SOURCE_PDF" \
  --output-dir "$OUTPUT_DIR" \
  --batch-id "$BATCH_ID" \
  --start-page 16 \
  --end-page 26 \
  --max-attempts 8 \
  --sleep-seconds 0.2 \
  --no-render

"$PYTHON_BIN" "$SCRIPT" build \
  --source-pdf "$SOURCE_PDF" \
  --output-dir "$OUTPUT_DIR" \
  --batch-id "$BATCH_ID" \
  --start-page 46 \
  --end-page 46 \
  --max-attempts 8 \
  --sleep-seconds 0.2 \
  --no-render

"$PYTHON_BIN" "$SCRIPT" build \
  --source-pdf "$SOURCE_PDF" \
  --output-dir "$OUTPUT_DIR" \
  --batch-id "$BATCH_ID" \
  --start-page 56 \
  --end-page 66 \
  --max-attempts 8 \
  --sleep-seconds 0.2 \
  --no-render

"$PYTHON_BIN" "$SCRIPT" build \
  --source-pdf "$SOURCE_PDF" \
  --output-dir "$OUTPUT_DIR" \
  --batch-id "$BATCH_ID" \
  --start-page 1 \
  --end-page 66 \
  --render-only

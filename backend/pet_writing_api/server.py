"""HTTP server for the PET Writing MVP backend."""

from __future__ import annotations

import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from backend.pet_reading_api.service import ReadingService
from backend.pet_reading_api.storage import ReadingStorage

from .service import ServiceError, WritingService
from .storage import Storage


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length > 0 else b"{}"
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ServiceError("INVALID_JSON", "Request body must be valid JSON.", status=400) from exc


def make_handler(service: WritingService, reading_service: ReadingService) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _dispatch(self) -> None:
            parsed = urlparse(self.path)
            method = self.command
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)
            try:
                if method == "GET" and path == "/api/v1/health":
                    json_response(self, 200, {"status": "ok"})
                    return
                if method == "POST" and path == "/api/v1/reading/assessments":
                    body = read_json_body(self)
                    json_response(
                        self,
                        201,
                        reading_service.create_assessment(
                            student_id=body["student_id"],
                            grade_level=body.get("grade_level"),
                        ),
                    )
                    return
                if method == "GET" and path.startswith("/api/v1/reading/assessments/") and path.endswith("/next"):
                    assessment_id = path.split("/")[-2]
                    json_response(self, 200, reading_service.get_next_passage(assessment_id))
                    return
                if method == "POST" and path.startswith("/api/v1/reading/assessments/") and path.endswith("/responses"):
                    assessment_id = path.split("/")[-2]
                    body = read_json_body(self)
                    json_response(
                        self,
                        200,
                        reading_service.submit_responses(
                            assessment_id=assessment_id,
                            passage_id=body["passage_id"],
                            time_spent_sec=int(body.get("time_spent_sec", 0)),
                            responses=body["responses"],
                        ),
                    )
                    return
                if method == "POST" and path.startswith("/api/v1/reading/assessments/") and path.endswith("/complete"):
                    assessment_id = path.split("/")[-2]
                    json_response(self, 200, reading_service.complete_assessment(assessment_id))
                    return
                if method == "GET" and path.startswith("/api/v1/reading/assessments/") and path.endswith("/report"):
                    assessment_id = path.split("/")[-2]
                    json_response(self, 200, reading_service.get_report(assessment_id))
                    return
                if method == "GET" and path == "/api/v1/writing/prompts":
                    task_type = query.get("task_type", [None])[0]
                    limit = int(query.get("limit", ["20"])[0])
                    json_response(self, 200, service.list_prompts(task_type=task_type, limit=limit))
                    return
                if method == "GET" and path.startswith("/api/v1/writing/prompts/"):
                    prompt_id = path.split("/")[-1]
                    json_response(self, 200, service.get_prompt(prompt_id))
                    return
                if method == "POST" and path == "/api/v1/writing/prescore":
                    body = read_json_body(self)
                    json_response(
                        self,
                        200,
                        service.prescore(
                            prompt_id=body["prompt_id"],
                            text=body["text"],
                            time_spent_sec=int(body.get("time_spent_sec", 0)),
                            word_count_client=body.get("word_count_client"),
                        ),
                    )
                    return
                if method == "POST" and path == "/api/v1/writing/attempts":
                    body = read_json_body(self)
                    json_response(
                        self,
                        201,
                        service.create_attempt(
                            student_id=body["student_id"],
                            prompt_id=body["prompt_id"],
                        ),
                    )
                    return
                if method == "GET" and path.startswith("/api/v1/writing/attempts/") and not path.endswith("/comparison"):
                    attempt_id = path.split("/")[-1]
                    json_response(self, 200, service.get_attempt(attempt_id))
                    return
                if method == "PUT" and path.endswith("/draft"):
                    attempt_id = path.split("/")[-2]
                    body = read_json_body(self)
                    json_response(
                        self,
                        200,
                        service.save_draft(
                            attempt_id=attempt_id,
                            draft_number=int(body["draft_number"]),
                            text=body["text"],
                            time_spent_sec=int(body.get("time_spent_sec", 0)),
                        ),
                    )
                    return
                if method == "POST" and path.endswith("/submissions"):
                    attempt_id = path.split("/")[-2]
                    body = read_json_body(self)
                    json_response(
                        self,
                        201,
                        service.submit_draft(
                            attempt_id=attempt_id,
                            draft_number=int(body["draft_number"]),
                            text=body["text"],
                            time_spent_sec=int(body.get("time_spent_sec", 0)),
                            word_count_client=body.get("word_count_client"),
                        ),
                    )
                    return
                if method == "POST" and path.endswith("/rewrite"):
                    attempt_id = path.split("/")[-2]
                    json_response(self, 200, service.start_rewrite(attempt_id))
                    return
                if method == "GET" and path.endswith("/comparison"):
                    attempt_id = path.split("/")[-2]
                    json_response(self, 200, service.get_comparison(attempt_id))
                    return
                if method == "GET" and path.startswith("/api/v1/writing/submissions/") and path.endswith("/report"):
                    submission_id = path.split("/")[-2]
                    json_response(self, 200, service.get_report(submission_id))
                    return
                if method == "GET" and path.startswith("/api/v1/writing/submissions/"):
                    submission_id = path.split("/")[-1]
                    json_response(self, 200, service.get_submission(submission_id))
                    return
                if method == "GET" and "/writing/history" in path:
                    student_id = path.split("/")[-3]
                    limit = int(query.get("limit", ["20"])[0])
                    json_response(self, 200, service.get_history(student_id, limit=limit))
                    return
                if method == "GET" and path == "/api/v1/internal/writing/reviews/queue":
                    limit = int(query.get("limit", ["20"])[0])
                    json_response(self, 200, service.list_review_queue(limit=limit))
                    return
                if method == "POST" and path == "/api/v1/internal/writing/reviews":
                    body = read_json_body(self)
                    json_response(
                        self,
                        201,
                        service.add_review(
                            submission_id=body["submission_id"],
                            reviewer_id=body["reviewer_id"],
                            scores=body["scores"],
                            comment=body.get("comment"),
                        ),
                    )
                    return
                raise ServiceError("NOT_FOUND", f"No route for {method} {path}", status=404)
            except KeyError as exc:
                error = ServiceError("BAD_REQUEST", f"Missing required field: {exc.args[0]}", status=400)
                json_response(self, error.status, error.to_payload())
            except ValueError as exc:
                error = ServiceError("BAD_REQUEST", str(exc), status=400)
                json_response(self, error.status, error.to_payload())
            except ServiceError as exc:
                json_response(self, exc.status, exc.to_payload())
            except Exception as exc:  # pragma: no cover - safety net
                error = ServiceError("INTERNAL_ERROR", str(exc), status=500)
                json_response(self, error.status, error.to_payload())

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch()

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch()

        def do_PUT(self) -> None:  # noqa: N802
            self._dispatch()

        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    return Handler


def create_server(host: str, port: int, db_path: str) -> ThreadingHTTPServer:
    service = WritingService(Storage(db_path))
    reading_service = ReadingService(ReadingStorage(db_path))
    server = ThreadingHTTPServer((host, port), make_handler(service, reading_service))
    return server


def run_server(host: str, port: int, db_path: str) -> None:
    server = create_server(host=host, port=port, db_path=db_path)
    print(f"PET Writing backend running on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

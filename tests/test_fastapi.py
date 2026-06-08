import asyncio
import json

from backend.main import ApplicationServices, create_app
from config import Settings


def make_settings(tmp_path):
    return Settings(
        gemini_api_key="",
        gemini_model="gemini-2.5-flash",
        local_storage_path=tmp_path / "documents",
        sqlite_database_path=tmp_path / "loans.db",
        log_level="INFO",
        backend_host="127.0.0.1",
        backend_port=8000,
        cors_origins=("http://localhost:5173",),
    )


async def asgi_request(app, method, path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else b""
    request_sent = False
    messages = []

    async def receive():
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "state": {},
    }
    await app(scope, receive, send)
    response_start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"") for message in messages if message["type"] == "http.response.body"
    )
    return response_start["status"], json.loads(response_body) if response_body else None


def test_fastapi_routes_and_local_status_workflow(tmp_path):
    settings = make_settings(tmp_path)
    services = ApplicationServices.create(settings)
    customer = services.storage.customer_path("LID001")
    customer.mkdir(parents=True)
    (customer / "AA_data.json").write_text(json.dumps({"personal_info": {}}), encoding="utf-8")
    app = create_app(settings=settings, services=services)

    async def exercise_api():
        async with app.router.lifespan_context(app):
            status, health = await asgi_request(app, "GET", "/")
            assert status == 200
            assert health["message"].endswith("with FastAPI")

            status, customers = await asgi_request(app, "GET", "/customers")
            assert status == 200
            assert customers == {"customers": ["LID001"]}

            status, approval = await asgi_request(
                app,
                "POST",
                "/approve_loan",
                {"customer_id": "LID001"},
            )
            assert status == 200
            assert approval["status"] == "success"

            status, approved = await asgi_request(app, "GET", "/approved-loans")
            assert status == 200
            assert approved == {"approved_loans": ["LID001"]}

            status, invalid = await asgi_request(
                app,
                "POST",
                "/approve_loan",
                {"customer_id": "../outside"},
            )
            assert status == 422
            assert invalid["detail"]

    asyncio.run(exercise_api())


def test_fastapi_openapi_contract_is_preserved(tmp_path):
    settings = make_settings(tmp_path)
    app = create_app(settings=settings, services=ApplicationServices.create(settings))
    schema = app.openapi()

    expected_paths = {
        "/",
        "/customers",
        "/run_workflow",
        "/results/{customer_id}",
        "/gradcam/{customer_id}/{filename}",
        "/send_email",
        "/send_sms",
        "/escalate",
        "/approve_loan",
        "/approved-loans",
        "/human-escalations",
    }
    assert expected_paths <= set(schema["paths"])
    assert schema["info"]["title"] == "Loan Verification API"

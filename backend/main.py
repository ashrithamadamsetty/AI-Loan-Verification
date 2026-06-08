"""FastAPI application for the local loan-verification deployment."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
import logging
from pathlib import Path as FilePath
import shutil
import sys
import tempfile
from typing import Annotated, Any, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT_DIR = FilePath(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import Settings, get_settings
from local_database import LoanDatabase
from local_storage import LocalStorage

logger = logging.getLogger(__name__)
CustomerPath = Annotated[str, Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")]


@dataclass(frozen=True)
class ApplicationServices:
    """Local services used by FastAPI route handlers."""

    settings: Settings
    storage: LocalStorage
    database: LoanDatabase

    @classmethod
    def create(cls, settings: Settings | None = None) -> "ApplicationServices":
        resolved_settings = settings or get_settings()
        storage = LocalStorage(resolved_settings.local_storage_path)
        database = LoanDatabase(resolved_settings.sqlite_database_path)
        database.sync_customers(storage.list_customer_ids())
        return cls(settings=resolved_settings, storage=storage, database=database)

    def sync_customers(self) -> None:
        self.database.sync_customers(self.storage.list_customer_ids())

    def require_customer(self, customer_id: str) -> None:
        self.sync_customers()
        if not self.database.exists(customer_id) or not self.storage.customer_has_input_documents(customer_id):
            raise HTTPException(
                status_code=404,
                detail=f"Customer ID {customer_id} not found in local storage",
            )


class CustomerRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
    )

    @field_validator("customer_id")
    @classmethod
    def normalize_customer_id(cls, value: str) -> str:
        return value.strip()


class WorkflowRequest(CustomerRequest):
    pass


class WorkflowResponse(BaseModel):
    status: str
    results: dict[str, Any]
    errors: list[Any]


class ActionRequest(CustomerRequest):
    pass


def make_serializable(obj: Any) -> Any:
    """Convert workflow output and model objects into JSON-compatible values."""
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {key: make_serializable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_serializable(value) for value in obj]
    if hasattr(obj, "model_dump"):
        return make_serializable(obj.model_dump())
    if hasattr(obj, "to_dict"):
        return make_serializable(obj.to_dict())
    if hasattr(obj, "__dict__"):
        return make_serializable(vars(obj))
    return str(obj)


def get_services(request: Request) -> ApplicationServices:
    """Resolve application services initialized by the FastAPI lifespan."""
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise HTTPException(status_code=503, detail="Application services are not initialized")
    return services


Services = Annotated[ApplicationServices, Depends(get_services)]


def execute_workflow(customer_id: str, services: ApplicationServices) -> dict[str, Any]:
    """Execute the blocking OCR/ML workflow outside FastAPI's event loop."""
    from orchestration import VerificationOrchestrator

    temp_dir = FilePath(tempfile.mkdtemp(prefix=f"customer_{customer_id}_"))
    documents_folder = temp_dir / customer_id
    try:
        logger.info("Starting local workflow for customer %s", customer_id)
        services.storage.copy_customer_inputs(customer_id, documents_folder)
        results = VerificationOrchestrator(
            str(documents_folder),
            loan_id=customer_id,
            artifact_storage=services.storage,
        ).run_workflow()
        serializable = make_serializable(results)
        ui_results = {
            "status": serializable.get("status", "unknown"),
            "errors": serializable.get("errors", []),
            "results": serializable.get("results", {}),
        }
        services.storage.write_json(customer_id, "results.json", data=ui_results)
        return ui_results
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def create_app(
    settings: Settings | None = None,
    services: ApplicationServices | None = None,
) -> FastAPI:
    """Create the FastAPI app, allowing isolated local services in tests."""
    resolved_settings = settings or (services.settings if services else get_settings())

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.services = services or ApplicationServices.create(resolved_settings)
        logger.info(
            "FastAPI local services initialized: storage=%s database=%s",
            application.state.services.storage.root,
            application.state.services.database.path,
        )
        yield

    application = FastAPI(
        title="Loan Verification API",
        description="Local FastAPI backend for Gemini-powered loan verification.",
        version="2.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/", tags=["health"])
    async def root(local_services: Services) -> dict[str, str]:
        return {
            "message": "Loan Verification API is running locally with FastAPI",
            "storage_path": str(local_services.storage.root),
            "database_path": str(local_services.database.path),
            "gemini_model": local_services.settings.gemini_model,
        }

    @application.get("/customers", tags=["applications"])
    async def get_customers(local_services: Services) -> dict[str, list[str]]:
        local_services.sync_customers()
        return {"customers": local_services.database.list_by_status("new")}

    @application.post(
        "/run_workflow",
        response_model=WorkflowResponse,
        tags=["verification"],
    )
    async def run_workflow(
        payload: WorkflowRequest,
        local_services: Services,
    ) -> WorkflowResponse:
        local_services.require_customer(payload.customer_id)
        try:
            result = await run_in_threadpool(execute_workflow, payload.customer_id, local_services)
            return WorkflowResponse(**result)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Workflow execution failed for %s", payload.customer_id)
            raise HTTPException(status_code=500, detail=f"Workflow execution failed: {exc}") from exc

    @application.get("/results/{customer_id}", tags=["verification"])
    async def get_results(
        customer_id: CustomerPath,
        local_services: Services,
    ) -> dict[str, Any]:
        local_services.require_customer(customer_id)
        results = local_services.storage.read_json(customer_id, "results.json")
        if results is None:
            results = local_services.storage.read_json(customer_id, "dummy_results.json")
        if results is None:
            raise HTTPException(status_code=404, detail=f"Results not found for customer {customer_id}")
        return results

    @application.get("/gradcam/{customer_id}/{filename}", tags=["artifacts"])
    async def get_gradcam_image(
        customer_id: CustomerPath,
        filename: Annotated[str, Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,254}$")],
        local_services: Services,
    ) -> FileResponse:
        local_services.require_customer(customer_id)
        image_path = local_services.storage.find_first(
            [
                (customer_id, "gradcam", filename),
                (customer_id, "offer_letter_gradcam", filename),
            ]
        )
        if image_path is None:
            raise HTTPException(status_code=404, detail=f"GradCAM image not found: {filename}")
        return FileResponse(image_path, media_type="image/png", filename=filename)

    @application.post("/send_email", tags=["actions"])
    async def send_email(
        payload: ActionRequest,
        local_services: Services,
    ) -> dict[str, str]:
        local_services.require_customer(payload.customer_id)
        logger.info("Local email notification requested for %s", payload.customer_id)
        return {
            "status": "success",
            "message": f"Email notification recorded locally for customer {payload.customer_id}",
            "customer_id": payload.customer_id,
        }

    @application.post("/send_sms", tags=["actions"])
    async def send_sms(
        payload: ActionRequest,
        local_services: Services,
    ) -> dict[str, str]:
        local_services.require_customer(payload.customer_id)
        logger.info("Local SMS notification requested for %s", payload.customer_id)
        return {
            "status": "success",
            "message": f"SMS notification recorded locally for customer {payload.customer_id}",
            "customer_id": payload.customer_id,
        }

    @application.post("/escalate", tags=["actions"])
    async def escalate_to_human(
        payload: ActionRequest,
        local_services: Services,
    ) -> dict[str, str]:
        local_services.require_customer(payload.customer_id)
        local_services.database.set_status(payload.customer_id, "escalated")
        logger.info("Customer %s escalated for human review", payload.customer_id)
        return {
            "status": "success",
            "message": f"Case escalated to human review for customer {payload.customer_id}",
            "customer_id": payload.customer_id,
        }

    @application.post("/approve_loan", tags=["actions"])
    async def approve_loan(
        payload: ActionRequest,
        local_services: Services,
    ) -> dict[str, str]:
        local_services.require_customer(payload.customer_id)
        local_services.database.set_status(payload.customer_id, "approved")
        logger.info("Loan approved for customer %s", payload.customer_id)
        return {
            "status": "success",
            "message": f"Loan approved for customer {payload.customer_id}",
            "customer_id": payload.customer_id,
        }

    @application.get("/approved-loans", tags=["applications"])
    async def get_approved_loans(local_services: Services) -> dict[str, list[str]]:
        return {"approved_loans": local_services.database.list_by_status("approved")}

    @application.get("/human-escalations", tags=["applications"])
    async def get_human_escalations(local_services: Services) -> dict[str, list[str]]:
        return {"escalations": local_services.database.list_by_status("escalated")}

    return application


settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
app = create_app(settings=settings)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.backend_host, port=settings.backend_port)

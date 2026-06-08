"""Safe local-filesystem replacement for the former object-storage integration."""

from pathlib import Path
import json
import shutil
from typing import Any, Iterable

from config import get_settings


class LocalStorage:
    def __init__(self, root: Path | str | None = None):
        self.root = Path(root or get_settings().local_storage_path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, *parts: str) -> Path:
        candidate = self.root.joinpath(*parts).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("Storage path must remain inside LOCAL_STORAGE_PATH")
        return candidate

    def customer_path(self, customer_id: str) -> Path:
        return self.path_for(customer_id)

    def list_customer_ids(self) -> list[str]:
        return sorted(path.name for path in self.root.iterdir() if path.is_dir() and not path.name.startswith("."))

    def customer_has_input_documents(self, customer_id: str) -> bool:
        folder = self.customer_path(customer_id)
        if not folder.is_dir():
            return False
        return any(
            path.is_file()
            and path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".json"}
            and "gradcam" not in path.parts
            for path in folder.rglob("*")
        )

    def copy_customer_inputs(self, customer_id: str, destination: Path | str) -> Path:
        source = self.customer_path(customer_id)
        if not source.is_dir():
            raise FileNotFoundError(f"No local documents found for customer {customer_id}")
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        for source_file in source.rglob("*"):
            relative = source_file.relative_to(source)
            if source_file.is_dir() or "gradcam" in relative.parts or relative.name in {
                "results.json", "final_results.json", "extracted_documents.json"
            }:
                continue
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target)
        return destination

    def read_json(self, *parts: str, default: Any = None) -> Any:
        path = self.path_for(*parts)
        if not path.exists():
            return default
        with path.open(encoding="utf-8") as file:
            return json.load(file)

    def write_json(self, *parts: str, data: Any) -> Path:
        path = self.path_for(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        temporary.replace(path)
        return path

    def write_bytes(self, *parts: str, data: bytes) -> Path:
        path = self.path_for(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def find_first(self, alternatives: Iterable[tuple[str, ...]]) -> Path | None:
        for parts in alternatives:
            path = self.path_for(*parts)
            if path.is_file():
                return path
        return None

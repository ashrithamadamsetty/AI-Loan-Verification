from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON_FILES = [
    path
    for path in ROOT.rglob("*.py")
    if ".venv" not in path.parts and "venv" not in path.parts and path.name != __file__.split("/")[-1]
]


def test_removed_cloud_sdks_are_not_imported():
    forbidden = ("boto" + "3", "boto" + "core", "langchain_" + "".join(chr(value) for value in (97, 119, 115)), "str" + "ands")
    findings = []
    for path in PYTHON_FILES:
        content = path.read_text(encoding="utf-8").lower()
        if any(name in content for name in forbidden):
            findings.append(str(path.relative_to(ROOT)))
    assert findings == []


def test_generative_calls_are_centralized():
    direct_call = ".models.generate_" + "content("
    direct_stream_call = ".models.generate_" + "content_stream("
    callers = []
    for path in PYTHON_FILES:
        if path.name == "gemini_service.py":
            continue
        content = path.read_text(encoding="utf-8")
        if direct_call in content or direct_stream_call in content:
            callers.append(str(path.relative_to(ROOT)))
    assert callers == []

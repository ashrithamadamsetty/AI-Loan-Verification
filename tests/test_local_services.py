from local_database import LoanDatabase
from local_storage import LocalStorage


def test_local_storage_round_trip_and_path_safety(tmp_path):
    storage = LocalStorage(tmp_path / "documents")
    output = storage.write_json("LID001", "results.json", data={"status": "success"})

    assert output.is_file()
    assert storage.read_json("LID001", "results.json") == {"status": "success"}
    assert storage.list_customer_ids() == ["LID001"]

    try:
        storage.path_for("..", "outside.json")
    except ValueError:
        pass
    else:
        raise AssertionError("Path traversal should be rejected")


def test_sqlite_status_transitions(tmp_path):
    database = LoanDatabase(tmp_path / "loans.db")
    database.add_application("LID001")
    assert database.list_by_status("new") == ["LID001"]

    database.set_status("LID001", "approved")
    assert database.list_by_status("new") == []
    assert database.list_by_status("approved") == ["LID001"]

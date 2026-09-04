from qfxaile.storage import JsonRequestStore


def test_store_recovers_from_invalid_json(tmp_path):
    path = tmp_path / "pending.json"
    path.write_text("{", encoding="utf-8")

    assert JsonRequestStore(path).load() == {}


def test_store_saves_and_loads_records(tmp_path):
    store = JsonRequestStore(tmp_path / "pending.json")
    records = {"42": {"type": "friend"}}

    store.save(records)

    assert store.load() == records

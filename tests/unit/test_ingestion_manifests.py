from cpgf.ingestion.manifests import file_record, load_manifest, write_manifest_atomic


def test_manifest_roundtrip_and_file_record(tmp_path):
    manifest = tmp_path / "manifest.json"
    write_manifest_atomic(manifest, {"a": 1})
    assert load_manifest(manifest) == {"a": 1}

    data_file = tmp_path / "data.txt"
    data_file.write_text("abc", encoding="utf-8")
    record = file_record(data_file)
    assert record["bytes"] == 3
    assert len(record["sha256"]) == 64

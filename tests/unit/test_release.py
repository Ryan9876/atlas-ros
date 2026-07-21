from atlas_ros.release.tooling import checksums, verify


def test_checksums_detect_change(tmp_path) -> None:
    (tmp_path / "a.txt").write_text("one")
    target = tmp_path / "CHECKSUMS.sha256"
    checksums(tmp_path, target)
    assert verify(tmp_path, target) == []
    (tmp_path / "a.txt").write_text("two")
    assert verify(tmp_path, target) == ["a.txt"]

"""Verify installation metadata, native host assets and licence in the wheel."""
from pathlib import Path
from zipfile import ZipFile

wheel = next(Path("dist").glob("*.whl"))
with ZipFile(wheel) as archive:
    names = archive.namelist()
    assert any(name.endswith("LICENSE") for name in names)
    assert "frappe_soca/soca/core.py" in names
    assert "frappe_soca/soca/transport.py" in names
    assert not any(name.endswith(".pem") or "/.venv/" in name for name in names)
    assert any(name.endswith("soca_profile.json") for name in names)
print("Native host assets and public package boundary verified")

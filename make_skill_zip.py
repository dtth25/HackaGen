import zipfile
from pathlib import Path

base = Path(r"D:\DTTH-Hackathon-2026-AI-Course-Generator\claude_skill_build")
skill_dir = base / "study-pack-upgrade"
zip_path = Path(r"D:\DTTH-Hackathon-2026-AI-Course-Generator\study-pack-upgrade.zip")

if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for path in skill_dir.rglob("*"):
        if path.is_file():
            arcname = path.relative_to(base).as_posix()
            z.write(path, arcname)

print("Created:", zip_path)
print("ZIP entries:")
with zipfile.ZipFile(zip_path, "r") as z:
    for name in z.namelist():
        print(repr(name))

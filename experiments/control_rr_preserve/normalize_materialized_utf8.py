from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    "OptiScaler.ini",
    "OptiScaler/Config.cpp",
    "OptiScaler/Config.h",
    "OptiScaler/dllmain.cpp",
    "OptiScaler/hooks/Streamline_Hooks.cpp",
    "OptiScaler/misc/Quirks.h",
    "OptiScaler/shaders/dlssnr/DlssNr_Dx12.cpp",
]

changed = []
for rel in TARGETS:
    path = ROOT / rel
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        path.write_bytes(data[3:])
        changed.append(rel)

if changed:
    print("Removed accidental UTF-8 BOM from:")
    for rel in changed:
        print(f"  {rel}")
else:
    print("Materialized files already use BOM-free UTF-8")

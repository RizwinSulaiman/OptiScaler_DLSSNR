import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PINS = json.loads((Path(__file__).with_name("upstream_pins.json")).read_text(encoding="utf-8"))


def run(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


# The FSR SDK v2 gitlink is the public SDK 2.3.0 baseline: FSR 4.1.1, FG 4.0.1, RR 1.2.0.
fsr = PINS["fidelityfx_sdk_v2"]
actual_fsr = run("git", "rev-parse", "HEAD", cwd=ROOT / "external" / "FidelityFX-SDK-v2")
if actual_fsr != fsr["commit"]:
    raise RuntimeError(f"FidelityFX-SDK-v2 pin drift: expected {fsr['commit']}, got {actual_fsr}")

# The fork is heavily diverged from OptiScaler master, so FSR4 is synced by content contract rather than a blind merge.
for rel, expected_blob in PINS["optiscaler"]["fsr4_files_match_upstream"].items():
    actual_blob = run("git", "hash-object", rel)
    if actual_blob != expected_blob:
        raise RuntimeError(f"FSR4 source drift for {rel}: expected {expected_blob}, got {actual_blob}")

# The integration patch must include the current CONTROL safety contract before a cloud build is accepted.
checks = {
    "OptiScaler/misc/Quirks.h": [
        'QUIRK_ENTRY("controlresonant.exe"',
        "GameQuirk::DoNotPreserveFGSwapChain",
        "GameQuirk::DisableOTA",
    ],
    "OptiScaler/hooks/Streamline_Hooks.cpp": [
        "Config::Instance()->DisableOTA.value_or_default()",
        "sl::PreferenceFlags::eAllowOTA",
        "sl::PreferenceFlags::eLoadDownloadedPlugins",
    ],
    "OptiScaler/Config.h": ["CustomOptional<bool> DisableOTA { false };"],
}
for rel, needles in checks.items():
    text = (ROOT / rel).read_text(encoding="utf-8-sig")
    for needle in needles:
        if needle not in text:
            raise RuntimeError(f"{rel}: missing required CONTROL contract: {needle}")

print(
    "pins OK: FSR SDK 2.3.0 / FSR 4.1.1 / FG 4.0.1 / RR 1.2.0; "
    f"lmxxf source pin {PINS['lmxxf_rdna4']['source_commit'][:12]}"
)

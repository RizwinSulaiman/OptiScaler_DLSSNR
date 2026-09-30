import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PINS = json.loads((Path(__file__).with_name("upstream_pins.json")).read_text(encoding="utf-8"))


def run(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


# The FSR SDK v2 gitlink is the public SDK 2.3.0 baseline: FSR 4.1.1, FG 4.0.1, RR 1.2.0.
fsr = PINS["fidelityfx_sdk_v2"]
expected_fsr = ("2.3.0", "4.1.1", "4.0.1", "1.2.0")
actual_versions = (
    fsr["sdk_version"],
    fsr["fsr_upscaling"],
    fsr["fsr_frame_generation"],
    fsr["fsr_ray_regeneration"],
)
if actual_versions != expected_fsr:
    raise RuntimeError(f"Unexpected FSR contract: expected {expected_fsr}, got {actual_versions}")

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

# Quality-first governance for the late Sep-30 sync.  Stable and post-release refs are both recorded:
# stable is the reproducible package baseline; source_commit may move only to an explicitly accepted,
# bit-exact post-release production state.  Known lossy paths stay opt-in/off.
policy = PINS["policy"]
if not policy["quality_first"] or not policy["bit_exact_optimizations_default"]:
    raise RuntimeError("CONTROL upstream policy must stay quality-first with bit-exact optimizations enabled")
if policy["lossy_optimizations_default"]:
    raise RuntimeError("Lossy optimizations must not be enabled by default")

lmxxf = PINS["lmxxf_rdna4"]
if lmxxf["stable_release"] != "0.38":
    raise RuntimeError(f"Expected audited lmxxf stable release 0.38, got {lmxxf['stable_release']}")
if lmxxf["source_commit"] not in lmxxf["accepted_post_0_38_bit_exact_commits"]:
    raise RuntimeError("lmxxf source_commit must be one of the explicitly accepted post-0.38 bit-exact commits")
if lmxxf["stable_effect"]["lossy_1088_rows"] != "off by default":
    raise RuntimeError("Lossy 1088-row mode must remain off by default")

mochi = PINS["mochizuki_dlssnr_amd"]
if mochi["release"] != "v0.0.2.5" or not mochi["source_commit"]:
    raise RuntimeError("Mochizuki moving-picture reference is not pinned to v0.0.2.5")

theautomatic = PINS["theautomatic"]
if theautomatic["release"] != "v1.9.8.1" or not theautomatic["source_commit"]:
    raise RuntimeError("TheAutomatic integration reference is not pinned to v1.9.8.1")

print(
    "pins OK: FSR SDK 2.3.0 / FSR 4.1.1 / FG 4.0.1 / RR 1.2.0; "
    f"lmxxf stable {lmxxf['stable_release']} + accepted source {lmxxf['source_commit'][:12]}; "
    f"Mochizuki {mochi['release']}; TheAutomatic {theautomatic['release']}"
)

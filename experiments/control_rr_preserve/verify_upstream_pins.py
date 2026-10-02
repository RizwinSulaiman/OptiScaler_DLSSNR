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
    "OptiScaler/dlssnr/DlssNr_Proxy.cpp": [
        'SetUInt(params, "DLSSNR.DepthSubrectBaseX", depthBaseX)',
        'SetUInt(params, "DLSSNR.MVecSubrectBaseX", motionBaseX)',
    ],
    "OptiScaler/dlssnr/forwarder/dlssnr_forwarder.cpp": [
        'setUInt(capabilityParams, "DLSSNR.DepthSubrectBaseX", depthBaseX)',
        'setUInt(capabilityParams, "DLSSNR.MVecSubrectBaseX", motionBaseX)',
    ],
}
for rel, needles in checks.items():
    text = (ROOT / rel).read_text(encoding="utf-8-sig")
    for needle in needles:
        if needle not in text:
            raise RuntimeError(f"{rel}: missing required CONTROL contract: {needle}")

# Quality-first governance. Stable and post-release refs are both recorded:
# stable is the reproducible package baseline; source_commit may move only to an explicitly accepted,
# bit-exact post-release production state. Known lossy paths stay opt-in/off.
policy = PINS["policy"]
if not policy["quality_first"] or not policy["bit_exact_optimizations_default"]:
    raise RuntimeError("CONTROL upstream policy must stay quality-first with bit-exact optimizations enabled")
if policy["lossy_optimizations_default"]:
    raise RuntimeError("Lossy optimizations must not be enabled by default")

lmxxf = PINS["lmxxf_rdna4"]
if lmxxf["stable_release"] != "0.39":
    raise RuntimeError(f"Expected audited lmxxf stable release 0.39, got {lmxxf['stable_release']}")
if lmxxf["source_commit"] not in lmxxf["accepted_post_0_38_bit_exact_commits"]:
    raise RuntimeError("lmxxf source_commit must be one of the explicitly accepted post-0.38 bit-exact commits")
if lmxxf["source_commit"] != "0edf4bd86e55598e986ef533ba78a22120779bb6":
    raise RuntimeError("lmxxf quality-safe production pin must be the validated 0edf4bd install state")
if lmxxf["latest_repo_commit_seen"] != "8af862408ae477f4d207304419483919f1a0d3f2":
    raise RuntimeError("lmxxf latest-seen pin is stale")
if lmxxf["stable_effect"]["lossy_1088_rows"] != "off by default":
    raise RuntimeError("Lossy 1088-row mode must remain off by default")
if not any(item.get("commit") == "5a7cd0ba3a4ef8cbaf108a870994b5d7e7ea17cd" for item in lmxxf["do_not_enable_by_default"]):
    raise RuntimeError("Shelved lmxxf lossy fast-tier commit must remain explicitly excluded")

mochi = PINS["mochizuki_dlssnr_amd"]
if mochi["release"] != "v0.0.3" or not mochi["source_commit"]:
    raise RuntimeError("Mochizuki moving-picture reference is not pinned to v0.0.3")

theautomatic = PINS["theautomatic"]
if theautomatic["release"] != "v1.9.9.1" or not theautomatic["source_commit"]:
    raise RuntimeError("TheAutomatic integration reference is not pinned to v1.9.9.1")
if not theautomatic.get("daniel_0_5_1_layout_supported"):
    raise RuntimeError("TheAutomatic reference must record Daniel 0.5.1 layout support")

amdnr = PINS["amdnr"]
if amdnr["core_release"] != "0.3.5" or amdnr.get("core_release_tag") != "Alpha0.3.5":
    raise RuntimeError("AMDNR core baseline must be the public 0.3.5 release")
if not amdnr.get("future_core_0_3_5_public"):
    raise RuntimeError("AMDNR 0.3.5 must be recorded as public")
if not amdnr.get("core_release_commit") or not amdnr.get("latest_repo_commit_seen"):
    raise RuntimeError("AMDNR release and latest-seen commits must both be pinned")
if not amdnr.get("full_source_public") or amdnr.get("full_source_snapshot_commit") != "a1818e87891cee0fe15fc4e6e3495746edcbf515":
    raise RuntimeError("AMDNR full-source snapshot pin is stale or missing")
if amdnr.get("daniel_runtime_supported") != "0.5.1":
    raise RuntimeError("AMDNR compatibility record must recognize public Daniel 0.5.1")

daniel = PINS["daniel_runtime"]
if daniel.get("public_release") != "0.5.1":
    raise RuntimeError("Daniel runtime baseline must be public 0.5.1")
if daniel.get("release_commit") != "ead70619c39278366030a7194aaf0634e6af59bb":
    raise RuntimeError("Daniel 0.5.1 release commit pin drift")
if "Reference" not in daniel.get("quality_policy", ""):
    raise RuntimeError("Daniel Reference mode must remain the CONTROL quality-first baseline")

print(
    "pins OK: FSR SDK 2.3.0 / FSR 4.1.1 / FG 4.0.1 / RR 1.2.0; "
    f"lmxxf stable {lmxxf['stable_release']} + exact source {lmxxf['source_commit'][:12]} "
    f"(latest seen {lmxxf['latest_repo_commit_seen'][:12]}); "
    f"Daniel {daniel['public_release']}; Mochizuki {mochi['release']}; "
    f"TheAutomatic {theautomatic['release']}; AMDNR {amdnr['core_release']}"
)

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8-sig")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one anchor, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8-sig")


# Phase-1 switches. Both default off, so applying this patch must not alter the normal frame path.
replace_once(
    "OptiScaler/Config.h",
    "    CustomOptional<bool> DlssNrEnabled { false };\n",
    "    CustomOptional<bool> DlssNrEnabled { false };\n"
    "    // CONTROL/RR-preserve experiment. Phase 1 is diagnostics only; no rendering behavior changes.\n"
    "    CustomOptional<bool> DlssNrControlDiagnostics { false };\n"
    "    CustomOptional<bool> DlssNrControlRrPreserveExperimental { false };\n",
)

replace_once(
    "OptiScaler/Config.cpp",
    '            DlssNrEnabled.set_from_config(readBool("DlssNr", "Enabled"));\n',
    '            DlssNrEnabled.set_from_config(readBool("DlssNr", "Enabled"));\n'
    '            DlssNrControlDiagnostics.set_from_config(readBool("DlssNr", "ControlDiagnostics"));\n'
    '            DlssNrControlRrPreserveExperimental.set_from_config(\n'
    '                readBool("DlssNr", "ControlRrPreserveExperimental"));\n',
)

replace_once(
    "OptiScaler/Config.cpp",
    '    ini.SetValue("DlssNr", "Enabled", GetBoolValue(Instance()->DlssNrEnabled.value_for_config()).c_str());\n',
    '    ini.SetValue("DlssNr", "Enabled", GetBoolValue(Instance()->DlssNrEnabled.value_for_config()).c_str());\n'
    '    ini.SetValue("DlssNr", "ControlDiagnostics",\n'
    '                 GetBoolValue(Instance()->DlssNrControlDiagnostics.value_for_config()).c_str());\n'
    '    ini.SetValue("DlssNr", "ControlRrPreserveExperimental",\n'
    '                 GetBoolValue(Instance()->DlssNrControlRrPreserveExperimental.value_for_config()).c_str());\n',
)

# CONTROL's active rectangle is a first-class diagnostic because the game/texture allocation may disagree.
# Log only when the tuple changes so this is usable in a normal capture without per-frame spam.
anchor = '''    if (cfg.DlssNrProxyProbe.value_or_default())
        ProbeProxyDispatch(cmdList);
'''
insert = '''    if (cfg.DlssNrControlDiagnostics.value_or_default())
    {
        const D3D12_RESOURCE_DESC depthDiag = depth->GetDesc();
        const D3D12_RESOURCE_DESC motionDiag = motion->GetDesc();
        struct ControlDiagState
        {
            unsigned int outW = 0, outH = 0, subW = 0, subH = 0;
            unsigned int depthW = 0, depthH = 0, motionW = 0, motionH = 0;
            unsigned int guideW = 0, guideH = 0;
            float mvX = 0.0f, mvY = 0.0f;
            bool inverted = false, valid = false;
        };
        static ControlDiagState last {};
        ControlDiagState now {
            width, (unsigned int) height, frame.RenderSubrectWidth, frame.RenderSubrectHeight,
            (unsigned int) depthDiag.Width, depthDiag.Height,
            (unsigned int) motionDiag.Width, motionDiag.Height,
            guideWidth, guideHeight, frame.MvScaleX, frame.MvScaleY, frame.DepthInverted, true
        };
        if (!last.valid || std::memcmp(&last, &now, sizeof(ControlDiagState)) != 0)
        {
            last = now;
            LOG_INFO("CONTROL NR diag: output {}x{}, render subrect {}x{}, depth {}x{}, motion {}x{}, "
                     "active guides {}x{}, MV scale {}x{}, depth {}, reset {}",
                     now.outW, now.outH, now.subW, now.subH, now.depthW, now.depthH,
                     now.motionW, now.motionH, now.guideW, now.guideH, now.mvX, now.mvY,
                     now.inverted ? "inverted" : "normal", frame.Reset);
        }

        if (cfg.DlssNrControlRrPreserveExperimental.value_or_default())
            LOG_DEBUG("CONTROL RR-preserve gate enabled; phase-1 build remains diagnostics-only");
    }

''' + anchor
replace_once("OptiScaler/shaders/dlssnr/DlssNr_Dx12.cpp", anchor, insert)

print("CONTROL RR-preserve phase-1 integration patch applied")

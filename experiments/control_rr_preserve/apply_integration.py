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

# Pull in the current upstream CONTROL Resonant stability quirks without merging the entire
# upstream OptiScaler history into the heavily-diverged DLSS-NR branch. These are intentionally
# small, exact, and idempotent.
replace_once(
    "OptiScaler/Config.h",
    "    CustomOptional<bool> DisableFlipMetering { false };\n",
    "    CustomOptional<bool> DisableFlipMetering { false };\n"
    "    CustomOptional<bool> DisableOTA { false };\n",
)

replace_once(
    "OptiScaler/Config.cpp",
    '            DisableFlipMetering.set_from_config(readBool("NvApi", "DisableFlipMetering"));\n',
    '            DisableFlipMetering.set_from_config(readBool("NvApi", "DisableFlipMetering"));\n'
    '            DisableOTA.set_from_config(readBool("NvApi", "DisableOTA"));\n',
)

replace_once(
    "OptiScaler/Config.cpp",
    '        ini.SetValue("NvApi", "DisableFlipMetering",\n'
    '                     GetBoolValue(Instance()->DisableFlipMetering.value_for_config()).c_str());\n',
    '        ini.SetValue("NvApi", "DisableFlipMetering",\n'
    '                     GetBoolValue(Instance()->DisableFlipMetering.value_for_config()).c_str());\n'
    '        ini.SetValue("NvApi", "DisableOTA", GetBoolValue(Instance()->DisableOTA.value_for_config()).c_str());\n',
)

replace_once(
    "OptiScaler.ini",
    "DisableFlipMetering=auto\n\n\n\n; -------------------------------------------------------\n[Dx11withDx12]\n",
    "DisableFlipMetering=auto\n\n"
    "; Disables OTA of Streamline plugins. CONTROL Resonant enables this automatically via its game quirk.\n"
    "; true or false - Default (auto) is false\n"
    "DisableOTA=auto\n\n\n\n; -------------------------------------------------------\n[Dx11withDx12]\n",
)

replace_once(
    "OptiScaler/hooks/Streamline_Hooks.cpp",
    '''    // To prevent mixed up OTA situations
    // if (State::Instance().activeFgOutput == FGOutput::DLSSG)
    //{
    //    localPref.flags &= ~sl::PreferenceFlags::eAllowOTA;
    //    localPref.flags &= ~sl::PreferenceFlags::eLoadDownloadedPlugins;
    //}
''',
    '''    // To prevent mixed up OTA situations. CONTROL Resonant enables this via its game quirk.
    if (Config::Instance()->DisableOTA.value_or_default())
    {
        localPref.flags &= ~sl::PreferenceFlags::eAllowOTA;
        localPref.flags &= ~sl::PreferenceFlags::eLoadDownloadedPlugins;
    }
''',
)

replace_once(
    "OptiScaler/misc/Quirks.h",
    "    DontUseUnrealColorBarriers,\n\n    // Quirks that are applied deeper in code\n",
    "    DontUseUnrealColorBarriers,\n"
    "    DisableOTA,\n\n"
    "    // Quirks that are applied deeper in code\n",
)

replace_once(
    "OptiScaler/misc/Quirks.h",
    '    QUIRK_ENTRY("control_dx12.exe", GameQuirk::DisableDxgiSpoofing, GameQuirk::ForceAutoExposure),\n'
    '    QUIRK_ENTRY("deathloop.exe", GameQuirk::DisableDxgiSpoofing),\n',
    '    QUIRK_ENTRY("control_dx12.exe", GameQuirk::DisableDxgiSpoofing, GameQuirk::ForceAutoExposure),\n\n'
    '    // CONTROL Resonant: Streamline spoofing is sufficient; preserving the FG swapchain and OTA plugins are unstable.\n'
    '    QUIRK_ENTRY("controlresonant.exe", GameQuirk::DisableDxgiSpoofing, GameQuirk::DoNotPreserveFGSwapChain,\n'
    '                GameQuirk::DisableOTA),\n\n'
    '    QUIRK_ENTRY("deathloop.exe", GameQuirk::DisableDxgiSpoofing),\n',
)

replace_once(
    "OptiScaler/dllmain.cpp",
    '    if (quirks & GameQuirk::CreateSLOnThe2ndDevice)\n'
    '        stringQuirks.push_back("Create SL on the 2nd device");\n\n'
    '    state->detectedQuirks.append_range(stringQuirks);\n',
    '    if (quirks & GameQuirk::CreateSLOnThe2ndDevice)\n'
    '        stringQuirks.push_back("Create SL on the 2nd device");\n\n'
    '    if (quirks & GameQuirk::DisableOTA)\n'
    '        stringQuirks.push_back("Disable Streamline OTA");\n\n'
    '    state->detectedQuirks.append_range(stringQuirks);\n',
)

replace_once(
    "OptiScaler/dllmain.cpp",
    '    if (quirks & GameQuirk::DoNotLoadAmdxc64 && !Config::Instance()->Fsr4DoNotLoadAmdxc64.has_value())\n'
    '    {\n'
    '        Config::Instance()->Fsr4DoNotLoadAmdxc64.set_volatile_value(true);\n'
    '    }\n'
    '    else\n'
    '        quirks.reset(GameQuirk::DoNotLoadAmdxc64);\n\n'
    '    // For Luma, we assume if Luma addon in game folder it\'s used\n',
    '    if (quirks & GameQuirk::DoNotLoadAmdxc64 && !Config::Instance()->Fsr4DoNotLoadAmdxc64.has_value())\n'
    '    {\n'
    '        Config::Instance()->Fsr4DoNotLoadAmdxc64.set_volatile_value(true);\n'
    '    }\n'
    '    else\n'
    '        quirks.reset(GameQuirk::DoNotLoadAmdxc64);\n\n'
    '    if (quirks & GameQuirk::DisableOTA && !Config::Instance()->DisableOTA.has_value())\n'
    '        Config::Instance()->DisableOTA.set_volatile_value(true);\n'
    '    else\n'
    '        quirks.reset(GameQuirk::DisableOTA);\n\n'
    '    // For Luma, we assume if Luma addon in game folder it\'s used\n',
)

print("CONTROL RR-preserve + current CONTROL upstream stability patch applied")

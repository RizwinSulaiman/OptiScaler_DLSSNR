# AMD NR Bridge experiment

This branch adds one-click Output Scaling presets intended for testing an **external AMD DLSS-NR runtime** on RDNA4. It does not include or modify that runtime.

## Idea

Public DLSS-NR experiments show that neural cost scales strongly with pixel count. OptiScaler already has the right two-stage pipeline: the temporal upscaler can target a resolution below display resolution, then Output Scaling restores the final display size.

The new `AMD NR bridge` buttons set Output Scaling to 83%, 75%, 67%, 58%, or 50%, force the fast FSR1 presentation scaler, disable OptiScaler's own DLSS-NR pass, and reinitialize the current backend.

For a 3440x1440 display the approximate intermediate sizes / pixel loads are:

| Preset | Approx target | Pixels vs native |
|---|---:|---:|
| 83% | 2855x1195 | 68.9% |
| 75% | 2580x1080 | 56.3% |
| 67% | 2305x965 | 44.9% |
| 58% | 1995x835 | 33.6% |
| 50% | 1720x720 | 25.0% |

These are workload ratios, **not measured FPS gains**.
## Test order

1. Use a DX12 game with an FSR 3/4 path and the external AMD NR runtime installed separately.
2. Keep the game display resolution at native 3440x1440.
3. Establish a native baseline with Output Scaling disabled.
4. Open OptiScaler, go to Output Scaling, and start with `AMD NR bridge: 75%`.
5. Confirm the external NR log reports a smaller processing/staging resolution or materially lower `network job ... ms` values.
6. Compare 83%, 75%, 67%, 58%, and 50%. Use the highest ratio that meets the desired frame-time target.
7. If the external hook does not see the intermediate FidelityFX target, disable the bridge; hook ordering is game/runtime dependent and still needs real-world validation.

## Benchmarking

Use `tools/Measure-NR.ps1 -Log <path-to-dlssnr_on_amd.log> -Label 75pct` after each fixed-camera run. Compare median and p95 neural-job time, not only displayed FPS.

## Scope

This branch contains only OptiScaler changes and clean-room integration logic based on publicly observable behavior. It does not redistribute `dlssnr_on_amd`, `nvngx_dlssnr.dll`, or any third-party proprietary model/runtime binary.
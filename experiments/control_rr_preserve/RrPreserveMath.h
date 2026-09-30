#pragma once

#include <algorithm>
#include <cmath>

namespace control_rr_preserve
{
struct Rgb
{
    float r = 0.0f;
    float g = 0.0f;
    float b = 0.0f;
};

struct ConfidenceInputs
{
    float motion = 1.0f;
    float depth = 1.0f;
    float disocclusion = 1.0f;
    float reactive = 1.0f;
    float exposure = 1.0f;
};

inline float Saturate(float v)
{
    if (!std::isfinite(v))
        return 0.0f;
    return std::clamp(v, 0.0f, 1.0f);
}

// Deliberately conservative: any independent reason not to trust the carried NR edit
// can veto it. A product also degrades smoothly instead of turning a near-threshold
// disocclusion into a binary edge.
inline float Confidence(const ConfidenceInputs& v)
{
    return Saturate(v.motion) * Saturate(v.depth) * Saturate(v.disocclusion) *
           Saturate(v.reactive) * Saturate(v.exposure);
}

inline float Luminance(const Rgb& c)
{
    return std::max(0.0f, 0.212639f * c.r + 0.715169f * c.g + 0.072192f * c.b);
}

// Reference CPU form of the first RR-preserve compositor. RR/base is authoritative.
// The model is used only to estimate a bounded luminance gain, and confidence decides
// how much of that gain is allowed onto the RR image. This intentionally does NOT yet
// transfer chroma or low-frequency lighting; those get separate confidence/bounds later.
inline Rgb ComposeBoundedLuminanceEdit(const Rgb& rr, const Rgb& model,
                                       float confidence, float maxRatio = 2.0f)
{
    const float c = Saturate(confidence);
    if (c <= 0.0f)
        return rr;

    const float guard = std::clamp(std::isfinite(maxRatio) ? maxRatio : 1.0f, 1.0f, 8.0f);
    const float y0 = Luminance(rr);
    const float y1 = Luminance(model);

    // Near-black RR pixels are not a stable denominator. Keep RR untouched rather
    // than letting one model sparkle create an unbounded ratio.
    constexpr float kFloor = 1.0f / 1024.0f;
    if (y0 < kFloor || !std::isfinite(y1))
        return rr;

    const float maxStops = std::log2(guard);
    const float modelStops = std::log2(std::max(y1, kFloor) / y0);
    const float boundedStops = std::clamp(modelStops, -maxStops, maxStops);
    const float gain = std::exp2(boundedStops * c);

    return { rr.r * gain, rr.g * gain, rr.b * gain };
}
} // namespace control_rr_preserve

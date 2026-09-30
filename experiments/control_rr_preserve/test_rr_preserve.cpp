#include "RrPreserveMath.h"

#include <cassert>
#include <cmath>
#include <iostream>

using namespace control_rr_preserve;

static bool Near(float a, float b, float eps = 1e-5f)
{
    return std::fabs(a - b) <= eps;
}

static void Same(const Rgb& a, const Rgb& b)
{
    assert(Near(a.r, b.r));
    assert(Near(a.g, b.g));
    assert(Near(a.b, b.b));
}

int main()
{
    const Rgb rr { 0.25f, 0.50f, 1.00f };

    // Clean RR is an exact fallback whenever confidence is zero.
    Same(ComposeBoundedLuminanceEdit(rr, { 2.0f, 2.0f, 2.0f }, 0.0f), rr);

    // A disocclusion veto must collapse confidence to zero even if every other term trusts the edit.
    ConfidenceInputs cut {};
    cut.disocclusion = 0.0f;
    assert(Confidence(cut) == 0.0f);
    Same(ComposeBoundedLuminanceEdit(rr, { 2.0f, 2.0f, 2.0f }, Confidence(cut)), rr);

    // Invalid confidence is rejected, not promoted to certainty.
    ConfidenceInputs bad {};
    bad.motion = NAN;
    assert(Confidence(bad) == 0.0f);

    // Full confidence may apply an edit but the gain cannot exceed MaxRatio.
    const Rgb bright = ComposeBoundedLuminanceEdit(rr, { 100.0f, 100.0f, 100.0f }, 1.0f, 2.0f);
    assert(bright.r <= rr.r * 2.00001f);
    assert(bright.g <= rr.g * 2.00001f);
    assert(bright.b <= rr.b * 2.00001f);

    // The lower bound is symmetric in log space: MaxRatio 2 also limits darkening to 1/2.
    const Rgb dark = ComposeBoundedLuminanceEdit(rr, { 0.00001f, 0.00001f, 0.00001f }, 1.0f, 2.0f);
    assert(dark.r >= rr.r * 0.49999f);
    assert(dark.g >= rr.g * 0.49999f);
    assert(dark.b >= rr.b * 0.49999f);

    // Partial confidence must produce an edit between fallback and the fully trusted result.
    const Rgb half = ComposeBoundedLuminanceEdit(rr, { 2.0f, 2.0f, 2.0f }, 0.5f, 2.0f);
    assert(half.r > rr.r && half.r < bright.r);

    // Near-black RR stays authoritative; ratios there are numerically and visually unsafe.
    const Rgb black { 0.0f, 0.0f, 0.0f };
    Same(ComposeBoundedLuminanceEdit(black, { 1.0f, 1.0f, 1.0f }, 1.0f), black);

    std::cout << "RR-preserve reference tests passed\n";
    return 0;
}

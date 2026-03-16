#!/usr/bin/env python3
"""
Test to understand DS9 ellipse angle convention in world coordinates.

KEY INSIGHT: 
- In PIXEL coordinates: angle is from +x axis, CCW
- In WORLD coordinates (fk5/icrs): angle is from NORTH towards EAST

The relationship depends on the WCS transformation, specifically:
- CD matrix or CDELT values
- Whether the image is flipped (common in astronomical images)
"""

print("""
================================================================================
DS9 ELLIPSE ANGLE CONVENTIONS
================================================================================

1. PIXEL COORDINATES (image coordinate system):
   - Angle measured from positive X-axis, counterclockwise
   - 0° = along +X axis
   - 90° = along +Y axis

2. WORLD COORDINATES (fk5, icrs, galactic):
   - Angle measured from NORTH towards EAST
   - 0° = along North (increasing Dec)
   - 90° = along East (increasing RA, which is typically DECREASING X in FITS!)

================================================================================
THE CRITICAL ISSUE: 
================================================================================

In most astronomical FITS images:
- Y-axis (rows) typically aligns with Declination (or close to it)
- X-axis (columns) typically aligns with RA, BUT RA INCREASES TO THE LEFT!

This means:
- +X in pixel coords ≈ -RA (West)
- +Y in pixel coords ≈ +Dec (North)

So if we have an ellipse at angle θ from +X in pixel coords:
- In pixel coords: θ degrees CCW from +X
- In world coords: The NORTH direction is roughly along +Y
- So PA_world = 90° - θ (if no rotation in WCS)

But it's actually more complex because:
1. WCS can have arbitrary rotation (PC/CD matrix)
2. The standard is PA from North through East

================================================================================
PROPER CONVERSION:
================================================================================

To convert from pixel angle (θ_pix, from +X CCW) to DS9 world PA:

1. Simple case (Y≈Dec, X≈-RA, no rotation):
   PA_ds9 = 90 - θ_pix
   
   Why? 
   - North is along +Y (90° in pixel coords)
   - θ_pix=0 means along +X (West), which is PA=90 from North
   - θ_pix=90 means along +Y (North), which is PA=0 from North
   
2. With WCS rotation:
   Need to account for CROTA2 or CD matrix rotation

================================================================================
""")

# Let's verify with a specific example
import numpy as np

print("EXAMPLE SCENARIOS:")
print("-" * 60)

scenarios = [
    (0, "Major axis along +X (pixel)", "Should be PA≈90° (East-West) in DS9"),
    (90, "Major axis along +Y (pixel)", "Should be PA≈0° (North-South) in DS9"),
    (45, "Major axis at 45° from +X", "Should be PA≈45° in DS9"),
    (-45, "Major axis at -45° from +X", "Should be PA≈135° in DS9"),
]

for theta_pix, desc_pix, desc_world in scenarios:
    # Simple conversion (assumes Y≈Dec, X≈-RA)
    pa_ds9 = (90 - theta_pix) % 180
    print(f"θ_pixel = {theta_pix:4d}° : {desc_pix}")
    print(f"         → PA_DS9 = {pa_ds9:5.1f}° : {desc_world}")
    print()

print("""
================================================================================
CONCLUSION:
================================================================================

The conversion formula should be:
    PA_DS9 = (90 - theta_pixel) % 180

NOT just:
    PA_DS9 = theta_pixel % 180

This explains the 90° offset you're seeing!
================================================================================
""")

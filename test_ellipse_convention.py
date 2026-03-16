#!/usr/bin/env python3
"""
Test script to understand the ellipse orientation convention in the Gaussian model.

This will help us understand:
1. What does theta=0 mean in the Gaussian model?
2. What does sigmax vs sigmay represent?
3. How does the model compare to photutils EllipticalAperture?
"""

import numpy as np
import matplotlib.pyplot as plt
from photutils.aperture import EllipticalAperture

def gaussian_2d(x, y, A, x0, y0, sx, sy, th):
    """
    2D elliptical Gaussian - the model used in gaussfit.py
    
    Parameters:
    - th: rotation angle (radians)
    - sx: sigma in one direction
    - sy: sigma in another direction
    """
    a = (np.cos(th)**2)/(2*sx**2) + (np.sin(th)**2)/(2*sy**2)
    b = np.sin(2*th)/(4*sx**2) - np.sin(2*th)/(4*sy**2)
    c = (np.sin(th)**2)/(2*sx**2) + (np.cos(th)**2)/(2*sy**2)
    return A * np.exp(- (a*(x - x0)**2 + 2*b*(x - x0)*(y - y0) + c*(y - y0)**2))

# Create a grid
size = 100
x = np.arange(size)
y = np.arange(size)
xx, yy = np.meshgrid(x, y)

# Center
x0, y0 = 50, 50

# Test case: elongated source
# sx = 15 (larger), sy = 5 (smaller)
# If theta=0, where does the major axis point?
sx, sy = 15, 5
A = 1.0

fig, axes = plt.subplots(2, 3, figsize=(15, 10))

test_angles = [0, 30, 45, 60, 90, -45]

for idx, angle_deg in enumerate(test_angles):
    ax = axes[idx // 3, idx % 3]
    
    theta_rad = np.deg2rad(angle_deg)
    
    # Generate Gaussian
    z = gaussian_2d(xx, yy, A, x0, y0, sx, sy, theta_rad)
    
    # Plot the Gaussian
    ax.imshow(z, origin='lower', cmap='viridis')
    ax.set_title(f'theta = {angle_deg}° (sx={sx}, sy={sy})')
    
    # Mark the center
    ax.plot(x0, y0, 'r+', markersize=15, markeredgewidth=2)
    
    # Draw the expected ellipse using photutils
    # FWHM = 2.3548 * sigma
    fwhm_x = 2.3548 * sx
    fwhm_y = 2.3548 * sy
    
    # photutils uses: a=semimajor, b=semiminor, theta from x-axis CCW
    # Let's try with the same theta
    aperture = EllipticalAperture((x0, y0), fwhm_x, fwhm_y, theta=theta_rad)
    aperture.plot(ax, color='red', lw=2, label='photutils (same theta)')
    
    # Also try with theta + 90
    aperture90 = EllipticalAperture((x0, y0), fwhm_x, fwhm_y, theta=theta_rad + np.pi/2)
    aperture90.plot(ax, color='cyan', lw=2, linestyle='--', label='photutils (theta+90)')
    
    ax.set_xlim(20, 80)
    ax.set_ylim(20, 80)
    ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig('/home/dassel/Hyper-Playground/test_ellipse_convention.png', dpi=150)
plt.show()

print("\n" + "="*80)
print("ANALYSIS:")
print("="*80)
print("""
In the Gaussian model:
  a = cos²(θ)/(2σx²) + sin²(θ)/(2σy²)
  b = sin(2θ)/(4σx²) - sin(2θ)/(4σy²)  
  c = sin²(θ)/(2σx²) + cos²(θ)/(2σy²)

The quadratic form is: a*x² + 2b*xy + c*y²

When θ=0:
  a = 1/(2σx²)
  b = 0
  c = 1/(2σy²)
  
This gives: x²/(2σx²) + y²/(2σy²)

So at θ=0:
- σx controls the width along the X-AXIS
- σy controls the width along the Y-AXIS

If σx > σy, the ellipse is elongated along the X-axis at θ=0.
θ rotates this counterclockwise.

The MAJOR axis (longest) follows σx and points in direction θ from the x-axis.
""")

print("\n" + "="*80)
print("COMPARING WITH PHOTUTILS:")
print("="*80)
print("""
In photutils.EllipticalAperture(position, a, b, theta):
- 'a' is the SEMIMAJOR axis (the longer one)
- 'b' is the SEMIMINOR axis (the shorter one)  
- theta is the rotation of the SEMIMAJOR axis from the positive x-axis, CCW

KEY INSIGHT:
- In our Gaussian: σx is tied to the DIRECTION of theta
- In photutils: 'a' (semimajor) is tied to the DIRECTION of theta

So if σx > σy in our fit, then:
  - The major axis is along theta
  - We should use: a = FWHM_x, b = FWHM_y, theta = theta

But if σy > σx in our fit (which can happen due to fitting degeneracy):
  - The major axis is actually perpendicular to theta
  - The current normalization swaps σx↔σy and adds 90° to theta
  - This should work correctly...

UNLESS there's a sign convention issue!
""")

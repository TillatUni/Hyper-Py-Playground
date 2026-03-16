#!/usr/bin/env python3
"""
Check the WCS of the actual FITS files to understand the coordinate transformation.
"""

import os
import glob
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

# Find a FITS file
maps_dir = "/home/dassel"
fits_files = glob.glob(os.path.join(maps_dir, "G010*.fits"))

if not fits_files:
    maps_dir = "/home/dassel/maps"
    fits_files = glob.glob(os.path.join(maps_dir, "*.fits"))

if fits_files:
    fits_file = fits_files[0]
    print(f"Checking WCS of: {fits_file}")
    print("=" * 70)
    
    with fits.open(fits_file) as hdul:
        header = hdul[0].header
        wcs = WCS(header, naxis=2)  # Use only 2D WCS
        
        # Check for rotation info
        print("\nWCS Information:")
        print("-" * 70)
        
        # CDELT (pixel scale)
        cdelt1 = header.get('CDELT1', None)
        cdelt2 = header.get('CDELT2', None)
        print(f"CDELT1 (deg/pix): {cdelt1}")
        print(f"CDELT2 (deg/pix): {cdelt2}")
        
        # CROTA (rotation)
        crota2 = header.get('CROTA2', header.get('CROTA1', None))
        print(f"CROTA2 (deg): {crota2}")
        
        # CD matrix
        cd11 = header.get('CD1_1', None)
        cd12 = header.get('CD1_2', None)
        cd21 = header.get('CD2_1', None)
        cd22 = header.get('CD2_2', None)
        print(f"\nCD Matrix:")
        print(f"  CD1_1: {cd11}  CD1_2: {cd12}")
        print(f"  CD2_1: {cd21}  CD2_2: {cd22}")
        
        # PC matrix
        pc11 = header.get('PC1_1', None)
        pc12 = header.get('PC1_2', None)
        pc21 = header.get('PC2_1', None)
        pc22 = header.get('PC2_2', None)
        print(f"\nPC Matrix:")
        print(f"  PC1_1: {pc11}  PC1_2: {pc12}")
        print(f"  PC2_1: {pc21}  PC2_2: {pc22}")
        
        # Calculate the position angle of North in the image
        print("\n" + "=" * 70)
        print("CALCULATING NORTH DIRECTION IN PIXEL COORDS:")
        print("-" * 70)
        
        # Get the center pixel
        naxis1 = header.get('NAXIS1', 100)
        naxis2 = header.get('NAXIS2', 100)
        cx, cy = naxis1/2, naxis2/2
        
        # Get world coords at center
        ra_c, dec_c = wcs.wcs_pix2world(cx, cy, 0)
        
        # Get pixel coords of a point 0.01 deg north
        x_north, y_north = wcs.wcs_world2pix(ra_c, dec_c + 0.01, 0)
        
        # Direction of North in pixel coords
        dx_north = x_north - cx
        dy_north = y_north - cy
        
        # Angle of North from +X axis (counterclockwise)
        angle_north_deg = np.rad2deg(np.arctan2(dy_north, dx_north))
        
        print(f"Center pixel: ({cx:.1f}, {cy:.1f})")
        print(f"Center world: (RA={ra_c:.6f}, Dec={dec_c:.6f})")
        print(f"North direction in pixels: dx={dx_north:.4f}, dy={dy_north:.4f}")
        print(f"Angle of North from +X axis: {angle_north_deg:.2f}°")
        
        print("\n" + "=" * 70)
        print("IMPLICATIONS FOR PA CONVERSION:")
        print("-" * 70)
        print(f"""
If North is at {angle_north_deg:.1f}° from +X in pixel coords, then:

To convert pixel angle θ_pix to DS9 PA (from North towards East):
  PA_DS9 = ({angle_north_deg:.1f} - θ_pix) mod 180

For a standard image where North is roughly along +Y (90°):
  PA_DS9 = (90 - θ_pix) mod 180

Current formula in the code: (90 - θ_pix) mod 180
""")
        
        if abs(angle_north_deg - 90) > 5:
            print(f"⚠️  WARNING: North is NOT along +Y axis!")
            print(f"   The conversion formula may need adjustment.")
            print(f"   Consider using: PA_DS9 = ({angle_north_deg:.1f} - θ_pix) mod 180")
else:
    print("No FITS files found!")

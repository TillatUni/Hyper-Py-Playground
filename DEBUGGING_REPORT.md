# Hyper-Py Debugging Report
## Investigation of Slow Maps and Fit Errors

**Date:** January 16, 2026  
**Config:** max_group_size=1, n_cores=10, 5 threads/worker

---

## 1. ROOT CAUSE: max_group_size NOT IMPLEMENTED

### Finding
The `max_group_size: 1` parameter in `hyper_config-playground.yaml` is **NOT READ OR USED BY THE CODE**.

**Evidence:**
```bash
$ grep -r "max_group" hyper_py_playground/*.py
# (no results)

$ grep "max_group" hyper_config-playground.yaml
  max_group_size: 1  # Skip groups larger than this to avoid extremely slow fits
```

### Impact
All blended sources are processed regardless of group size. Maps with many blended sources still attempt to fit all sources together, which is computationally expensive and explains why:
- **881427.fits** with 26 blended sources hung for 50+ minutes
- **126348.fits** with 31 blended sources hung for 23+ minutes
- **G345.5043+00.3480.fits** with 112 blended sources completed in ~9 minutes (got lucky)

### Location to Fix
**File:** [single_map.py](hyper_py_playground/single_map.py) around line 420-440

The fix needs to:
1. Read `max_group_size` from config
2. Skip groups larger than the threshold
3. Mark skipped sources appropriately in output

---

## 2. BOUNDS ERROR: "Initial guess is outside of provided bounds"

### Affected Maps
| Map | Box Size | Order |
|-----|----------|-------|
| G310.0135+00.3892.fits | (89, 89) | 0 |
| 767784.fits | (73, 73) | 0 |
| 778802.fits | (89, 89) | 0 |

### Root Cause
In [fitting.py](hyper_py_playground/fitting.py#L242-L249) and [gaussfit.py](hyper_py_playground/gaussfit.py#L247-L250), amplitude bounds are set as:

```python
local_peak = np.nanmax(cutout_masked[int(yc)-1:int(yc)+1, int(xc)-1:int(xc)+1])
params.add(f"{prefix}amplitude", value=local_peak, min=0.4*local_peak, max=1.3*local_peak)
```

**Problem:** If `local_peak` is **negative** (possible after aggressive background subtraction or in noisy regions):
- `local_peak = -5.0`
- `min = 0.4 * (-5.0) = -2.0`
- `max = 1.3 * (-5.0) = -6.5`
- Result: `min > max` → **INVALID BOUNDS**

lmfit raises "Initial guess is outside of provided bounds" when this occurs.

### Fix
```python
# Before setting bounds, ensure local_peak is positive
local_peak = np.nanmax(cutout_masked[int(yc)-1:int(yc)+1, int(xc)-1:int(xc)+1])
if local_peak <= 0:
    local_peak = np.nanmax(cutout_masked)  # fallback to global max
if local_peak <= 0:
    local_peak = 1.0  # absolute fallback

# Now safely set bounds
params.add(f"{prefix}amplitude", value=local_peak, min=0.4*local_peak, max=1.5*local_peak)
```

---

## 3. NaN VALUES ERROR

### Affected Maps
| Map | Box Size | Error |
|-----|----------|-------|
| 767784.fits | (99, 99) | NaN values detected |
| 778802.fits | (99, 99) | NaN values detected |
| 787212.fits | (85, 85), (99, 99) | NaN values detected |
| G012.8909+00.4938C.fits | (101, 101), (107, 107) | NaN values detected |

### What NaN Means
**NaN (Not a Number)** appears in FITS data when:
1. **Bad/dead pixels** in the detector
2. **Edge effects** where the map was clipped
3. **Cosmic ray removal** left holes
4. **Numerical overflow** during data reduction
5. **Invalid operations** like 0/0 or log(negative)

### Root Cause in Hyper-py
The error message "NaN values detected in your input data or the output of your objective/model function" from lmfit indicates:

1. The cutout contains NaN pixels that weren't properly masked
2. The model evaluation produced NaN (e.g., overflow in exponential)
3. The residual calculation hit NaN

**Current handling in** [fitting.py](hyper_py_playground/fitting.py#L347-L353):
```python
valid = ~np.isnan(cutout_masked)
x_valid = xx.ravel()[valid.ravel()]
y_valid = yy.ravel()[valid.ravel()]
data_valid = cutout_masked.ravel()[valid.ravel()]
```

This filters data but doesn't prevent model overflow.

### Fixes for NaN

**Option 1: Pre-interpolate NaN regions**
```python
from astropy.convolution import interpolate_replace_nans, Gaussian2DKernel
kernel = Gaussian2DKernel(x_stddev=2)
cutout_filled = interpolate_replace_nans(cutout, kernel)
```

**Option 2: Add numerical safety in model function**
```python
def model_fn(p, x, y):
    model = np.zeros_like(x, dtype=float)
    for i in range(len(xcen_cut)):
        # ... calculate gaussian ...
        exponent = - (a*(x - x0)**2 + 2*b*(x - x0)*(y - y0) + c*(y - y0)**2)
        # Prevent overflow: clip exponent to reasonable range
        exponent = np.clip(exponent, -700, 0)  # exp(-700) ≈ 0
        model += A * np.exp(exponent)
    return np.where(np.isfinite(model), model, 0.0)
```

**Option 3: Skip sources in NaN-heavy regions**
```python
nan_fraction = np.sum(np.isnan(cutout_masked)) / cutout_masked.size
if nan_fraction > 0.3:  # More than 30% NaN
    logger.warning(f"Skipping source {source_id}: {nan_fraction*100:.1f}% NaN pixels")
    continue
```

---

## 4. GROUP FIT FAILED: G023.9659-00.1087.fits

### Error
```
Group fit failed for sources (np.int64(10), np.int64(11), np.int64(12))
```

### Root Cause
In [single_map.py](hyper_py_playground/single_map.py#L468-L470):
```python
if fit_result is None:
    logger.error(f"Group fit failed for sources {group_key}")
    continue
```

The `fit_result` is `None` when `fit_group_with_background()` fails to converge for any box size/order combination.

**Common causes:**
1. Sources too close together → degenerate solution
2. One or more sources have negative local peaks
3. Initial parameter estimates outside bounds
4. Cutout has too many NaN pixels
5. All attempted fits failed validation

### Fix
Add better error handling and fallback strategies:
```python
# In fitting.py, return more diagnostic info
if best_result is None:
    # Try with fixed positions as fallback
    for i, (xc, yc) in enumerate(zip(xcen_cut, ycen_cut)):
        params[f"g{i}_x0"].set(vary=False)
        params[f"g{i}_y0"].set(vary=False)
    # Retry fit...
```

---

## 5. SLOW MAPS SUMMARY

| Map | Blended Sources | Time Stuck | Likely Cause |
|-----|-----------------|------------|--------------|
| 126348.fits | 31 | >23 min | Group too large |
| 615590.fits | 28 | >6 min | Group too large |
| 767784.fits | 109 | >8 min | Many groups + NaN errors |
| 787212.fits | 83 | >9 min | Many groups + NaN errors |
| 881427.fits | 26 | >50 min | Pathological source config |
| G012.8909+00.4938C.fits | 19 | >8 min | NaN errors causing retries |
| G343.1261-00.0623.fits | 44 | >25 min | Group too large |

### Why Some Large Groups Complete Fast
**G345.5043+00.3480.fits** (112 blended) completed in ~9 min because:
- Groups may be split into smaller subgroups
- Source configuration led to fast convergence
- No NaN issues requiring fallback iterations

---

## 6. RECOMMENDED FIXES

### Priority 1: Implement max_group_size

**File:** `hyper_py_playground/single_map.py` around line 420

```python
# Add after line 218 (after group_sources call)
max_group_size = cfg.get("grouping", "max_group_size", 0)  # 0 = no limit

# In blended loop (around line 420), add:
for i in blended:
    group_indices = common_group[i]
    group_indices = group_indices[group_indices >= 0]
    
    # NEW: Skip groups larger than max_group_size
    if max_group_size > 0 and len(group_indices) > max_group_size:
        logger.warning(f"Skipping group with {len(group_indices)} sources (max_group_size={max_group_size})")
        continue
    
    group_key = tuple(sorted(group_indices))
    # ... rest of loop
```

### Priority 2: Fix amplitude bounds

**Files:** `fitting.py` and `gaussfit.py`

```python
# Replace amplitude bound setting with:
local_peak = np.nanmax(cutout_masked[int(yc)-1:int(yc)+1, int(xc)-1:int(xc)+1])

# Ensure positive amplitude
if not np.isfinite(local_peak) or local_peak <= 0:
    local_peak = np.nanmax(cutout_masked)
if not np.isfinite(local_peak) or local_peak <= 0:
    local_peak = median_bg  # fallback to background level
if local_peak <= 0:
    local_peak = 1.0  # absolute minimum

# Safe bounds
amp_min = max(0.0, 0.4 * local_peak)
amp_max = max(amp_min + 1e-6, 1.5 * local_peak)
params.add(f"{prefix}amplitude", value=local_peak, min=amp_min, max=amp_max)
```

### Priority 3: Add NaN safety

**File:** `fitting.py` model_fn

```python
def model_fn(p, x, y):
    model = np.zeros_like(x, dtype=float)
    for i in range(len(xcen_cut)):
        # ... existing code ...
        
        # Clip exponent to prevent overflow
        exponent = - (a*(x - x0)**2 + 2*b*(x - x0)*(y - y0) + c*(y - y0)**2)
        exponent = np.clip(exponent, -500, 0)
        model += A * np.exp(exponent)
    
    # Final safety
    model = np.where(np.isfinite(model), model, 0.0)
    return model
```

### Priority 4: Add fit timeout

```python
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Fit timed out")

# In fit_group_with_background:
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)  # 5 minute timeout
try:
    result = minimize(...)
finally:
    signal.alarm(0)  # Cancel alarm
```

---

## 7. TESTING RECOMMENDATIONS

1. **Test max_group_size implementation** with the slow maps:
   - Set `max_group_size: 5` and verify large groups are skipped
   
2. **Test bounds fix** on G310.0135+00.3892.fits:
   - Should no longer get bounds error
   
3. **Test NaN handling** on 787212.fits:
   - Should complete without NaN errors or skip affected sources gracefully

4. **Create unit tests** for edge cases:
   - Negative local peaks
   - All-NaN cutouts
   - Single-pixel sources

---

## 8. FILES TO MODIFY

1. **[single_map.py](hyper_py_playground/single_map.py)**
   - Add max_group_size check
   - Add timeout handling

2. **[fitting.py](hyper_py_playground/fitting.py)**
   - Fix amplitude bounds (around lines 242-250)
   - Add model overflow protection
   - Add NaN fraction check

3. **[gaussfit.py](hyper_py_playground/gaussfit.py)**
   - Same amplitude bounds fix (around lines 247-250)
   - Same model overflow protection

4. **[hyper_config-playground.yaml](hyper_config-playground.yaml)**
   - Move max_group_size to proper section after implementation

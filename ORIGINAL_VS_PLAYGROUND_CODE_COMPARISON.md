# Hyper-Py Original vs Hyper-Playground: Thorough Code Comparison

## Scope and method

Compared recursively:
- Original: `Hyper_Backup/hyper_py_backup`
- Playground: `Hyper-Playground/hyper_py_playground`

Method used:
1. Full recursive unified diff (`diff -ru`) excluding `__pycache__`.
2. Per-file hunk inspection with line ranges from diff headers.
3. Functional interpretation of each code change.
4. Likely intent assessment based on surrounding logic, comments, and new config fields.

Total diff size: 1670 lines.

## High-level summary

Changed files (14):
- `assets/default_config.yaml` (+17 / -0)
- `bkg_multigauss.py` (+16 / -2)
- `data_output.py` (+2 / -5)
- `detection.py` (+220 / -46)
- `fitting.py` (+245 / -27)
- `gaussfit.py` (+242 / -27)
- `groups.py` (+58 / -32)
- `hyper.py` (+87 / -11)
- `map_io.py` (+3 / -2)
- `photometry.py` (+4 / -3)
- `run_hyper.py` (+4 / -4)
- `single_map.py` (+83 / -15)
- `__init__.py` (+1 / -1)
- `__main__.py` (+1 / -1)

Added file (playground only):
- `performance_timer.py`

Overall themes of the playground changes:
- Performance and scaling: KD-tree, vectorization, thread limits, timing logs.
- Robustness: fit timeouts, retries, NaN/invalid handling, loop safety limits.
- Workflow flexibility: new parallel modes and map timeout control.
- Scientific consistency fixes: PA convention and Gaussian rotation term sign fix.

---

## File-by-file detailed comparison

## 1) assets/default_config.yaml

Changed hunks:
- `@@ -21,6 +21,15 @@`
- `@@ -63,6 +72,14 @@`

What changed:
- Added `control.max_total_threads`.
- Added `control.parallel_mode` with values `"maps"` or `"sources"`.
- Added `control.map_timeout_minutes`.
- Added `detection.local_max_radius`.
- Added `detection.local_max_steepness`.

Functional impact:
- Enables explicit control of total thread pressure in multi-process runs.
- Adds intra-map parallel strategy option (`sources`) in addition to map-level parallelism.
- Adds per-map timeout concept.
- Adds new source-quality filtering to reject non-local maxima and plateau-like emission peaks.

Likely reason:
- Make processing faster and more stable on shared systems.
- Reduce false detections from extended/halo emission.
- Avoid jobs hanging forever.

---

## 2) performance_timer.py (new file)

What changed:
- New timing infrastructure with:
  - `PerformanceTimer` class (thread-safe log writing).
  - context manager `measure(...)`.
  - global timer setters/getters.
  - summary writer with per-script totals.

Functional impact:
- Enables persistent timing logs for profiling bottlenecks.
- Supports concurrent writes from parallel execution paths.

Likely reason:
- Targeted performance diagnostics for optimization work in playground.

---

## 3) bkg_multigauss.py

Changed hunks:
- `@@ -162,9 +162,16 @@`
- `@@ -298,9 +305,16 @@`

What changed:
- Added `max_loop_iterations = 50` to threshold-adjustment loops.
- Added amplitude safety check:
  - skip source when amplitude is NaN or non-positive.
- Replaced `while True` with bounded loop `while loop_count < max_loop_iterations`.

Functional impact:
- Prevents potential infinite loops.
- Avoids invalid threshold logic on broken fit parameters.
- Improves runtime safety under bad fit conditions.

Likely reason:
- Hardening against pathological fit cases discovered during large runs.

---

## 4) data_output.py

Changed hunk:
- `@@ -109,11 +109,8 @@`

What changed:
- Replaced row-by-row IPAC table rebuild with direct `table.copy()`.

Functional impact:
- Same output semantics, much lower overhead for large tables.
- Avoids O(n^2)-like behavior from repeated `add_row` operations.

Likely reason:
- Speed optimization for large catalogs.

---

## 5) detection.py

Changed hunks:
- `@@ -1,8 +1,11 @@`
- `@@ -13,38 +16,59 @@`
- `@@ -61,12 +85,17 @@`
- `@@ -76,46 +105,180 @@`
- `@@ -125,6 +288,9 @@`
- `@@ -135,6 +301,14 @@`

What changed in detail:
1. Imports and timing
- Added `time`, `cKDTree`, and timer access (`get_timer`).

2. High-pass filter optimization
- Added kernel cache (`_kernel_cache`) to avoid repeated kernel allocation.
- Uses float64 and `np.maximum` for efficient clipping to non-negative.

3. Normalization optimization
- Reduced copies and improved normalization path.

4. RMS estimation optimization
- Early return when no positive pixels; cleaner mask usage.

5. Peak filtering reimplementation
- Neighbor suppression moved from nested loops O(n^2) to KD-tree pair queries.
- Pair sorting preserves original tie/ordering behavior intentionally.

6. SNR filtering vectorization
- Replaced per-row loops with vectorized index checks and extraction.

7. New local-maximum quality filter
- Added `filter_local_maximum(...)`:
  - local dominance check within radius (`local_max_radius * FWHM`).
  - edge steepness check (`local_max_steepness`) using radial sampling.

8. detect_sources orchestration
- Reads new config fields for local max filtering.
- Pipeline now: geometric filtering -> SNR filtering -> local-max filtering.
- Adds timing log entry including source count.

Functional impact:
- Significant speedup for source filtering on large source sets.
- Better control over spurious detections on broad background structures.
- Additional filtering can reduce source count compared to original defaults.

Likely reason:
- Improve throughput and detection quality under crowded/extended environments.

Potential caveat:
- New defaults in config (`local_max_radius: 0.5`, `local_max_steepness: 0.01`) are non-zero, so filtering is active by default and can alter completeness relative to original behavior.

---

## 6) groups.py

Changed hunks:
- `@@ -1,8 +1,12 @@`
- `@@ -16,48 +20,70 @@`

What changed:
- Added `cKDTree` import.
- Replaced pairwise distance neighborhood grouping with:
  - KD-tree pair search for edges.
  - Union-Find with path compression + rank heuristics.
- Added zero-source early return.
- Refactored group member extraction through root-to-members mapping.

Functional impact:
- Complexity improvement from O(n^2) style to near O(n log n + k).
- More scalable grouping for dense maps.
- Group semantics preserved (sources connected by transitive proximity still merge).

Likely reason:
- Performance optimization for large source lists.

---

## 7) fitting.py (group fitting)

Changed hunks:
- `@@ -1,5 +1,7 @@`
- `@@ -13,15 +15,160 @@`
- `@@ -238,11 +385,9 @@`
- `@@ -279,21 +424,28 @@`
- `@@ -303,10 +455,13 @@`
- `@@ -345,15 +500,72 @@`
- `@@ -427,7 +639,7 @@`
- `@@ -555,8 +767,14 @@`

What changed in detail:
1. New timeout infrastructure
- Added timeout helpers/classes:
  - `run_with_timeout` (thread-based helper)
  - `TimeoutCallback` for lmfit `iter_cb`
  - `TimeoutResidualWrapper`
  - `FitTimeoutError` (defined but not central)
- Added timing import and timer logging.

2. Safer amplitude initialization
- New `safe_amplitude_bounds(local_peak, fallback_value)` handles NaN/negative peaks.
- Replaces direct proportional min/max bounds from local peak.

3. Gaussian model numeric fixes
- Rotation cross-term sign changed:
  - from `-sin(2th)/(4sx^2) + sin(2th)/(4sy^2)`
  - to   ` sin(2th)/(4sx^2) - sin(2th)/(4sy^2)`
- Added sigma floor (`max(sx,1e-6)`, `max(sy,1e-6)`).
- Clipped exponent to [-500, 0] before `exp`.

4. Background model application
- Uses existing polynomial parameter names from params directly instead of re-adding terms inside model function.

5. Residual robustness
- Replaces NaN/Inf in weights and residuals.
- Ensures float64 and finite residual arrays.

6. Fit execution robustness
- Skips cutouts with >50% NaNs.
- Added per-fit timeout (`fit_timeout`, default 120s for grouped fits).
- Added retry loop (up to 2 retries) with relaxed bounds and perturbed sigma starts.
- Timeout can trigger adaptive timeout increase for retries.

7. Timing instrumentation
- Logs total timing for success and failure cases.

Functional impact:
- Higher fit stability under noisy/corrupted data.
- Lower risk of stalled fitting loops.
- Better numerical behavior for extreme parameter states.
- Potentially different fitted parameter outcomes due to changed bounds/retry logic.

Likely reason:
- Address stuck/unstable fits and numerical exceptions observed in production-scale runs.

---

## 8) gaussfit.py (isolated source fitting)

Changed hunks:
- `@@ -1,4 +1,6 @@`
- `@@ -8,10 +10,155 @@`
- `@@ -237,11 +384,9 @@`
- `@@ -275,21 +420,28 @@`
- `@@ -299,7 +451,12 @@`
- `@@ -337,17 +494,69 @@`
- `@@ -514,6 +723,12 @@`

What changed:
- Mirrors the same robustness framework introduced in `fitting.py`:
  - timeout wrappers/callbacks
  - safe amplitude bounds
  - sigma floor and exponent clipping
  - corrected Gaussian cross-term sign
  - NaN sanitization in data/weights/residual
  - skip if >50% NaN pixels
  - timeout + retry strategy (default 60s for isolated fit)
  - timing logging

Functional impact:
- Same category as grouped fitting: more robust, less hanging, more resilient numerical behavior.

Likely reason:
- Keep isolated and grouped fitting pipelines behaviorally aligned and robust.

---

## 9) single_map.py

Changed hunks:
- `@@ -1,7 +1,23 @@`
- `@@ -9,17 +25,17 @@`
- `@@ -322,8 +338,17 @@`
- `@@ -368,7 +393,7 @@`
- `@@ -403,6 +428,11 @@`
- `@@ -415,6 +445,37 @@`
- `@@ -483,6 +544,13 @@`
- `@@ -550,7 +618,7 @@`

What changed in detail:
1. Thread control at module import
- Loads numpy early, then uses `threadpoolctl` to enforce BLAS thread limits from `OMP_NUM_THREADS`.
- Designed to keep worker thread count bounded.

2. Import path migration
- All imports moved from backup package namespace to playground namespace.

3. Axis normalization for fit outputs
- Enforces `FWHM_1 >= FWHM_2`; if swapped, adds 90 deg to theta and wraps.
- Explicitly documents Gaussian axis-angle degeneracy handling.

4. Peak flux unit conversion changed
- Converted from division by `beam_area_pix` to multiplication.
- Applied in both isolated and grouped branches.

5. Large-group control
- Added `fit_options.max_group_size` and `fit_options.skip_large_groups` behavior.
- If skipping large group, still emits source rows with `fit_status=0` and NaN fit quantities.

Functional impact:
- Better consistency in orientation/major-minor axis reporting.
- Better protection from very large blended groups exploding runtime.
- Guaranteed output completeness for skipped groups.
- Thread governance for worker performance stability.

Likely reason:
- Resolve inconsistent ellipse conventions.
- Prevent extreme blended groups from dominating runtime.
- Keep output tables complete even when fitting is skipped.

Important note to verify scientifically:
- The flux conversion change (divide -> multiply by beam-area-in-pixels) is intentionally commented as a correction, but this should be validated against your map unit assumptions (`mJy/pixel` vs `mJy/beam`) to ensure no scale inversion in reported peak flux.

---

## 10) hyper.py (top-level orchestration)

Changed hunks:
- `@@ -3,22 +3,43 @@`
- `@@ -27,8 +48,9 @@`
- `@@ -71,20 +93,56 @@`
- `@@ -93,13 +151,17 @@`
- `@@ -110,9 +172,12 @@`
- `@@ -124,7 +189,10 @@`
- `@@ -142,9 +210,17 @@`

What changed in detail:
1. Namespace migration
- imports switched from backup package namespace to playground package namespace.

2. Multiprocessing start method
- changed from `fork` to `spawn`.
- comments explain deadlock avoidance rationale with sklearn/lmfit state.

3. Timer integration
- initializes and uses `performance_timer` for major phases.

4. Expanded parallel controls
- reads new config controls:
  - `max_total_threads`
  - `parallel_mode`
  - `map_timeout_minutes`
- supports source-level parallel mode path (maps sequential, intra-map parallel expected downstream).

5. Logging improvements
- adds richer logs describing map/source parallel mode and thread usage.

6. Timeout handling around futures
- attempts timeout handling in parallel map execution path.

Functional impact:
- Better process safety (`spawn`) with possible startup overhead increase.
- More visibility and profiling data.
- More parallelization strategy flexibility.
- Timeout behavior intended for map-level resilience.

Likely reason:
- Resolve deadlocks/stalls and make large pipeline runs diagnosable.

Potential caveat:
- In current implementation, timeout is applied inside `for future in as_completed(futures)` via `future.result(timeout=...)`. Since `as_completed` already yields completed futures, this timeout may not effectively enforce wall-clock map cancellation. Intent is clear, but practical enforcement may be weaker than expected.

---

## 11) map_io.py

Changed hunks:
- `@@ -38,7 +38,9 @@`
- `@@ -50,7 +52,6 @@`

What changed:
- Captures `BUNIT` before WCS header stripping, then uses saved value for conversion.

Functional impact:
- Prevents unit metadata loss during header transformation.
- Makes unit conversion step more reliable.

Likely reason:
- Fix bug where BUNIT disappeared before conversion logic.

---

## 12) photometry.py

Changed hunks:
- `@@ -33,7 +33,8 @@`
- `@@ -58,8 +59,8 @@`

What changed:
- Position angle conversion changed:
  - from `theta = deg2rad(PA + 90)`
  - to   `theta = deg2rad(PA)`
- Flux/error append now uses scalar extraction:
  - `float(flux[0])` and `float(error)`.

Functional impact:
- Aligns PA convention directly with photutils expectation.
- Avoids table field type inconsistencies (array-like entries vs scalar).

Likely reason:
- Correct orientation mismatch and stabilize output schema.

---

## 13) run_hyper.py

Changed hunks:
- `@@ -14,10 +14,10 @@`
- `@@ -32,8 +32,8 @@`

What changed:
- Package import path switched to `hyper_py_playground`.
- Default package string `_PKG` changed to `hyper_py_playground`.
- Default config filename changed to `hyper_config-playground.yaml`.

Functional impact:
- CLI now targets playground package/config by default.

Likely reason:
- Environment separation between stable backup package and experimental playground package.

---

## 14) __init__.py and __main__.py

Changed hunks:
- `__init__.py`: `@@ -3,7 +3,7 @@`
- `__main__.py`: `@@ -1,4 +1,4 @@`

What changed:
- Documentation strings updated to invoke playground package name (`python -m hyper_py_playground`).

Functional impact:
- No runtime behavior change beyond user-facing invocation guidance.

Likely reason:
- Keep docs consistent with renamed package entry points.

---

## Functional change map (quick reference)

Scientific/algorithmic behavior changes:
- Detection now includes local-maximum and steepness rejection by default config.
- Gaussian model cross-term sign corrected in both fit engines.
- PA handling aligned to photutils convention (no +90 shift).
- Major/minor axis normalization now enforced.

Performance changes:
- KD-tree acceleration in detection and grouping.
- Vectorized SNR and normalization operations.
- Thread limiting in worker process startup path.
- Timing instrumentation across pipeline stages.
- Faster table copy method in output writer.

Robustness/stability changes:
- Fit timeout + retry in both isolated and grouped fits.
- NaN sanitization and skip logic for bad cutouts.
- Loop safety guard in background masking.
- `spawn` multiprocessing start method to reduce deadlocks.
- Optional skip policy for very large blended groups with explicit output rows.

---

## Likely design intent of the playground branch

The playground branch appears to be a performance-hardening and reliability branch rather than a pure feature branch. Most changes point to this objective stack:
1. Keep large runs from hanging (`spawn`, fit timeouts, loop limits, large-group skip).
2. Reduce runtime (`KD-tree`, vectorization, copy optimizations, thread control).
3. Improve diagnostics (`performance_timer`, explicit logging).
4. Correct known geometric/angle convention issues (PA handling, major/minor normalization, Gaussian cross-term sign).
5. Improve source quality filtering in crowded/extended backgrounds (local maximum + steepness checks).

---

## Items worth validating with test data

1. Peak flux scaling after `single_map.py` conversion change (division to multiplication).
2. Practical effectiveness of map timeout logic under `as_completed` usage in `hyper.py`.
3. Sensitivity/completeness impact of non-zero default local-max filters in detection config.
4. Numerical/fit-result shifts due to broadened retry bounds and timeout wrappers.

---

## Conclusion

Hyper-Playground is a substantial evolution of the original Hyper-Py implementation, focused on operational robustness, speed, and better observability, with several scientifically relevant convention fixes. The largest behavior shifts are in detection filtering defaults, fit control/retry strategy, and geometric/flux handling details.

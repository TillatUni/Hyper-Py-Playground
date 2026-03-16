# Quick Reference: Finding Slow Code Sections

## Step 1: Run Hyper-py
```bash
cd /home/dassel/Hyper-Playground
source /home/dassel/hyperenv/bin/activate
hyper-py hyper_config-playground.yaml
```

## Step 2: Check Performance Logs
```bash
# Find the latest log
ls -lt output-playground/performance_logs/ | head -5

# View a specific log
cat output-playground/performance_logs/performance_timing_<map_name>_<timestamp>.log

# View just the summary
tail -20 output-playground/performance_logs/performance_timing_<map_name>_<timestamp>.log
```

## Step 3: Identify Bottlenecks

Look at the **PERFORMANCE SUMMARY** at the bottom of the log:

```
Script                              Time (s)     % of Total  
--------------------------------------------------------------------------------
single_map.py                          85.30s       69.1%    <-- Main processing
fitting.py                             25.40s       20.6%    <-- Blended source fitting
gaussfit.py                             8.50s        6.9%    <-- Isolated source fitting
detection.py                            2.50s        2.0%    <-- Source detection
hyper.py                                1.75s        1.4%    <-- Orchestration
```

## Step 4: Find the Specific Code

Each timing entry shows exact lines:

```
14:30:45.321  single_map.py  317-419  18.4567s  Fitting 98 isolated sources
              ^^^^^^^^^^^^   ^^^^^^^
              File name      Lines
```

### Open the file at those lines:
```bash
# Using vim
vim +317 hyper_py_playground/single_map.py

# Using VS Code
code -g hyper_py_playground/single_map.py:317

# Using less (jump to line 317 by typing "317g")
less +317 hyper_py_playground/single_map.py
```

## Common Bottlenecks and What They Mean

### 1. "Fitting isolated sources" (single_map.py, lines 317-419)
- **What it does**: Fits a Gaussian + background model to each isolated source
- **Why slow**: Many sources = many fits, each solving an optimization problem
- **Look for**: High duration or low success rate

### 2. "Fitting blended sources" (single_map.py, lines 425-607)
- **What it does**: Fits multiple Gaussians simultaneously for overlapping sources
- **Why slow**: More complex optimization with more parameters
- **Look for**: Very high duration per group

### 3. "fit_group_with_background" (fitting.py, lines 25-563)
- **What it does**: The actual optimization for blended sources
- **Why slow**: Complex iterative fitting with background modeling
- **Look for**: Groups with many sources taking longest

### 4. "fit_isolated_gaussian" (gaussfit.py, lines 14-521)
- **What it does**: The actual optimization for isolated sources
- **Why slow**: Iterative fitting process
- **Look for**: Individual sources taking unusually long

### 5. "detect_sources" (detection.py, lines 123-145)
- **What it does**: Finds sources in the map using filtering and thresholding
- **Why slow**: Processing entire map, especially if large
- **Look for**: Unusual duration for map size

### 6. "Reading and preparing map (I/O)" (single_map.py, lines 130-143)
- **What it does**: Loads FITS file from disk
- **Why slow**: Disk I/O, large files, slow storage
- **Look for**: High duration = I/O bottleneck

## Comparing Runs

```bash
# Compare timing between runs
cd output-playground/performance_logs/

# See all summaries
for f in performance_timing_*.log; do
    echo "=== $f ==="
    tail -20 "$f" | grep "Total execution time"
    echo ""
done
```

## What to Focus On

1. **Start with highest % in summary** - that's where most time is spent
2. **Look for operations called many times** - small improvements = big impact
3. **Check for failed fits** - they waste time without producing results
4. **Compare similar maps** - why is one slower than another?

## Example Analysis

```
Timestamp            Script                  Lines      Duration     Description
--------------------------------------------------------------------------------
14:30:24.643         gaussfit.py            14-521     0.3421s      source_id=0  ✓ Normal
14:30:24.985         gaussfit.py            14-521     0.2987s      source_id=1  ✓ Normal
14:30:25.287         gaussfit.py            14-521     5.4321s      source_id=2  ⚠️ SLOW!
14:30:30.719         gaussfit.py            14-521     0.3156s      source_id=3  ✓ Normal
```

**Finding**: Source #2 is taking 15x longer than others!
**Action**: Check that specific source - might be a bad cutout, convergence issue, etc.

## Tips

1. **Run on a small test case first** to get baseline timing
2. **Archive logs** for comparison after making changes
3. **Look for patterns** - do certain types of sources always take longer?
4. **Check the descriptions** - they include helpful context like source counts
5. **Use grep** to find specific patterns:
   ```bash
   # Find all slow operations (>5 seconds)
   grep "5\.[0-9]*s\|[6-9]\.[0-9]*s\|[0-9][0-9]\." timing.log
   
   # Find all failed fits
   grep "FAILED" timing.log
   
   # Find all blended group fits
   grep "fit_group_with_background" timing.log
   ```

## Need More Detail?

See the full documentation in:
- `PERFORMANCE_TIMING.md` - Complete guide
- `TIMING_IMPLEMENTATION_SUMMARY.md` - What was changed

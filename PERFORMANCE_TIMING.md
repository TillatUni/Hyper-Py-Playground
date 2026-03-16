# Performance Timing in Hyper-Playground

## Overview

The Hyper-Playground codebase now includes comprehensive performance timing to help identify bottlenecks and optimize execution time.

## Features

- **Automatic timing** of all major processing steps
- **Detailed logging** with script names, line numbers, descriptions, and durations
- **Separate log files** for each map being processed
- **Summary statistics** showing which operations take the most time
- **Thread-safe** operation for parallel processing

## Output Location

Performance timing logs are saved to:
```
<output_directory>/performance_logs/
```

Each run creates a timestamped log file:
```
performance_timing_<map_name>_<timestamp>.log
```

## Log File Format

Each timing entry includes:
```
Timestamp    Script           Lines      Duration    Description
10:23:45.123 single_map.py    27-80      0.1234s     Initialization and setup
10:23:46.456 detection.py     123-145    0.5678s     detect_sources (found 42 sources)
...
```

## What Gets Timed

### hyper.py (Main orchestration)
- Configuration loading and path setup
- Processing all maps (parallel or serial)
- Collecting output tables
- Merging and writing final outputs
- Creating background datacubes
- Total execution time

### single_map.py (Per-map processing)
- Initialization and setup
- Reading and preparing map (I/O)
- Calculating map RMS
- Source detection
- Grouping sources
- Fitting isolated sources
- Fitting blended sources
- Writing output tables and region files
- Total time per map

### fitting.py (Group fitting)
- Each call to `fit_group_with_background()`
- Includes group ID and number of sources

### gaussfit.py (Isolated source fitting)
- Each call to `fit_isolated_gaussian()`
- Includes source ID

### detection.py (Source detection)
- Each call to `detect_sources()`
- Includes number of sources found

## Summary Statistics

At the end of each log file, a summary is automatically generated:

```
================================================================================
PERFORMANCE SUMMARY
================================================================================
Total execution time: 123.45s (2.06 minutes)

Script                              Time (s)     % of Total  
--------------------------------------------------------------------------------
single_map.py                          85.30s       69.1%
fitting.py                             25.40s       20.6%
gaussfit.py                             8.50s        6.9%
detection.py                            2.50s        2.0%
hyper.py                                1.75s        1.4%
```

## Finding Specific Code Sections

Each timing entry includes:
1. **Script name**: Which file the code is in
2. **Line range**: Exact lines being timed (e.g., `27-80`)
3. **Description**: What operation was performed
4. **Additional context**: Source IDs, group IDs, number of sources, etc.

To find the code:
```bash
# Open the file and go to the specified lines
vim +27 hyper_py_playground/single_map.py
```

## Example Usage

The timing is completely automatic - just run Hyper-py normally:

```bash
hyper-py hyper_config-playground.yaml
```

After execution, check the performance logs:

```bash
# View the latest timing log
ls -lt output-playground/performance_logs/
cat output-playground/performance_logs/performance_timing_map_name_20231208_102345.log
```

## Interpreting Results

### Look for:
- **High percentages** in the summary (operations taking most time)
- **Long durations** for individual operations
- **Repeated slow operations** (e.g., slow per-source fitting)
- **I/O operations** that might benefit from caching

### Common bottlenecks:
1. **Fitting blended sources** - Usually the slowest operation
2. **Fitting isolated sources** - Can be slow with many sources
3. **Reading and preparing maps** - I/O bound
4. **Source detection** - Depends on map size and number of sources

## Overhead

The performance timing adds minimal overhead:
- ~0.1ms per timing call
- No impact on computation results
- Logs are written incrementally (no memory buildup)

## Thread Safety

The timer is thread-safe and works correctly with:
- Parallel map processing
- Multiple Python processes
- Concurrent logging from different sources

## Disabling Timing

To disable timing (not recommended), comment out the timer initialization in:
- `hyper.py` (line ~73)
- `single_map.py` (line ~83)

## Tips for Optimization

1. **Focus on the top 3-4 operations** from the summary
2. **Check if blended source fitting** can be optimized (different algorithms)
3. **Monitor I/O times** - consider faster storage or caching
4. **Profile individual functions** if needed (use Python's cProfile)
5. **Compare timing across different runs** to measure improvements

## Questions?

The timing module is in: `hyper_py_playground/performance_timer.py`

Key functions:
- `init_timer(output_dir, map_name)` - Initialize a timer
- `timer.measure(script, start_line, end_line, description)` - Context manager for timing
- `timer.log_timing(...)` - Manual timing logging
- `timer.write_summary()` - Generate summary statistics

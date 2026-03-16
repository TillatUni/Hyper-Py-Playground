#!/usr/bin/env python3
"""
Run hyper-py from the playground fork with all optimizations.
Usage: python run_hyper_playground.py hyper_config-playground.yaml

IMPORTANT: Thread limits MUST be set before Python imports numpy.
This script reads the config file to determine threads_per_worker dynamically.
"""
import sys
import os
import warnings

# ============================================================================
# CRITICAL: Thread limit configuration - MUST happen before numpy import
# OpenBLAS reads environment variables at C library load time, which happens
# BEFORE Python code runs if numpy is imported at module scope.
# We MUST override all thread vars before any numpy/scipy import.
# ============================================================================

# Use a marker to detect if we're the main process or a spawned worker
# Spawned workers inherit HYPER_THREAD_CONFIG_DONE and the thread vars from parent
if os.environ.get('HYPER_THREAD_CONFIG_DONE') != '1':
    # Mark that we've configured threads (workers will inherit this)
    os.environ['HYPER_THREAD_CONFIG_DONE'] = '1'
    
    # Read config to determine n_cores and max_total_threads
    def _get_thread_config():
        """Read config to calculate threads per worker. Must run before numpy import."""
        import yaml  # yaml is safe to import early
        
        # Default values
        n_cores = os.cpu_count() or 6
        max_total_threads = 50
        
        # Try to read from config file
        if len(sys.argv) >= 2:
            config_path = sys.argv[1]
            if not os.path.isabs(config_path):
                config_path = os.path.join(os.getcwd(), config_path)
            try:
                with open(config_path, 'r') as f:
                    cfg = yaml.safe_load(f)
                control = cfg.get('control', {})
                n_cores = control.get('n_cores', n_cores)
                max_total_threads = control.get('max_total_threads', max_total_threads)
            except Exception:
                pass  # Use defaults if config can't be read
        
        # Calculate threads per worker (at least 1)
        threads_per_worker = max(1, max_total_threads // n_cores)
        return threads_per_worker, n_cores, max_total_threads

    _threads_per_worker, _n_cores, _max_total = _get_thread_config()

    # Set thread limits BEFORE numpy/sklearn imports to prevent oversubscription
    # IMPORTANT: We use os.putenv() AND os.environ to ensure C libraries see the change
    for var in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
        os.environ[var] = str(_threads_per_worker)
        os.putenv(var, str(_threads_per_worker))

    print(f"🔧 Thread config: {_threads_per_worker} threads/worker × {_n_cores} workers = {_threads_per_worker * _n_cores} max total (limit: {_max_total})")

# Suppress common warnings that flood the output
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', message='.*ConvergenceWarning.*')
warnings.filterwarnings('ignore', message='.*FITSFixedWarning.*')
warnings.filterwarnings('ignore', message='.*OBSGEO.*')
warnings.filterwarnings('ignore', message='.*lbfgs failed to converge.*')
warnings.filterwarnings('ignore', message='.*disp.*iprint.*deprecated.*')
warnings.filterwarnings('ignore', message='.*overflow.*')
warnings.filterwarnings('ignore', message='.*The fit may be unsuccessful.*')

# Add the playground directory to path so it imports the local version
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# CRITICAL: Import numpy FIRST, then immediately apply thread limits with ThreadpoolController
# This is necessary because OpenBLAS ignores os.environ if set after the library loads
# The library loads when numpy is imported, so we must apply limits after that
import numpy as np  # This loads OpenBLAS

try:
    from threadpoolctl import ThreadpoolController
    _max_threads = int(os.environ.get('OMP_NUM_THREADS', '8'))
    _controller = ThreadpoolController()
    _controller.limit(limits=_max_threads, user_api='blas')
    print(f"🔒 BLAS thread limit enforced: {_max_threads} threads per process")
except ImportError:
    print("⚠️ threadpoolctl not available - thread limits may not be enforced")

from hyper_py_playground.hyper import start_hyper

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_hyper_playground.py <config.yaml>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.getcwd(), config_path)
    
    start_hyper(config_path)

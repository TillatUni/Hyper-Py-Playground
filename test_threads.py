#!/usr/bin/env python3
"""Test thread inheritance in spawned workers."""
import os
import sys
import multiprocessing

# Set thread limits BEFORE any numpy imports
os.environ['HYPER_THREAD_CONFIG_DONE'] = '1'
os.environ['OMP_NUM_THREADS'] = '8'
os.environ['MKL_NUM_THREADS'] = '8'
os.environ['OPENBLAS_NUM_THREADS'] = '8'
os.environ['NUMEXPR_NUM_THREADS'] = '8'

print('Parent process settings (before numpy):')
print(f'  OMP_NUM_THREADS={os.environ.get("OMP_NUM_THREADS")}')

# Now import numpy
import numpy as np
from threadpoolctl import threadpool_info, threadpool_limits
from concurrent.futures import ProcessPoolExecutor

# Check parent BLAS threads
parent_info = threadpool_info()
print(f'Parent BLAS after numpy import: {[lib["num_threads"] for lib in parent_info if lib["user_api"] == "blas"]}')


def worker_check(x):
    """Worker function - must be top-level for pickle."""
    import os
    import numpy as np
    from threadpoolctl import threadpool_info, threadpool_limits
    
    omp = os.environ.get('OMP_NUM_THREADS', 'NOT SET')
    marker = os.environ.get('HYPER_THREAD_CONFIG_DONE', 'NOT SET')
    
    # Force numpy to do something
    a = np.random.rand(100, 100)
    _ = np.linalg.inv(a)
    
    info = threadpool_info()
    blas_threads = [lib['num_threads'] for lib in info if lib['user_api'] == 'blas']
    
    # Test with threadpool_limits
    with threadpool_limits(limits=8, user_api='blas'):
        info_limited = threadpool_info()
        blas_limited = [lib['num_threads'] for lib in info_limited if lib['user_api'] == 'blas']
    
    return f'Worker {x}: OMP_env={omp}, BLAS_default={blas_threads}, BLAS_limited={blas_limited}'


if __name__ == '__main__':
    # Use spawn
    multiprocessing.set_start_method('spawn', force=True)
    
    print('\nSpawning 3 workers...')
    with ProcessPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(worker_check, range(3)))
    
    print('\nWorker results:')
    for r in results:
        print(f'  {r}')

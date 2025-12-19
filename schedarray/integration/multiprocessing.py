#!/usr/bin/env python3
"""
Integration with multiprocessing utilities.

This module provides integration between SchedArray and the existing
multiprocessing utilities, allowing large batches to be submitted
to the scheduler instead of using ProcessPoolExecutor directly.
"""

import time
from typing import Any, Callable, List, Optional, Tuple

from decologr.logger import Logger as log

from schedarray.core.scheduler import JobState, SqliteJobScheduler
from schedarray.core.worker_pool import WorkerPoolManager


class SchedArrayMultiprocessingIntegration:
    """
    Integration between SchedArray and multiprocessing utilities.

    Provides methods to:
    - Submit batches of jobs to scheduler instead of ProcessPoolExecutor
    - Wait for job completion
    - Collect results
    """

    def __init__(
        self,
        scheduler: Optional[SqliteJobScheduler] = None,
        worker_pool: Optional[WorkerPoolManager] = None,
        max_workers: Optional[int] = None,
    ):
        """
        Initialize the integration.

        :param scheduler: Scheduler instance (default: creates new instance)
        :param worker_pool: Worker pool instance (default: creates new instance)
        :param max_workers: Maximum number of workers (default: CPU count)
        """
        self.scheduler = scheduler or SqliteJobScheduler()
        self.worker_pool = worker_pool or WorkerPoolManager(
            scheduler=self.scheduler, max_workers=max_workers
        )
        self._worker_pool_started = False

    def process_jobs_via_scheduler(
        self,
        job_func: Callable,
        job_args_list: List[Tuple],
        progress_callback: Optional[Callable[[int, int, Any], None]] = None,
        poll_interval: float = 1.0,
    ) -> List[Tuple[Any, Optional[Exception]]]:
        """
        Process jobs via scheduler instead of ProcessPoolExecutor.

        This is useful for large batches where you want persistence,
        priority scheduling, and better resource management.

        :param job_func: Function to call for each job
        :param job_args_list: List of argument tuples
        :param progress_callback: Optional progress callback
        :param poll_interval: Polling interval in seconds
        :return: List of (result, exception) tuples
        """
        if not job_args_list:
            return []

        total_jobs = len(job_args_list)

        # Start worker pool if not already started
        if not self._worker_pool_started:
            self.worker_pool.start_workers()
            self._worker_pool_started = True

        log.info(f"Submitting {total_jobs} jobs to scheduler")

        # Submit all jobs to scheduler
        job_ids = []
        for i, args in enumerate(job_args_list):
            # Create a command that will execute the function
            # For now, we'll need to serialize the function call
            # This is a simplified version - in practice, you'd want
            # a more robust serialization mechanism
            job_name = f"job_{i}_{job_func.__name__}"
            command = self._create_command_for_function(job_func, args)

            job_id = self.scheduler.submit_job(
                command=command,
                job_name=job_name,
                priority=total_jobs - i,  # Earlier jobs get higher priority
            )
            job_ids.append((job_id, args))

        log.info(f"Submitted {len(job_ids)} jobs, waiting for completion...")

        # Wait for all jobs to complete
        results = []
        completed = 0

        while completed < total_jobs:
            for job_id, args in job_ids:
                if job_id is None:  # Already processed
                    continue

                status = self.scheduler.get_job_status(job_id)
                if not status:
                    continue

                state = status.get("state")
                if state == JobState.COMPLETED.value:
                    # Job completed successfully
                    result = self._get_job_result(job_id, status)
                    results.append((result, None))
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total_jobs, result)
                    job_ids[job_ids.index((job_id, args))] = (None, args)

                elif state == JobState.FAILED.value:
                    # Job failed
                    error = self._get_job_error(job_id, status)
                    results.append((None, error))
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total_jobs, error)
                    job_ids[job_ids.index((job_id, args))] = (None, args)

                elif state in [
                    JobState.CANCELLED.value,
                    JobState.TIMEOUT.value,
                ]:
                    # Job cancelled or timed out
                    error = Exception(f"Job {state}")
                    results.append((None, error))
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total_jobs, error)
                    job_ids[job_ids.index((job_id, args))] = (None, args)

            if completed < total_jobs:
                time.sleep(poll_interval)

        return results

    def _create_command_for_function(
        self, job_func: Callable, args: Tuple
    ) -> str:
        """
        Create a command string to execute a function.

        This is a simplified version. In practice, you'd want to:
        - Serialize the function and arguments properly
        - Use a worker script that can deserialize and execute
        - Handle complex types and dependencies

        :param job_func: Function to execute
        :param args: Function arguments
        :return: Command string
        """
        # This is a placeholder - actual implementation would need
        # proper serialization and a worker script
        func_name = job_func.__name__
        args_str = " ".join(str(arg) for arg in args)
        return f"python -c 'from {job_func.__module__} import {func_name}; {func_name}({args_str})'"

    def _get_job_result(self, job_id: str, status: dict) -> Any:
        """
        Get result from completed job.

        :param job_id: Job ID
        :param status: Job status dictionary
        :return: Job result
        """
        # In practice, you'd read from output_file or metadata
        return status.get("return_code", 0)

    def _get_job_error(self, job_id: str, status: dict) -> Exception:
        """
        Get error from failed job.

        :param job_id: Job ID
        :param status: Job status dictionary
        :return: Exception object
        """
        error_file = status.get("error_file")
        if error_file:
            try:
                with open(error_file, "r") as f:
                    error_msg = f.read()
                return Exception(error_msg)
            except Exception:
                pass
        return Exception(f"Job {job_id} failed with return code {status.get('return_code', -1)}")

    def stop(self):
        """Stop the worker pool."""
        if self._worker_pool_started:
            self.worker_pool.stop_workers()
            self._worker_pool_started = False

# Global integration instance
_integration_instance: Optional[SchedArrayMultiprocessingIntegration] = None

def get_integration(
    max_workers: Optional[int] = None,
) -> SchedArrayMultiprocessingIntegration:
    """
    Get or create the global integration instance.

    :param max_workers: Maximum number of workers
    :return: SchedArrayMultiprocessingIntegration instance
    """
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = SchedArrayMultiprocessingIntegration(
            max_workers=max_workers
        )
    return _integration_instance


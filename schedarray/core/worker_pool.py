#!/usr/bin/env python3
"""
Worker pool manager for SQLite job scheduler.

Manages worker processes/threads that execute jobs from the scheduler queue.
"""

import multiprocessing
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from decologr.logger import Logger as log

from schedarray.core.scheduler import JobState, SqliteJobScheduler

class WorkerProcess:
    """Represents a single worker process."""

    def __init__(self, worker_id: str, max_cpus: int = 1):
        self.worker_id = worker_id
        self.max_cpus = max_cpus
        self.available_cpus = max_cpus
        self.current_job_id: Optional[str] = None
        self.process: Optional[subprocess.Popen] = None
        self.state = "idle"  # idle, busy, failed
        self.last_heartbeat = time.time()

    def assign_job(self, job_id: str) -> bool:
        """Assign a job to this worker."""
        if self.state != "idle" or self.available_cpus < 1:
            return False
        self.current_job_id = job_id
        self.state = "busy"
        self.available_cpus -= 1
        return True

    def release_job(self):
        """Release the current job."""
        self.current_job_id = None
        self.state = "idle"
        self.available_cpus = self.max_cpus
        self.last_heartbeat = time.time()

    def is_alive(self) -> bool:
        """Check if worker is alive."""
        if self.process is None:
            return True  # Thread-based worker
        return self.process.poll() is None

class WorkerPoolManager:
    """
    Manages worker processes/threads that execute jobs.

    - Creates worker pool on startup
    - Assigns jobs to workers based on resources
    - Monitors worker health
    - Handles worker failures
    """

    def __init__(
        self,
        scheduler: SqliteJobScheduler,
        max_workers: Optional[int] = None,
        poll_interval: float = 1.0,
    ):
        """
        Initialize the worker pool manager.

        :param scheduler: SQLite job scheduler instance
        :param max_workers: Maximum number of workers (default: CPU count)
        :param poll_interval: Polling interval in seconds for checking jobs
        """
        self.scheduler = scheduler
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.poll_interval = poll_interval

        self.workers: Dict[str, WorkerProcess] = {}
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

    def start_workers(self):
        """Start the worker pool."""
        if self.running:
            log.warning("Worker pool already running")
            return

        self.running = True

        # Create worker processes
        for i in range(self.max_workers):
            worker_id = f"worker_{i+1}_{uuid.uuid4().hex[:8]}"
            worker = WorkerProcess(worker_id, max_cpus=1)
            self.workers[worker_id] = worker

        log.info(f"Started worker pool with {len(self.workers)} workers")

        # Start worker thread
        self.worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="WorkerPoolManager"
        )
        self.worker_thread.start()

    def stop_workers(self):
        """Gracefully stop all workers."""
        if not self.running:
            return

        log.info("Stopping worker pool...")
        self.running = False

        # Wait for worker thread to finish
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)

        # Cancel any running jobs
        with self.lock:
            for worker in self.workers.values():
                if worker.current_job_id:
                    self.scheduler.cancel_job(worker.current_job_id)
                    worker.release_job()

        log.info("Worker pool stopped")

    def _worker_loop(self):
        """Main worker loop that assigns and monitors jobs."""
        while self.running:
            try:
                # Get pending jobs
                pending_jobs = self.scheduler.get_pending_jobs(limit=self.max_workers)

                # Assign jobs to available workers
                for job in pending_jobs:
                    job_id = job["job_id"]
                    worker = self._find_available_worker()

                    if worker:
                        if self._assign_and_execute_job(worker, job):
                            log.debug(
                                f"Assigned job {job_id} ({job['job_name']}) to {worker.worker_id}"
                            )
                    else:
                        # No available workers, break and wait
                        break

                # Check running jobs for completion
                self._check_running_jobs()

                # Monitor worker health
                self._check_worker_health()

            except Exception as ex:
                log.error(f"Error in worker loop: {ex}")

            time.sleep(self.poll_interval)

    def _find_available_worker(self) -> Optional[WorkerProcess]:
        """Find an available worker."""
        with self.lock:
            for worker in self.workers.values():
                if worker.state == "idle" and worker.available_cpus > 0:
                    return worker
        return None

    def _assign_and_execute_job(
        self, worker: WorkerProcess, job: Dict[str, Any]
    ) -> bool:
        """
        Assign a job to a worker and start execution.

        :param worker: Worker to assign job to
        :param job: Job dictionary from scheduler
        :return: True if assigned successfully
        """
        job_id = job["job_id"]
        command = job["command"]
        working_dir = job.get("working_dir")
        output_file = job.get("output_file")
        error_file = job.get("error_file")

        if not worker.assign_job(job_id):
            return False

        # Update job state to running
        self.scheduler.update_job_state(job_id, JobState.RUNNING)

        # Get timeout from job metadata
        timeout = job.get("timeout")

        # Start execution in a separate thread
        thread = threading.Thread(
            target=self._execute_job,
            args=(worker, job_id, command, working_dir, output_file, error_file, timeout),
            daemon=True,
        )
        thread.start()

        return True

    def _execute_job(
        self,
        worker: WorkerProcess,
        job_id: str,
        command: str,
        working_dir: Optional[str],
        output_file: Optional[str],
        error_file: Optional[str],
        timeout: Optional[int] = None,
    ):
        """
        Execute a job in a subprocess.

        :param worker: Worker executing the job
        :param job_id: Job ID
        :param command: Command to execute
        :param working_dir: Working directory
        :param output_file: Output file path
        :param error_file: Error file path
        :param timeout: Optional timeout in seconds
        """
        try:
            # Prepare output/error file handles
            stdout_handle = None
            stderr_handle = None

            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                stdout_handle = open(output_path, "w")
            if error_file:
                error_path = Path(error_file)
                error_path.parent.mkdir(parents=True, exist_ok=True)
                stderr_handle = open(error_path, "w")

            # Execute command
            cwd = Path(working_dir) if working_dir else None
            if cwd and not cwd.exists():
                raise FileNotFoundError(f"Working directory does not exist: {working_dir}")

            process = subprocess.Popen(
                command,
                shell=True,
                cwd=str(cwd) if cwd else None,
                stdout=stdout_handle or subprocess.PIPE,
                stderr=stderr_handle or subprocess.PIPE,
                text=True,
            )

            worker.process = process

            # Wait for completion with optional timeout
            try:
                return_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Kill the process if it times out
                process.kill()
                process.wait()
                log.warning(f"Job {job_id} timed out after {timeout} seconds")
                self.scheduler.update_job_state(job_id, JobState.TIMEOUT)
                return

            # Capture stdout/stderr if using PIPE (not writing to files)
            stdout_text = ""
            stderr_text = ""
            if not stdout_handle and process.stdout:
                stdout_text = process.stdout.read()
            if not stderr_handle and process.stderr:
                stderr_text = process.stderr.read()

            # Close file handles
            if stdout_handle:
                stdout_handle.close()
            if stderr_handle:
                stderr_handle.close()

            # Update job state with captured output
            if return_code == 0:
                self.scheduler.update_job_state(
                    job_id, JobState.COMPLETED, return_code=return_code, output=stdout_text, error=stderr_text
                )
            else:
                self.scheduler.update_job_state(
                    job_id, JobState.FAILED, return_code=return_code, output=stdout_text, error=stderr_text
                )

        except Exception as ex:
            log.error(f"Error executing job {job_id}: {ex}")
            self.scheduler.update_job_state(job_id, JobState.FAILED, error=str(ex))
        finally:
            # Release worker
            worker.release_job()
            worker.process = None

    def _check_running_jobs(self):
        """Check status of running jobs."""
        running_jobs = self.scheduler.get_running_jobs()

        with self.lock:
            for job in running_jobs:
                job_id = job["job_id"]

                # Find worker for this job
                worker = None
                for w in self.workers.values():
                    if w.current_job_id == job_id:
                        worker = w
                        break

                if not worker:
                    # Job marked as running but no worker assigned - mark as failed
                    log.warning(f"Job {job_id} marked as running but no worker found")
                    self.scheduler.update_job_state(job_id, JobState.FAILED)
                elif worker.process and not worker.is_alive():
                    # Process died unexpectedly
                    return_code = worker.process.returncode
                    log.warning(
                        f"Job {job_id} process died unexpectedly with return code {return_code}"
                    )
                    self.scheduler.update_job_state(
                        job_id, JobState.FAILED, return_code=return_code
                    )
                    worker.release_job()

    def _check_worker_health(self):
        """Check health of all workers."""
        with self.lock:
            for worker_id, worker in list(self.workers.items()):
                if not worker.is_alive() and worker.state == "busy":
                    log.warning(f"Worker {worker_id} died while processing job")
                    if worker.current_job_id:
                        self.scheduler.update_job_state(
                            worker.current_job_id, JobState.FAILED
                        )
                    worker.release_job()

    def get_worker_status(self) -> Dict[str, Any]:
        """
        Get status of all workers.

        :return: Dictionary with worker status information
        """
        with self.lock:
            workers_info = []
            for worker in self.workers.values():
                workers_info.append(
                    {
                        "worker_id": worker.worker_id,
                        "state": worker.state,
                        "current_job_id": worker.current_job_id,
                        "available_cpus": worker.available_cpus,
                        "max_cpus": worker.max_cpus,
                    }
                )

            return {
                "total_workers": len(self.workers),
                "running": self.running,
                "workers": workers_info,
            }

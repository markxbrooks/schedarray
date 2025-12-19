#!/usr/bin/env python3
"""
Integration with slurmify_run to route jobs through SchedArray.

This module provides a drop-in replacement for slurmify_run that routes
jobs through the SchedArray scheduler instead of executing directly or via SLURM.
"""

import datetime
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from mxlib.adapters.environment.slurm.slurmify import slurmify_run
from mxlib.commands.ccp4.command import wrap_ccp4_by_platform
from mxlib.commands.string import to_command_string
from decologr.logger import Logger as log
from mxlib.platform import resolve_platform_info

from schedarray.core.scheduler import JobState, SqliteJobScheduler
from schedarray.core.worker_pool import WorkerPoolManager

# Global scheduler and worker pool instances
_global_scheduler: Optional[SqliteJobScheduler] = None
_global_worker_pool: Optional[WorkerPoolManager] = None

def schedarray_run(
    command: str | list[str],
    *,
    dry_run: bool = False,
    slurmify: bool = False,
    requires_wsl: bool = False,
    cpus: int = None,
    memory: str = None,
    time_limit: str = None,
    partition: str = None,
    job_name: str = None,
    working_dir: str = None,
    wait_for_completion: bool = True,
    scheduler: Optional[SqliteJobScheduler] = None,
    worker_pool: Optional[WorkerPoolManager] = None,
) -> Optional[object]:
    """
    Run a command via SchedArray scheduler (drop-in replacement for slurmify_run).

    This function mirrors the interface of slurmify_run but routes jobs through
    the SchedArray scheduler instead of executing directly or via SLURM.

    :param command: Command string or list of arguments to execute
    :param dry_run: If True, print but do not execute
    :param slurmify: If True and SLURM available, use SLURM; otherwise use SchedArray
    :param requires_wsl: If True, the command *must* run inside WSL on Windows
    :param cpus: Number of CPUs to request (default: 1)
    :param memory: Memory requirement (e.g., "4G")
    :param time_limit: Time limit in HH:MM:SS format (converted to seconds)
    :param partition: Partition name (ignored for SchedArray)
    :param job_name: Optional job name (defaults to auto-generated)
    :param working_dir: Working directory for the command
    :param wait_for_completion: If True, wait for job to complete before returning
    :param scheduler: Optional scheduler instance (default: creates new)
    :param worker_pool: Optional worker pool instance (default: creates new)
    :return: CompletedProcess-like object or job_id if wait_for_completion=False
    """
    platform_info = resolve_platform_info()
    command = to_command_string(command)

    # Determine working directory
    if not working_dir:
        working_dir = os.getcwd()
    working_dir = Path(working_dir).resolve()

    # Check if SLURM is available and slurmify is requested
    use_slurm = False
    if slurmify and not platform_info.is_windows:
        # Check if SLURM is available
        try:
            import subprocess
            result = subprocess.run(
                ["sbatch", "--version"], capture_output=True, timeout=2
            )
            if result.returncode == 0:
                use_slurm = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # If SLURM is available and requested, use original slurmify_run
    if use_slurm:
        log.debug("SLURM available, using slurmify_run")
        return slurmify_run(
            command=command,
            dry_run=dry_run,
            slurmify=slurmify,
            requires_wsl=requires_wsl,
            cpus=cpus,
            memory=memory,
            time_limit=time_limit,
            partition=partition,
            job_name=job_name,
            working_dir=str(working_dir),
        )

    # Otherwise, use SchedArray
    log.debug("Using SchedArray scheduler")

    # Prepare command for platform (CCP4, WSL wrapping)
    if not slurmify:  # Only wrap if not going through SLURM
        command = wrap_ccp4_by_platform(command, platform_info, requires_wsl)

    # Log for validation
    log.message(
        f"[schedarray_run] command=\n{command}, dry_run={dry_run}, slurmify={slurmify}"
    )

    if dry_run:
        return None

    # Get or create scheduler and worker pool (use global instances)
    global _global_scheduler, _global_worker_pool
    
    if scheduler is None:
        if _global_scheduler is None:
            _global_scheduler = SqliteJobScheduler()
        scheduler = _global_scheduler
    
    if worker_pool is None:
        if _global_worker_pool is None:
            _global_worker_pool = WorkerPoolManager(scheduler, max_workers=None)
        worker_pool = _global_worker_pool
        # Start workers if not already running
        if not worker_pool.running:
            worker_pool.start_workers()

    # Convert time_limit from HH:MM:SS to seconds
    timeout_seconds = None
    if time_limit:
        try:
            parts = time_limit.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                timeout_seconds = hours * 3600 + minutes * 60 + seconds
        except (ValueError, AttributeError):
            log.warning(f"Invalid time_limit format: {time_limit}, ignoring")

    # Generate job name if not provided
    if not job_name:
        job_name = f"job_{int(datetime.datetime.now().timestamp())}"

    # Submit job to scheduler
    job_id = scheduler.submit_job(
        command=command,
        working_dir=str(working_dir),
        job_name=job_name,
        cpus=cpus or 1,
        memory=memory,
        timeout=timeout_seconds,
        priority=5,  # Default priority
    )

    log.info(f"Submitted job {job_id} ({job_name}) to SchedArray")

    if not wait_for_completion:
        # Return job ID for async execution
        return {"job_id": job_id, "scheduler": scheduler}

    # Wait for completion
    poll_interval = 0.5
    max_wait_time = timeout_seconds or (24 * 3600)  # Default 24 hours
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        status = scheduler.get_job_status(job_id)
        if not status:
            log.error(f"Job {job_id} not found in scheduler")
            break

        state = status.get("state")
        if state == JobState.COMPLETED.value:
            return_code = status.get("return_code", 0)
            # Get output/error from metadata or output_file/error_file
            stdout_text = ""
            stderr_text = ""
            
            # Try to get from metadata first (for captured PIPE output)
            metadata = status.get("metadata", {})
            if isinstance(metadata, str):
                import json
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            if isinstance(metadata, dict):
                stdout_text = metadata.get("stdout", "")
                stderr_text = metadata.get("stderr", "")
            
            # If not in metadata, try reading from output files
            if not stdout_text:
                output_file = status.get("output_file")
                if output_file and Path(output_file).exists():
                    try:
                        stdout_text = Path(output_file).read_text()
                    except Exception:
                        pass
            
            if not stderr_text:
                error_file = status.get("error_file")
                if error_file and Path(error_file).exists():
                    try:
                        stderr_text = Path(error_file).read_text()
                    except Exception:
                        pass
            
            # Return CompletedProcess-like object
            class CompletedProcess:
                def __init__(self, returncode, stdout="", stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            return CompletedProcess(returncode=return_code, stdout=stdout_text, stderr=stderr_text)
        elif state == JobState.FAILED.value:
            return_code = status.get("return_code", 1)
            # Get output/error from metadata or output_file/error_file
            stdout_text = ""
            stderr_text = ""
            
            # Try to get from metadata first (for captured PIPE output)
            metadata = status.get("metadata", {})
            if isinstance(metadata, str):
                import json
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            if isinstance(metadata, dict):
                stdout_text = metadata.get("stdout", "")
                stderr_text = metadata.get("stderr", "")
            
            # If not in metadata, try reading from output files
            if not stdout_text:
                output_file = status.get("output_file")
                if output_file and Path(output_file).exists():
                    try:
                        stdout_text = Path(output_file).read_text()
                    except Exception:
                        pass
            
            if not stderr_text:
                error_file = status.get("error_file")
                if error_file and Path(error_file).exists():
                    try:
                        stderr_text = Path(error_file).read_text()
                    except Exception:
                        pass
            
            class CompletedProcess:
                def __init__(self, returncode, stdout="", stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            return CompletedProcess(returncode=return_code, stdout=stdout_text, stderr=stderr_text)
        elif state in [
            JobState.CANCELLED.value,
            JobState.TIMEOUT.value,
        ]:
            log.warning(f"Job {job_id} was {state}")
            class CompletedProcess:
                def __init__(self, returncode, stdout="", stderr=""):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            return CompletedProcess(returncode=1)

        time.sleep(poll_interval)

    # Timeout waiting for job
    log.error(f"Job {job_id} did not complete within {max_wait_time} seconds")
    class CompletedProcess:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    return CompletedProcess(returncode=1)

def slurmify_run_with_schedarray(
    command: str | list[str],
    *,
    dry_run: bool = False,
    slurmify: bool = False,
    requires_wsl: bool = False,
    cpus: int = None,
    memory: str = None,
    time_limit: str = None,
    partition: str = None,
    job_name: str = None,
    working_dir: str = None,
    use_schedarray: bool = True,
) -> Optional[object]:
    """
    Enhanced slurmify_run that can route to SchedArray.

    This is a wrapper that adds SchedArray support to slurmify_run.
    Set use_schedarray=True to enable SchedArray routing.

    :param use_schedarray: If True, use SchedArray when SLURM unavailable
    :param ...: All other parameters same as slurmify_run
    :return: CompletedProcess or None
    """
    if use_schedarray:
        return schedarray_run(
            command=command,
            dry_run=dry_run,
            slurmify=slurmify,
            requires_wsl=requires_wsl,
            cpus=cpus,
            memory=memory,
            time_limit=time_limit,
            partition=partition,
            job_name=job_name,
            working_dir=working_dir,
            wait_for_completion=True,
        )
    else:
        # Use original slurmify_run
        return slurmify_run(
            command=command,
            dry_run=dry_run,
            slurmify=slurmify,
            requires_wsl=requires_wsl,
            cpus=cpus,
            memory=memory,
            time_limit=time_limit,
            partition=partition,
            job_name=job_name,
            working_dir=working_dir,
        )


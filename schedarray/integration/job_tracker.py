#!/usr/bin/env python3
"""
Integration with mxpandda JobTracker system.

This module provides integration between SchedArray and the existing
JobTracker, allowing jobs to be submitted via the scheduler and tracked
through the JobTracker system.
"""

from typing import Optional

from decologr.logger import Logger as log

from schedarray.core.scheduler import JobState, SqliteJobScheduler

class SchedArrayJobTrackerIntegration:
    """
    Integration between SchedArray and JobTracker.

    Provides methods to:
    - Submit jobs to scheduler and register with JobTracker
    - Poll scheduler job status for JobTracker
    - Map scheduler states to JobTracker states
    """

    def __init__(self, scheduler: Optional[SqliteJobScheduler] = None):
        """
        Initialize the integration.

        :param scheduler: Scheduler instance (default: creates new instance)
        """
        self.scheduler = scheduler or SqliteJobScheduler()

    def submit_job_to_scheduler(
        self,
        command: str,
        job_name: str,
        working_dir: Optional[str] = None,
        cpus: int = 1,
        memory: Optional[str] = None,
        timeout: Optional[int] = None,
        priority: int = 0,
        output_file: Optional[str] = None,
        error_file: Optional[str] = None,
    ) -> str:
        """
        Submit a job to the scheduler and return the scheduler job ID.

        :param command: Command to execute
        :param job_name: Job name
        :param working_dir: Working directory
        :param cpus: Number of CPUs
        :param memory: Memory limit
        :param timeout: Timeout in seconds
        :param priority: Job priority
        :param output_file: Output file path
        :param error_file: Error file path
        :return: Scheduler job ID
        """
        job_id = self.scheduler.submit_job(
            command=command,
            working_dir=working_dir,
            job_name=job_name,
            cpus=cpus,
            memory=memory,
            timeout=timeout,
            priority=priority,
            output_file=output_file,
            error_file=error_file,
        )
        log.info(f"Submitted job {job_name} to scheduler with ID {job_id}")
        return job_id

    def poll_scheduler_status(self, scheduler_job_id: str) -> str:
        """
        Poll scheduler job status and map to JobTracker state.

        :param scheduler_job_id: Scheduler job ID
        :return: JobTracker state string (lowercase)
        """
        job_status = self.scheduler.get_job_status(scheduler_job_id)
        if not job_status:
            return "unknown"

        state = job_status.get("state", "unknown")
        mapped = self._map_scheduler_state_to_tracked_state(state)
        # Return lowercase to match JobTracker expectations
        return mapped.lower() if mapped else "unknown"

    @staticmethod
    def _map_scheduler_state_to_tracked_state(scheduler_state: str) -> str:
        """
        Map SchedArray job state to JobTracker state.

        :param scheduler_state: SchedArray job state
        :return: JobTracker state string
        """
        state_mapping = {
            JobState.PENDING.value: "pending",
            JobState.RUNNING.value: "running",
            JobState.COMPLETED.value: "completed",
            JobState.FAILED.value: "failed",
            JobState.CANCELLED.value: "cancelled",
            JobState.TIMEOUT.value: "timeout",
        }
        return state_mapping.get(scheduler_state, "unknown")

    def cancel_scheduler_job(self, scheduler_job_id: str) -> bool:
        """
        Cancel a scheduler job.

        :param scheduler_job_id: Scheduler job ID
        :return: True if cancelled successfully
        """
        return self.scheduler.cancel_job(scheduler_job_id)

# Global integration instance
_integration_instance: Optional[SchedArrayJobTrackerIntegration] = None

def get_integration() -> SchedArrayJobTrackerIntegration:
    """
    Get or create the global integration instance.

    :return: SchedArrayJobTrackerIntegration instance
    """
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = SchedArrayJobTrackerIntegration()
    return _integration_instance


"""
SchedArray - Cross-platform job scheduler using SQLite.

A SLURM/SGE-like job scheduler that works on Windows, macOS, and Linux
using SQLite as the backend for persistence and job queue management.
"""

from schedarray.core.scheduler import SqliteJobScheduler, JobState
from schedarray.core.worker_pool import WorkerPoolManager, WorkerProcess
from schedarray.core.service import SchedulerService
from schedarray.task import task

__all__ = [
    "SqliteJobScheduler",
    "WorkerPoolManager",
    "WorkerProcess",
    "SchedulerService",
    "JobState",
    "task",
]

# Global scheduler instance
scheduler = SqliteJobScheduler()


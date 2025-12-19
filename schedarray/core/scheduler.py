#!/usr/bin/env python3
"""
SQLite-based job scheduler similar to SLURM/SGE.

This module provides a job scheduler that uses SQLite for persistence,
making it cross-platform and suitable for Windows, macOS, and Linux.

Provides:
- Job submission (like sbatch/qsub)
- Job status checking (like squeue/qstat)
- Job cancellation (like scancel/qdel)
- Resource management
- Worker pool management (Phase 2)
"""

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from decologr.logger import Logger as log, log_exception


class JobState(Enum):
    """Job states in the scheduler"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class SqliteJobScheduler:
    """
    SQLite-based job scheduler similar to SLURM/SGE.

    Provides:
    - Job submission (like sbatch/qsub)
    - Job status checking (like squeue/qstat)
    - Job cancellation (like scancel/qdel)
    - Resource management
    - Worker pool management (Phase 2)
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the SQLite job scheduler.

        :param db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default to user's home directory or mxpandda data directory
            try:
                from mxlib.globals import MXLIB_DATA_DIR

                db_path = Path(MXLIB_DATA_DIR) / "schedarray_scheduler.db"
            except ImportError:
                # Fallback to user's home directory
                db_path = Path.home() / ".schedarray" / "scheduler.db"
        else:
            db_path = Path(db_path)

        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.lock = threading.Lock()

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with required tables"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Create job_queue table (similar to SLURM's job queue)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS job_queue (
                    job_id TEXT PRIMARY KEY,
                    job_name TEXT NOT NULL,
                    command TEXT NOT NULL,
                    working_dir TEXT,
                    priority INTEGER DEFAULT 0,
                    state TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    cpu_limit INTEGER,
                    memory_limit TEXT,
                    timeout INTEGER,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    output_file TEXT,
                    error_file TEXT,
                    return_code INTEGER,
                    worker_id TEXT,
                    metadata TEXT,
                    user TEXT
                )
                """
            )

            # Create worker_nodes table (for future distributed execution)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS worker_nodes (
                    worker_id TEXT PRIMARY KEY,
                    hostname TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    max_cpus INTEGER,
                    available_cpus INTEGER,
                    max_memory TEXT,
                    available_memory TEXT,
                    state TEXT NOT NULL,
                    last_heartbeat TEXT,
                    registered_at TEXT NOT NULL
                )
                """
            )

            # Create resource_usage table for tracking
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS resource_usage (
                    usage_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    cpu_usage REAL,
                    memory_usage TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES job_queue(job_id)
                )
                """
            )

            # Create indexes for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_job_queue_state ON job_queue(state)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_job_queue_priority ON job_queue(priority DESC, submitted_at ASC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_job_queue_user ON job_queue(user)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_worker_nodes_state ON worker_nodes(state)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_resource_usage_job_id ON resource_usage(job_id)"
            )

            conn.commit()
        except Exception as ex:
            log_exception(ex, "Error initializing scheduler database")
            conn.rollback()
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper settings"""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def submit_job(
        self,
        command: str,
        working_dir: Optional[str] = None,
        job_name: Optional[str] = None,
        cpus: int = 1,
        memory: Optional[str] = None,
        timeout: Optional[int] = None,
        priority: int = 0,
        max_retries: int = 3,
        output_file: Optional[str] = None,
        error_file: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Submit a job to the scheduler (like sbatch/qsub).

        :param command: Command to execute
        :param working_dir: Working directory for the job
        :param job_name: Optional job name (defaults to auto-generated)
        :param cpus: Number of CPUs requested (default: 1)
        :param memory: Memory limit (e.g., "4G", "512M")
        :param timeout: Timeout in seconds
        :param priority: Job priority (higher = more priority, default: 0)
        :param max_retries: Maximum number of retries on failure (default: 3)
        :param output_file: Optional output file path
        :param error_file: Optional error file path
        :param metadata: Optional metadata dictionary
        :return: Job ID
        """
        job_id = str(uuid.uuid4())
        job_name = job_name or f"job_{int(datetime.now().timestamp())}"
        user = os.getenv("USER") or os.getenv("USERNAME") or "unknown"

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO job_queue (
                    job_id, job_name, command, working_dir, priority, state,
                    submitted_at, cpu_limit, memory_limit, timeout,
                    max_retries, output_file, error_file, metadata, user
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    job_name,
                    command,
                    working_dir,
                    priority,
                    JobState.PENDING.value,
                    datetime.now().isoformat(),
                    cpus,
                    memory,
                    timeout,
                    max_retries,
                    output_file,
                    error_file,
                    json.dumps(metadata or {}),
                    user,
                ),
            )
            conn.commit()
            log.info(f"Submitted job {job_id} ({job_name}) to scheduler")
            return job_id
        except Exception as ex:
            log_exception(ex, f"Error submitting job {job_id}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status (like squeue/qstat).

        :param job_id: Job ID
        :return: Job status dictionary or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM job_queue WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None

            job_dict = dict(row)
            job_dict["metadata"] = json.loads(job_dict.get("metadata") or "{}")
            return job_dict
        except Exception as ex:
            log_exception(ex, f"Error getting job status {job_id}")
            return None
        finally:
            conn.close()

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job (like scancel/qdel).

        :param job_id: Job ID
        :return: True if cancelled successfully, False otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Check if job exists and is cancellable
            cursor.execute(
                "SELECT state FROM job_queue WHERE job_id = ?", (job_id,)
            )
            row = cursor.fetchone()
            if not row:
                log.warning(f"Job {job_id} not found")
                return False

            state = row["state"]
            if state in [JobState.COMPLETED.value, JobState.CANCELLED.value]:
                log.warning(f"Job {job_id} is already {state}, cannot cancel")
                return False

            # Update job state to cancelled
            cursor.execute(
                """
                UPDATE job_queue
                SET state = ?, completed_at = ?
                WHERE job_id = ?
                """,
                (JobState.CANCELLED.value, datetime.now().isoformat(), job_id),
            )
            conn.commit()
            log.info(f"Cancelled job {job_id}")
            return True
        except Exception as ex:
            log_exception(ex, f"Error cancelling job {job_id}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def list_jobs(
        self,
        state: Optional[str] = None,
        user: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List jobs (like squeue -u user).

        :param state: Filter by job state (PENDING, RUNNING, COMPLETED, etc.)
        :param user: Filter by user
        :param limit: Maximum number of jobs to return
        :return: List of job dictionaries
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            query = "SELECT * FROM job_queue WHERE 1=1"
            params = []

            if state:
                query += " AND state = ?"
                params.append(state)

            if user:
                query += " AND user = ?"
                params.append(user)

            query += " ORDER BY priority DESC, submitted_at ASC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            jobs = []
            for row in rows:
                job_dict = dict(row)
                job_dict["metadata"] = json.loads(job_dict.get("metadata") or "{}")
                jobs.append(job_dict)

            return jobs
        except Exception as ex:
            log_exception(ex, "Error listing jobs")
            return []
        finally:
            conn.close()

    def get_pending_jobs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get pending jobs ordered by priority (for worker assignment).

        :param limit: Maximum number of jobs to return
        :return: List of pending job dictionaries
        """
        return self.list_jobs(state=JobState.PENDING.value, limit=limit)

    def update_job_state(
        self,
        job_id: str,
        state: JobState,
        return_code: Optional[int] = None,
        output: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        Update job state (internal method for worker processes).

        :param job_id: Job ID
        :param state: New job state
        :param return_code: Optional return code
        :param output: Optional output text
        :param error: Optional error text
        :return: True if updated successfully
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            update_fields = ["state = ?"]
            params = [state.value]

            if state == JobState.RUNNING:
                update_fields.append("started_at = ?")
                params.append(datetime.now().isoformat())
            elif state in [
                JobState.COMPLETED.value,
                JobState.FAILED.value,
                JobState.CANCELLED.value,
                JobState.TIMEOUT.value,
            ]:
                update_fields.append("completed_at = ?")
                params.append(datetime.now().isoformat())

            if return_code is not None:
                update_fields.append("return_code = ?")
                params.append(return_code)

            if output is not None:
                update_fields.append("output_file = ?")
                params.append(output)

            if error is not None:
                update_fields.append("error_file = ?")
                params.append(error)
            
            # Store stdout/stderr in metadata if provided
            if output is not None or error is not None:
                # Get existing metadata
                cursor.execute("SELECT metadata FROM job_queue WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                existing_metadata = {}
                if row and row["metadata"]:
                    try:
                        existing_metadata = json.loads(row["metadata"])
                    except:
                        existing_metadata = {}
                
                # Update with stdout/stderr
                if output is not None:
                    existing_metadata["stdout"] = output
                if error is not None:
                    existing_metadata["stderr"] = error
                
                update_fields.append("metadata = ?")
                params.append(json.dumps(existing_metadata))

            params.append(job_id)

            query = f"UPDATE job_queue SET {', '.join(update_fields)} WHERE job_id = ?"
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as ex:
            log_exception(ex, f"Error updating job state {job_id}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_running_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all running jobs.

        :return: List of running job dictionaries
        """
        return self.list_jobs(state=JobState.RUNNING.value)

    def get_completed_jobs(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get completed jobs.

        :param limit: Maximum number of jobs to return
        :return: List of completed job dictionaries
        """
        return self.list_jobs(state=JobState.COMPLETED.value, limit=limit)

    def get_failed_jobs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get failed jobs.

        :param limit: Maximum number of jobs to return
        :return: List of failed job dictionaries
        """
        return self.list_jobs(state=JobState.FAILED.value, limit=limit)

    def get_job_count_by_state(self) -> Dict[str, int]:
        """
        Get count of jobs by state.

        :return: Dictionary mapping state to count
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT state, COUNT(*) as count FROM job_queue GROUP BY state"
            )
            rows = cursor.fetchall()
            return {row["state"]: row["count"] for row in rows}
        except Exception as ex:
            log_exception(ex, "Error getting job counts")
            return {}
        finally:
            conn.close()

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from the queue (only if completed/failed/cancelled).

        :param job_id: Job ID
        :return: True if deleted successfully
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Check if job exists and is deletable
            cursor.execute(
                "SELECT state FROM job_queue WHERE job_id = ?", (job_id,)
            )
            row = cursor.fetchone()
            if not row:
                log.warning(f"Job {job_id} not found")
                return False

            state = row["state"]
            if state == JobState.RUNNING.value:
                log.warning(f"Cannot delete running job {job_id}")
                return False

            cursor.execute("DELETE FROM job_queue WHERE job_id = ?", (job_id,))
            conn.commit()
            log.info(f"Deleted job {job_id}")
            return True
        except Exception as ex:
            log_exception(ex, f"Error deleting job {job_id}")
            conn.rollback()
            return False
        finally:
            conn.close()

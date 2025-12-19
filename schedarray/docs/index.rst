SchedArray Documentation
==========================

Cross-platform job scheduler using SQLite, providing SLURM/SGE-like functionality on Windows, macOS, and Linux.

Overview
--------

SchedArray is a lightweight, cross-platform job scheduler that uses SQLite for persistence and job queue management. It provides similar functionality to SLURM and Sun Grid Engine (SGE) but works on all platforms without requiring cluster infrastructure.

Features
--------

* **Job Submission**: Submit jobs with priority, resource limits, and metadata
* **Job Status**: Check job status (pending, running, completed, failed, etc.)
* **Job Cancellation**: Cancel running or pending jobs
* **Priority Scheduling**: Jobs are executed in priority order
* **Worker Pool**: Configurable worker pool for parallel job execution
* **Timeout Support**: Jobs can have timeout limits
* **Persistence**: All job state persisted in SQLite database
* **Cross-Platform**: Works on Windows, macOS, and Linux
* **CLI Interface**: Command-line interface similar to SLURM commands
* **Task Decorator**: Python decorator for transparent job routing

Quick Start
-----------

Basic Usage:

.. code-block:: python

   from schedarray import SqliteJobScheduler, WorkerPoolManager

   # Create scheduler and worker pool
   scheduler = SqliteJobScheduler()
   worker_pool = WorkerPoolManager(scheduler, max_workers=4)

   # Submit a job
   job_id = scheduler.submit_job(
       command="python process_crystal.py 10000001",
       working_dir="/data/10000001",
       job_name="process_10000001",
       cpus=2,
       memory="4G",
       priority=5
   )

   # Start workers (they will automatically process pending jobs)
   worker_pool.start_workers()

   # Wait for completion
   import time
   while scheduler.get_job_status(job_id)["state"] == "pending":
       time.sleep(1)

   # Check result
   status = scheduler.get_job_status(job_id)
   print(f"Job completed with return code: {status['return_code']}")

   # Stop workers
   worker_pool.stop_workers()

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   cli_usage
   cli_examples
   task_decorator
   slurm_comparison
   slurmify_integration

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics

   decorator_naming
   decorator_power
   decorator_usage
   phase3

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


# SchedArray

Cross-platform job scheduler using SQLite, providing SLURM/SGE-like functionality on Windows, macOS, and Linux.

## Overview

SchedArray is a lightweight, cross-platform job scheduler that uses SQLite for persistence and job queue management. It provides similar functionality to SLURM and Sun Grid Engine (SGE) but works on all platforms without requiring cluster infrastructure.

## Features

- **Job Submission**: Submit jobs with priority, resource limits, and metadata
- **Job Status**: Check job status (pending, running, completed, failed, etc.)
- **Job Cancellation**: Cancel running or pending jobs
- **Priority Scheduling**: Jobs are executed in priority order
- **Worker Pool**: Configurable worker pool for parallel job execution
- **Timeout Support**: Jobs can have timeout limits
- **Persistence**: All job state persisted in SQLite database
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Quick Start

### Basic Usage

```python
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
```

### Integration with JobTracker

```python
from schedarray.integration.job_tracker import SchedArrayJobTrackerIntegration
from mxpandda.services.job.tracker.job import ExecutionBackend, JobTracker

# Create integration
integration = SchedArrayJobTrackerIntegration()

# Submit job to scheduler
scheduler_job_id = integration.submit_job_to_scheduler(
    command="python process.py",
    job_name="process_job",
    priority=5
)

# Register with JobTracker
tracker = JobTracker()
tracked_job_id = tracker.register_job(
    name="process_job",
    backend=ExecutionBackend.SCHEDARRAY,
    backend_job_id=scheduler_job_id,
    command="python process.py"
)

# Poll status via JobTracker
status = tracker.poll_job_status(tracked_job_id)
```

## Architecture

```
schedarray/
├── core/
│   ├── scheduler.py      # SqliteJobScheduler - core scheduling logic
│   ├── worker_pool.py    # WorkerPoolManager - worker pool management
│   └── service.py        # SchedulerService - standalone service wrapper
├── integration/
│   ├── job_tracker.py    # Integration with JobTracker
│   └── multiprocessing.py # Integration with multiprocessing utils
└── __init__.py
```

## Components

### SqliteJobScheduler

Core scheduler that manages the job queue in SQLite:
- `submit_job()` - Submit a new job
- `get_job_status()` - Get job status
- `cancel_job()` - Cancel a job
- `list_jobs()` - List jobs with filters
- `update_job_state()` - Update job state (internal)

### WorkerPoolManager

Manages worker processes that execute jobs:
- `start_workers()` - Start the worker pool
- `stop_workers()` - Stop the worker pool
- `get_worker_status()` - Get worker status

### SchedulerService

Standalone service wrapper:
- `start()` - Start the service
- `stop()` - Stop the service
- `status()` - Get service status

## Database Schema

The scheduler uses SQLite with the following tables:

- **job_queue**: Main job queue with all job metadata
- **worker_nodes**: For future distributed execution
- **resource_usage**: For resource tracking

## Phase 3 Integration

Phase 3 integrates SchedArray with existing systems:

1. **JobTracker Integration**: Added `SCHEDARRAY` backend to `ExecutionBackend` enum
2. **Multiprocessing Integration**: Option to use scheduler for large batches

## License

Part of the mxflask project.


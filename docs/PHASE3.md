# Phase 3: Integration with Existing Systems

## Overview

Phase 3 integrates SchedArray with the existing mxpandda systems:
- JobTracker integration
- Multiprocessing utilities integration

## Implementation

### 1. JobTracker Integration

**Added SCHEDARRAY Backend**

The `ExecutionBackend` enum in `mxpandda/services/job/tracker/job.py` now includes:
```python
SCHEDARRAY = "schedarray"  # SQLite-based scheduler
```

**Added Polling Method**

Added `_poll_schedarray_status()` method to `JobTracker` class that:
- Polls the scheduler for job status
- Maps scheduler states to JobTracker states
- Handles errors gracefully

**Integration Module**

Created `schedarray/integration/job_tracker.py` with:
- `SchedArrayJobTrackerIntegration` class
- `submit_job_to_scheduler()` - Submit jobs to scheduler
- `poll_scheduler_status()` - Poll scheduler job status
- `_map_scheduler_state_to_tracked_state()` - Map states

### 2. Multiprocessing Integration

Created `schedarray/integration/multiprocessing.py` with:
- `SchedArrayMultiprocessingIntegration` class
- `process_jobs_via_scheduler()` - Process jobs via scheduler instead of ProcessPoolExecutor

**Note**: This is a foundation for future integration. Full implementation would require:
- Proper function serialization
- Worker scripts for deserialization
- Result collection mechanisms

## Usage

### JobTracker Integration

```python
from schedarray.integration.job_tracker import SchedArrayJobTrackerIntegration
from mxpandda.services.job.tracker.job import ExecutionBackend, JobTracker

# Create integration (uses default scheduler)
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

### Using Custom Scheduler Instance

If you need to use a specific scheduler instance (e.g., with custom database path):

```python
from schedarray import SqliteJobScheduler
from schedarray.integration.job_tracker import SchedArrayJobTrackerIntegration

# Create scheduler with custom database
scheduler = SqliteJobScheduler(db_path="/path/to/custom.db")

# Create integration with custom scheduler
integration = SchedArrayJobTrackerIntegration(scheduler=scheduler)

# Use integration as above
```

## Status Mapping

SchedArray states map to JobTracker states as follows:

| SchedArray State | JobTracker State |
|-----------------|------------------|
| pending         | pending          |
| running         | running          |
| completed       | completed        |
| failed          | failed           |
| cancelled       | cancelled        |
| timeout         | timeout          |

## Testing

Phase 3 has been tested with:
- ✅ Job submission via integration
- ✅ Status polling via integration
- ✅ JobTracker registration
- ✅ Status mapping

## Known Limitations

1. **Scheduler Instance**: The integration uses a global scheduler instance by default. If you need to use a custom scheduler instance, pass it to the integration constructor.

2. **Multiprocessing Integration**: The multiprocessing integration is a foundation. Full implementation requires proper serialization mechanisms.

## Next Steps

Future enhancements could include:
- Full multiprocessing integration with proper serialization
- Integration with FillHKL and Dimple workflows
- Distributed worker support
- Resource usage tracking


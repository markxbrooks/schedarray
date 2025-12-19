# Integrating SchedArray with slurmify_run

## Feasibility Assessment

**Yes, it is feasible** to route all jobs run by `slurmify_run` through SchedArray. This document outlines the approach and considerations.

## Current State

`slurmify_run` is a central function that:
- Executes commands synchronously (waits for completion)
- Returns `subprocess.CompletedProcess` objects
- Handles SLURM submission when `slurmify=True` and SLURM is available
- Handles WSL wrapping on Windows
- Handles CCP4 environment setup
- Supports dry-run mode
- Used extensively in FillHKL workflows (CAD, MTZUtils, Buster, Uniqueify)

## Integration Approach

### Option 1: Drop-in Replacement (Recommended)

Create `schedarray_run()` that mirrors `slurmify_run()`'s interface:

**Advantages:**
- Minimal code changes required
- Can be adopted incrementally
- Preserves all existing functionality
- Backward compatible

**Implementation:**
```python
from schedarray.integration.slurmify import schedarray_run

# Replace:
result = slurmify_run(cmd, dry_run=dry_run, slurmify=slurmify)

# With:
result = schedarray_run(cmd, dry_run=dry_run, slurmify=slurmify)
```

### Option 2: Enhanced slurmify_run

Modify `slurmify_run()` to automatically use SchedArray when:
- SLURM is not available
- Running on Windows/Mac
- Explicitly requested via parameter

**Advantages:**
- No changes needed in calling code
- Automatic fallback behavior
- Single code path

**Implementation:**
```python
# In slurmify_run, add:
if not use_slurm and use_schedarray:
    return schedarray_run(...)
```

### Option 3: Configuration-Based Routing

Add configuration to control routing behavior:

**Advantages:**
- Flexible deployment
- Can be controlled per-environment
- Easy to enable/disable

**Implementation:**
```python
# In config or environment variable
USE_SCHEDARRAY = os.getenv("USE_SCHEDARRAY", "true").lower() == "true"

# In slurmify_run:
if USE_SCHEDARRAY and not use_slurm:
    return schedarray_run(...)
```

## Key Considerations

### 1. Synchronous vs Asynchronous Execution

**Challenge:** `slurmify_run` is synchronous, SchedArray is asynchronous.

**Solution:** `schedarray_run()` includes `wait_for_completion=True` by default, making it synchronous like `slurmify_run`.

### 2. Return Value Compatibility

**Challenge:** `slurmify_run` returns `subprocess.CompletedProcess`, SchedArray returns job IDs.

**Solution:** `schedarray_run()` returns a `CompletedProcess`-like object when `wait_for_completion=True`, maintaining compatibility.

### 3. SLURM Priority

**Challenge:** When should we use SLURM vs SchedArray?

**Solution:** 
- Use SLURM when available and `slurmify=True`
- Use SchedArray as fallback on Windows/Mac or when SLURM unavailable
- Can be controlled via configuration

### 4. Worker Pool Management

**Challenge:** Worker pool needs to be started before jobs can execute.

**Solution:** `schedarray_run()` automatically starts worker pool if not already running. Can also use a global singleton worker pool.

### 5. Error Handling

**Challenge:** Need to preserve error handling behavior.

**Solution:** `schedarray_run()` maintains the same error handling patterns, returning appropriate return codes and exceptions.

## Implementation Status

✅ **Core functionality implemented:**
- `schedarray_run()` function created
- Drop-in replacement interface
- Synchronous execution support
- SLURM fallback logic
- Platform handling (WSL, CCP4)

## Migration Strategy

### Phase 1: Testing (Current)
- Test `schedarray_run()` with sample commands
- Verify compatibility with existing code
- Test on Windows, Mac, Linux

### Phase 2: Selective Adoption
- Replace `slurmify_run` in specific workflows
- Start with FillHKL workflows
- Monitor for issues

### Phase 3: Full Integration
- Replace all `slurmify_run` calls
- Add configuration option
- Update documentation

## Usage Examples

### Basic Usage

```python
from schedarray.integration.slurmify import schedarray_run

# Synchronous execution (default)
result = schedarray_run(
    "python process.py",
    working_dir="/data/10000001",
    cpus=2,
    memory="4G"
)

if result.returncode == 0:
    print("Success!")
```

### Async Execution

```python
# Async execution (returns job_id immediately)
job_info = schedarray_run(
    "python long_process.py",
    wait_for_completion=False
)

job_id = job_info["job_id"]
scheduler = job_info["scheduler"]

# Check status later
status = scheduler.get_job_status(job_id)
```

### With SLURM Fallback

```python
# Automatically uses SLURM if available, SchedArray otherwise
result = schedarray_run(
    "python process.py",
    slurmify=True,  # Prefer SLURM if available
    cpus=4
)
```

## Benefits

1. **Cross-Platform:** Works on Windows, Mac, Linux
2. **Persistence:** Job state persisted in SQLite
3. **Priority Scheduling:** Jobs executed in priority order
4. **Resource Management:** CPU and memory limits
5. **Monitoring:** Job status tracking and history
6. **Scalability:** Can handle large job queues

## Limitations

1. **Worker Pool:** Requires worker pool to be running (auto-started)
2. **Database:** Requires SQLite database (auto-created)
3. **Synchronous Mode:** Polling adds small overhead vs direct execution
4. **SLURM Features:** Some SLURM-specific features not available (partitions, etc.)

## Testing

All core functionality has been tested:
- ✅ Basic command execution
- ✅ Dry-run mode
- ✅ Async execution
- ✅ Return value compatibility
- ✅ Error handling

## Next Steps

1. **Add configuration option** to enable/disable SchedArray globally
2. **Create migration script** to replace `slurmify_run` calls
3. **Add monitoring** for job queue status
4. **Document best practices** for when to use SchedArray vs SLURM

## Conclusion

Routing all `slurmify_run` jobs through SchedArray is **feasible and recommended** for:
- Cross-platform compatibility
- Better job management
- Persistent job tracking
- Priority scheduling

The implementation provides a drop-in replacement that maintains backward compatibility while adding new capabilities.


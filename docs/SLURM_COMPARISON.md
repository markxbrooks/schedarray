# SchedArray vs SLURM Comparison

## Job Management Commands

| Feature | SLURM | SchedArray |
|---------|-------|------------|
| Submit job | `sbatch script.sh` | `schedarray submit --script script.sh` |
| List jobs | `squeue` | `schedarray list` |
| Show job status | `squeue -j <job_id>` | `schedarray status <job_id>` |
| Cancel job | `scancel <job_id>` | `schedarray cancel <job_id>` |
| **Delete job** | ❌ Not available | ✅ `schedarray delete <job_id>` |
| **Cleanup jobs** | ❌ Not available | ✅ `schedarray cleanup` |

## Key Differences

### Job Deletion

**SLURM:**
- ❌ No `delete` command
- Completed jobs automatically disappear from `squeue` after retention period
- No way to manually delete job records
- Job history is managed by SLURM controller

**SchedArray:**
- ✅ `delete` command to remove completed/failed/cancelled jobs
- ✅ `cleanup` command for bulk deletion
- ✅ Manual control over job retention
- ✅ Can delete jobs older than N days

### Cleanup Functionality

**SLURM:**
- ❌ No cleanup command
- Jobs are automatically purged by SLURM controller based on configuration
- No user control over retention

**SchedArray:**
- ✅ `cleanup` command with flexible options:
  - `--completed`: Delete completed jobs
  - `--failed`: Delete failed jobs
  - `--cancelled`: Delete cancelled jobs
  - `--timeout`: Delete timeout jobs
  - `--older-than-days N`: Only delete jobs older than N days
  - `--json`: JSON output for automation

## SchedArray Cleanup Examples

### Delete All Completed Jobs

```bash
python -m schedarray cleanup --completed
```

### Delete All Failed and Cancelled Jobs

```bash
python -m schedarray cleanup --failed --cancelled
```

### Delete Jobs Older Than 7 Days

```bash
python -m schedarray cleanup --completed --older-than-days 7
```

### Cleanup Everything (Completed, Failed, Cancelled)

```bash
python -m schedarray cleanup --completed --failed --cancelled
```

### JSON Output for Automation

```bash
python -m schedarray cleanup --completed --json
```

## Why SchedArray Has Delete/Cleanup

1. **SQLite Backend**: Jobs are stored in a database, allowing manual deletion
2. **User Control**: Users can manage their own job history
3. **Disk Space**: Can free up database space by removing old jobs
4. **Privacy**: Can delete sensitive job records
5. **Automation**: Can be scripted for regular cleanup

## SLURM's Approach

SLURM doesn't provide delete/cleanup because:
- Jobs are managed by the controller daemon
- Job history is stored in controller's internal database
- Retention is configured system-wide by administrators
- Users don't have direct database access

## Best Practices

### Regular Cleanup

Set up a cron job to clean up old jobs:

```bash
# Clean up jobs older than 30 days, run daily
0 2 * * * python -m schedarray cleanup --completed --failed --older-than-days 30
```

### Selective Cleanup

```bash
# Keep recent failures for debugging, delete old completed jobs
python -m schedarray cleanup --completed --older-than-days 7

# Delete very old failures
python -m schedarray cleanup --failed --older-than-days 90
```

### Project-Specific Cleanup

```bash
# Use custom database for project
python -m schedarray --db-path /project/scheduler.db cleanup --completed
```

## Summary

SchedArray provides **more control** over job lifecycle management than SLURM:
- ✅ Manual deletion of individual jobs
- ✅ Bulk cleanup with flexible filters
- ✅ Age-based cleanup
- ✅ User-controlled retention
- ✅ Automation-friendly JSON output

This makes SchedArray more suitable for:
- Development environments
- Personal workstations
- Projects with specific retention needs
- Environments where users need direct control


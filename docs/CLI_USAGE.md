# SchedArray CLI Usage

## Overview

SchedArray provides a command-line interface similar to SLURM commands, making it easy to manage jobs from the terminal.

## Installation

The CLI is available via:
```bash
python -m schedarray <command>
```

Or create an alias:
```bash
alias schedarray='python -m schedarray'
```

## Commands

### Submit Job (`submit`)

Submit a job to the scheduler (like `sbatch`):

```bash
# Submit a command
python -m schedarray submit --command "python process.py" --job-name "process_job"

# Submit a script file
python -m schedarray submit --script script.sh --job-name "my_job"

# With resource limits
python -m schedarray submit \
    --command "python heavy_computation.py" \
    --job-name "heavy_job" \
    --cpus 4 \
    --memory "8G" \
    --timeout 3600 \
    --priority 10 \
    --output "output.log" \
    --error "error.log"
```

**Options:**
- `--command`, `-c`: Command to execute
- `--script`, `-s`: Script file to execute
- `--job-name`, `-J`: Job name
- `--working-dir`, `-d`: Working directory
- `--cpus`, `-n`: Number of CPUs (default: 1)
- `--memory`, `-m`: Memory limit (e.g., "4G", "512M")
- `--timeout`, `-t`: Timeout in seconds
- `--priority`, `-p`: Job priority (default: 0)
- `--output`, `-o`: Output file path
- `--error`, `-e`: Error file path

### Show Status (`status`)

Check job status (like `squeue`):

```bash
# Show status
python -m schedarray status <job_id>

# JSON output
python -m schedarray status <job_id> --json
```

### List Jobs (`list`)

List jobs (like `squeue`):

```bash
# List all jobs
python -m schedarray list

# Filter by state
python -m schedarray list --state pending
python -m schedarray list --state running
python -m schedarray list --state completed

# Filter by user
python -m schedarray list --user brooks

# Limit results
python -m schedarray list --limit 10

# JSON output
python -m schedarray list --json
```

### Cancel Job (`cancel`)

Cancel a job (like `scancel`):

```bash
python -m schedarray cancel <job_id>
```

### Delete Job (`delete`)

Delete a completed/failed job:

```bash
python -m schedarray delete <job_id>
```

### Show Counts (`counts`)

Show job counts by state:

```bash
# Human-readable
python -m schedarray counts

# JSON output
python -m schedarray counts --json
```

### Service Management (`service`)

Manage the scheduler service:

```bash
# Start service
python -m schedarray service start

# Show service status
python -m schedarray service status

# Stop service
python -m schedarray service stop

# With options
python -m schedarray service start --max-workers 8 --poll-interval 0.5
```

## Examples

### Basic Workflow

```bash
# Submit a job
JOB_ID=$(python -m schedarray submit --command "python process.py" --job-name "process")

# Check status
python -m schedarray status $JOB_ID

# List all jobs
python -m schedarray list

# Cancel if needed
python -m schedarray cancel $JOB_ID
```

### Batch Submission

```bash
# Submit multiple jobs
for i in {1..10}; do
    python -m schedarray submit \
        --command "python process.py $i" \
        --job-name "job_$i" \
        --priority $i
done

# Check counts
python -m schedarray counts

# List pending jobs
python -m schedarray list --state pending
```

### Service Management

```bash
# Start service in background
nohup python -m schedarray service start > schedarray.log 2>&1 &

# Check service status
python -m schedarray service status

# Stop service
python -m schedarray service stop
```

## JSON Output

All commands support `--json` flag for machine-readable output:

```bash
# Get job status as JSON
python -m schedarray status <job_id> --json

# List jobs as JSON
python -m schedarray list --json

# Parse with jq
python -m schedarray list --json | jq '.[] | select(.state == "pending")'
```

## Database Path

Specify a custom database path:

```bash
python -m schedarray --db-path /path/to/scheduler.db submit --command "echo hello"
```

## Integration with Scripts

```bash
#!/bin/bash
# Submit job and wait for completion

JOB_ID=$(python -m schedarray submit --command "python long_process.py" --job-name "long_process")

# Poll until complete
while true; do
    STATUS=$(python -m schedarray status $JOB_ID --json | jq -r '.state')
    if [ "$STATUS" == "completed" ]; then
        echo "Job completed!"
        break
    elif [ "$STATUS" == "failed" ]; then
        echo "Job failed!"
        exit 1
    fi
    sleep 1
done
```

## Comparison with SLURM

| SLURM Command | SchedArray Command |
|---------------|-------------------|
| `sbatch script.sh` | `schedarray submit --script script.sh` |
| `squeue -u user` | `schedarray list --user user` |
| `squeue -t RUNNING` | `schedarray list --state running` |
| `scancel <job_id>` | `schedarray cancel <job_id>` |
| `scontrol show job <job_id>` | `schedarray status <job_id>` |

## Tips

1. **Use job names**: Always specify `--job-name` for easier identification
2. **Monitor counts**: Use `schedarray counts` to quickly see job distribution
3. **JSON for automation**: Use `--json` flag for scripting and automation
4. **Service management**: Start the service once, then submit jobs as needed
5. **Database location**: Use `--db-path` to use a specific database file


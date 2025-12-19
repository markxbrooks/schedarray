# SchedArray CLI Examples

## Quick Start

```bash
# Submit a job
python -m schedarray submit --command "python my_script.py" --job-name "my_job"

# Check status
python -m schedarray status <job_id>

# List all jobs
python -m schedarray list

# Show job counts
python -m schedarray counts
```

## Common Use Cases

### 1. Submit and Monitor a Job

```bash
# Submit job and capture job ID
JOB_ID=$(python -m schedarray submit --command "python process.py" --job-name "process" | grep "Submitted job" | awk '{print $3}')

# Check status
python -m schedarray status $JOB_ID

# Wait for completion (in a script)
while true; do
    STATE=$(python -m schedarray status $JOB_ID --json | python -c "import sys, json; print(json.load(sys.stdin)['state'])")
    if [ "$STATE" == "completed" ] || [ "$STATE" == "failed" ]; then
        break
    fi
    sleep 1
done
```

### 2. Submit Multiple Jobs

```bash
# Submit batch of jobs
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

### 3. Monitor Job Queue

```bash
# Watch job queue (refresh every 2 seconds)
watch -n 2 'python -m schedarray list'

# Or with counts
watch -n 2 'python -m schedarray counts'
```

### 4. Submit Script File

```bash
# Create a script
cat > my_script.sh << 'EOF'
#!/bin/bash
echo "Starting processing..."
python process.py
echo "Done!"
EOF

# Submit script
python -m schedarray submit --script my_script.sh --job-name "script_job"
```

### 5. Resource-Limited Jobs

```bash
# Submit with resource limits
python -m schedarray submit \
    --command "python heavy_computation.py" \
    --job-name "heavy_job" \
    --cpus 8 \
    --memory "16G" \
    --timeout 7200 \
    --priority 10 \
    --output "heavy_job.out" \
    --error "heavy_job.err"
```

### 6. Cancel Jobs

```bash
# Cancel a specific job
python -m schedarray cancel <job_id>

# Cancel all pending jobs (bash)
python -m schedarray list --state pending --json | \
    python -c "import sys, json; [print(j['job_id']) for j in json.load(sys.stdin)]" | \
    xargs -I {} python -m schedarray cancel {}
```

### 7. Clean Up Completed Jobs

```bash
# Delete all completed jobs
python -m schedarray list --state completed --json | \
    python -c "import sys, json; [print(j['job_id']) for j in json.load(sys.stdin)]" | \
    xargs -I {} python -m schedarray delete {}
```

### 8. Service Management

```bash
# Start service in background
nohup python -m schedarray service start > schedarray_service.log 2>&1 &

# Check service status
python -m schedarray service status

# Stop service
python -m schedarray service stop
```

### 9. JSON Output for Automation

```bash
# Get job status as JSON
python -m schedarray status <job_id> --json

# List jobs as JSON and filter
python -m schedarray list --json | \
    python -c "import sys, json; [print(j['job_id']) for j in json.load(sys.stdin) if j['state'] == 'pending']"

# Get counts as JSON
python -m schedarray counts --json
```

### 10. Custom Database

```bash
# Use a specific database file
python -m schedarray --db-path /path/to/custom.db submit --command "echo hello"

# All subsequent commands use the same database
python -m schedarray --db-path /path/to/custom.db list
```

## Shell Aliases

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# SchedArray aliases
alias sa='python -m schedarray'
alias sa-submit='python -m schedarray submit'
alias sa-status='python -m schedarray status'
alias sa-list='python -m schedarray list'
alias sa-cancel='python -m schedarray cancel'
alias sa-counts='python -m schedarray counts'
```

Then use:
```bash
sa submit --command "echo hello"
sa list
sa counts
```

## Python Integration

```python
import subprocess
import json

# Submit job
result = subprocess.run(
    ['python', '-m', 'schedarray', 'submit', '--command', 'python script.py'],
    capture_output=True, text=True
)
job_id = result.stdout.strip().split()[-1]

# Check status
result = subprocess.run(
    ['python', '-m', 'schedarray', 'status', job_id, '--json'],
    capture_output=True, text=True
)
status = json.loads(result.stdout)
print(f"Job state: {status['state']}")
```

## Tips

1. **Always use job names**: Makes it easier to identify jobs
2. **Use JSON for scripts**: `--json` flag makes automation easier
3. **Monitor with watch**: Use `watch` command to monitor queue
4. **Service management**: Start service once, submit many jobs
5. **Database location**: Use `--db-path` for project-specific databases


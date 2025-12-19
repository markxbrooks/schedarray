#!/usr/bin/env python3
"""
SchedArray Command-Line Interface.

Provides CLI commands similar to SLURM:
- schedarray submit: Submit a job (like sbatch)
- schedarray status: Check job status (like squeue)
- schedarray cancel: Cancel a job (like scancel)
- schedarray list: List jobs (like squeue)
- schedarray service: Manage scheduler service
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from decologr.logger import Logger as log

from schedarray.core.scheduler import JobState, SqliteJobScheduler
from schedarray.core.service import SchedulerService
from schedarray.core.worker_pool import WorkerPoolManager

def submit_job(args):
    """Submit a job to the scheduler."""
    # Suppress logging for JSON output
    if args.json:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
    
    scheduler = SqliteJobScheduler(db_path=args.db_path)

    # Read command from file or use command line argument
    if args.script:
        with open(args.script, "r") as f:
            command = f.read()
    elif args.command:
        command = args.command
    else:
        print("Error: Either --script or --command must be provided", file=sys.stderr)
        sys.exit(1)

    job_id = scheduler.submit_job(
        command=command,
        working_dir=args.working_dir,
        job_name=args.job_name,
        cpus=args.cpus,
        memory=args.memory,
        timeout=args.timeout,
        priority=args.priority,
        output_file=args.output,
        error_file=args.error,
    )

    if args.json:
        print(json.dumps({"job_id": job_id, "job_name": args.job_name or job_id}, indent=2))
    else:
        print(f"Submitted job {job_id}")
        if args.job_name:
            print(f"Job name: {args.job_name}")
    return job_id

def show_status(args):
    """Show job status."""
    # Suppress logging for JSON output
    if args.json:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
    
    scheduler = SqliteJobScheduler(db_path=args.db_path)
    status = scheduler.get_job_status(args.job_id)

    if not status:
        print(f"Job {args.job_id} not found", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(dict(status), indent=2, default=str))
    else:
        print(f"Job ID: {status['job_id']}")
        print(f"Name: {status['job_name']}")
        print(f"State: {status['state']}")
        print(f"Submitted: {status['submitted_at']}")
        if status.get("started_at"):
            print(f"Started: {status['started_at']}")
        if status.get("completed_at"):
            print(f"Completed: {status['completed_at']}")
        if status.get("return_code") is not None:
            print(f"Return code: {status['return_code']}")
        if status.get("working_dir"):
            print(f"Working directory: {status['working_dir']}")
        if status.get("command"):
            print(f"Command: {status['command'][:100]}..." if len(status['command']) > 100 else f"Command: {status['command']}")

def cancel_job(args):
    """Cancel a job."""
    scheduler = SqliteJobScheduler(db_path=args.db_path)
    success = scheduler.cancel_job(args.job_id)

    if success:
        print(f"Cancelled job {args.job_id}")
    else:
        print(f"Failed to cancel job {args.job_id}", file=sys.stderr)
        sys.exit(1)

def list_jobs(args):
    """List jobs."""
    # Suppress logging for JSON output
    if args.json:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
    
    scheduler = SqliteJobScheduler(db_path=args.db_path)

    jobs = scheduler.list_jobs(
        state=args.state,
        user=args.user,
        limit=args.limit,
    )

    if args.json:
        print(json.dumps([dict(job) for job in jobs], indent=2, default=str))
    else:
        if not jobs:
            print("No jobs found")
            return

        # Print header
        print(f"{'Job ID':<40} {'Name':<20} {'State':<12} {'Priority':<8} {'Submitted':<20}")
        print("-" * 100)

        # Print jobs
        for job in jobs:
            job_id = job["job_id"][:38] + ".." if len(job["job_id"]) > 40 else job["job_id"]
            name = job["job_name"][:18] + ".." if len(job["job_name"]) > 20 else job["job_name"]
            state = job["state"]
            priority = job.get("priority", 0)
            submitted = job["submitted_at"][:18] if job.get("submitted_at") else "N/A"

            print(f"{job_id:<40} {name:<20} {state:<12} {priority:<8} {submitted:<20}")

def show_counts(args):
    """Show job counts by state."""
    # Suppress logging for JSON output
    if args.json:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
    
    scheduler = SqliteJobScheduler(db_path=args.db_path)
    counts = scheduler.get_job_count_by_state()

    if args.json:
        print(json.dumps(counts, indent=2))
    else:
        print("Job counts by state:")
        for state, count in sorted(counts.items()):
            print(f"  {state}: {count}")

def delete_job(args):
    """Delete a job."""
    scheduler = SqliteJobScheduler(db_path=args.db_path)
    success = scheduler.delete_job(args.job_id)

    if success:
        if args.json:
            print(json.dumps({"deleted": True, "job_id": args.job_id}, indent=2))
        else:
            print(f"Deleted job {args.job_id}")
    else:
        if args.json:
            print(json.dumps({"deleted": False, "job_id": args.job_id, "error": "Job not found or cannot be deleted"}, indent=2))
            sys.exit(1)
        else:
            print(f"Failed to delete job {args.job_id}", file=sys.stderr)
            sys.exit(1)

def cleanup_jobs(args):
    """Clean up old jobs."""
    # Suppress logging for JSON output
    if args.json:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
    
    scheduler = SqliteJobScheduler(db_path=args.db_path)
    
    # Get jobs to delete
    states_to_delete = []
    if args.completed:
        states_to_delete.append(JobState.COMPLETED.value)
    if args.failed:
        states_to_delete.append(JobState.FAILED.value)
    if args.cancelled:
        states_to_delete.append(JobState.CANCELLED.value)
    if args.timeout:
        states_to_delete.append(JobState.TIMEOUT.value)
    
    if not states_to_delete:
        states_to_delete = [JobState.COMPLETED.value, JobState.FAILED.value, JobState.CANCELLED.value]
    
    deleted_count = 0
    failed_count = 0
    
    for state in states_to_delete:
        jobs = scheduler.list_jobs(state=state, limit=None)
        for job in jobs:
            # Check age if specified
            if args.older_than_days:
                from datetime import datetime, timedelta
                completed_at = job.get("completed_at")
                if completed_at:
                    try:
                        completed_date = datetime.fromisoformat(completed_at)
                        cutoff_date = datetime.now() - timedelta(days=args.older_than_days)
                        if completed_date > cutoff_date:
                            continue  # Too recent, skip
                    except Exception:
                        pass  # If parsing fails, include it
            
            success = scheduler.delete_job(job["job_id"])
            if success:
                deleted_count += 1
            else:
                failed_count += 1
    
    if args.json:
        print(json.dumps({
            "deleted": deleted_count,
            "failed": failed_count,
            "states": states_to_delete
        }, indent=2))
    else:
        print(f"Deleted {deleted_count} job(s)")
        if failed_count > 0:
            print(f"Failed to delete {failed_count} job(s)", file=sys.stderr)
    
    return deleted_count

def service_start(args):
    """Start the scheduler service."""
    service = SchedulerService(
        db_path=args.db_path,
        max_workers=args.max_workers,
        poll_interval=args.poll_interval,
    )
    service.start()

def service_status(args):
    """Show service status."""
    # Suppress logging for JSON output
    if args.json:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
    
    service = SchedulerService(
        db_path=args.db_path,
        max_workers=args.max_workers,
        poll_interval=args.poll_interval,
    )
    status = service.status()

    if args.json:
        print(json.dumps(status, indent=2, default=str))
    else:
        print(f"Service running: {status['running']}")
        print(f"Workers: {status['workers']['total_workers']}")
        print(f"Jobs by state:")
        for state, count in sorted(status['jobs'].items()):
            print(f"  {state}: {count}")

def service_stop(args):
    """Stop the scheduler service."""
    service = SchedulerService(
        db_path=args.db_path,
        max_workers=args.max_workers,
        poll_interval=args.poll_interval,
    )
    service.stop()

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SchedArray - Cross-platform job scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to SQLite database (default: auto-detect)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # submit command
    submit_parser = subparsers.add_parser("submit", help="Submit a job (like sbatch)")
    submit_parser.add_argument("--script", "-s", type=Path, help="Script file to execute")
    submit_parser.add_argument("--command", "-c", help="Command to execute")
    submit_parser.add_argument("--job-name", "-J", help="Job name")
    submit_parser.add_argument("--working-dir", "-d", help="Working directory")
    submit_parser.add_argument("--cpus", "-n", type=int, default=1, help="Number of CPUs")
    submit_parser.add_argument("--memory", "-m", help="Memory limit (e.g., 4G)")
    submit_parser.add_argument("--timeout", "-t", type=int, help="Timeout in seconds")
    submit_parser.add_argument("--priority", "-p", type=int, default=0, help="Job priority")
    submit_parser.add_argument("--output", "-o", help="Output file")
    submit_parser.add_argument("--error", "-e", help="Error file")
    submit_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    submit_parser.set_defaults(func=submit_job)

    # status command
    status_parser = subparsers.add_parser("status", help="Show job status (like squeue)")
    status_parser.add_argument("job_id", help="Job ID")
    status_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    status_parser.set_defaults(func=show_status)

    # cancel command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a job (like scancel)")
    cancel_parser.add_argument("job_id", help="Job ID")
    cancel_parser.set_defaults(func=cancel_job)

    # list command
    list_parser = subparsers.add_parser("list", help="List jobs (like squeue)")
    list_parser.add_argument("--state", "-s", help="Filter by state")
    list_parser.add_argument("--user", "-u", help="Filter by user")
    list_parser.add_argument("--limit", "-n", type=int, help="Limit number of jobs")
    list_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    list_parser.set_defaults(func=list_jobs)

    # counts command
    counts_parser = subparsers.add_parser("counts", help="Show job counts by state")
    counts_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    counts_parser.set_defaults(func=show_counts)

    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a job")
    delete_parser.add_argument("job_id", help="Job ID")
    delete_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    delete_parser.set_defaults(func=delete_job)

    # cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old/completed jobs")
    cleanup_parser.add_argument("--completed", action="store_true", help="Delete completed jobs")
    cleanup_parser.add_argument("--failed", action="store_true", help="Delete failed jobs")
    cleanup_parser.add_argument("--cancelled", action="store_true", help="Delete cancelled jobs")
    cleanup_parser.add_argument("--timeout", action="store_true", help="Delete timeout jobs")
    cleanup_parser.add_argument("--older-than-days", type=int, help="Only delete jobs older than N days")
    cleanup_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    cleanup_parser.set_defaults(func=cleanup_jobs)

    # service subcommands
    service_parser = subparsers.add_parser("service", help="Manage scheduler service")
    service_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    service_subparsers = service_parser.add_subparsers(dest="service_command")

    service_start_parser = service_subparsers.add_parser("start", help="Start service")
    service_start_parser.add_argument("--max-workers", type=int, help="Maximum workers")
    service_start_parser.add_argument("--poll-interval", type=float, default=1.0, help="Poll interval")
    service_start_parser.set_defaults(func=service_start)

    service_status_parser = service_subparsers.add_parser("status", help="Show service status")
    service_status_parser.add_argument("--max-workers", type=int, help="Maximum workers")
    service_status_parser.add_argument("--poll-interval", type=float, default=1.0, help="Poll interval")
    service_status_parser.set_defaults(func=service_status)

    service_stop_parser = service_subparsers.add_parser("stop", help="Stop service")
    service_stop_parser.add_argument("--max-workers", type=int, help="Maximum workers")
    service_stop_parser.add_argument("--poll-interval", type=float, default=1.0, help="Poll interval")
    service_stop_parser.set_defaults(func=service_stop)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as ex:
        print(f"Error: {ex}", file=sys.stderr)
        if args.json:
            print(json.dumps({"error": str(ex)}, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()


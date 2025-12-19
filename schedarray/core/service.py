#!/usr/bin/env python3
"""
Standalone scheduler service that can run as a daemon.

This service manages the SQLite job scheduler and worker pool,
providing a complete job scheduling solution.
"""

import signal
import sys
import time
from pathlib import Path
from typing import Optional

from decologr.logger import Logger as log

from schedarray.core.scheduler import SqliteJobScheduler
from schedarray.core.worker_pool import WorkerPoolManager

class SchedulerService:
    """
    Standalone scheduler service that can run as a daemon.

    Usage:
        # Start service
        python -m schedarray.core.service start

        # Stop service
        python -m schedarray.core.service stop

        # Status
        python -m schedarray.core.service status
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        max_workers: Optional[int] = None,
        poll_interval: float = 1.0,
    ):
        """
        Initialize the scheduler service.

        :param db_path: Path to SQLite database (default: auto-detect)
        :param max_workers: Maximum number of workers (default: CPU count)
        :param poll_interval: Polling interval in seconds
        """
        self.scheduler = SqliteJobScheduler(db_path=db_path)
        self.worker_pool = WorkerPoolManager(
            scheduler=self.scheduler,
            max_workers=max_workers,
            poll_interval=poll_interval,
        )
        self.running = False

    def start(self):
        """Start the scheduler service."""
        if self.running:
            log.warning("Scheduler service already running")
            return

        log.info("Starting scheduler service...")

        # Register signal handlers for graceful shutdown (only in main thread)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # Signals can only be registered in main thread
            log.debug("Signal handlers not registered (not in main thread)")

        # Start worker pool
        self.worker_pool.start_workers()
        self.running = True

        log.info("Scheduler service started")

        # Main service loop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            log.info("Received interrupt signal")
        finally:
            self.stop()

    def stop(self):
        """Stop the scheduler service."""
        if not self.running:
            return

        log.info("Stopping scheduler service...")
        self.running = False
        self.worker_pool.stop_workers()
        log.info("Scheduler service stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        log.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def status(self) -> dict:
        """
        Get service status.

        :return: Dictionary with service status information
        """
        worker_status = self.worker_pool.get_worker_status()
        job_counts = self.scheduler.get_job_count_by_state()

        return {
            "running": self.running,
            "workers": worker_status,
            "jobs": job_counts,
        }

def main():
    """Main entry point for the service."""
    import argparse

    parser = argparse.ArgumentParser(description="SQLite Job Scheduler Service")
    parser.add_argument(
        "command",
        choices=["start", "stop", "status"],
        help="Service command",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        help="Maximum number of workers",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds",
    )

    args = parser.parse_args()

    service = SchedulerService(
        db_path=args.db_path,
        max_workers=args.max_workers,
        poll_interval=args.poll_interval,
    )

    if args.command == "start":
        service.start()
    elif args.command == "stop":
        service.stop()
    elif args.command == "status":
        status = service.status()
        print("Scheduler Service Status:")
        print(f"  Running: {status['running']}")
        print(f"  Workers: {status['workers']['total_workers']}")
        print(f"  Jobs by state: {status['jobs']}")

if __name__ == "__main__":
    main()

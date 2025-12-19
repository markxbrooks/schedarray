#!/usr/bin/env python3
"""
@schedarray.task decorator for routing function calls through SchedArray.

This decorator can be applied directly to functions (like slurmify_run)
to route their execution through the SchedArray scheduler.
"""

import functools
import os
from typing import Callable, Optional

from decologr.logger import Logger as log

def task(
    enabled: Optional[bool] = None,
    check_slurm_first: bool = True,
    fallback_to_original: bool = True,
):
    """
    Decorator that routes function calls through SchedArray.

    This decorator can be applied directly to functions to route their
    execution through SchedArray. It's designed to work with slurmify_run
    and similar functions.

    :param enabled: If True, enable routing. If None, check environment variable.
    :param check_slurm_first: If True, check for SLURM availability first.
    :param fallback_to_original: If True, fall back to original function on error.

    Usage:
        @schedarray.task(enabled=True)
        def slurmify_run(command, **kwargs):
            # Original implementation
            ...

        # Now all calls to slurmify_run go through SchedArray
        result = slurmify_run("echo hello")
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if routing is enabled
            if enabled is None:
                # Check environment variable
                routing_enabled = (
                    os.getenv("USE_SCHEDARRAY", "true").lower() == "true"
                )
            else:
                routing_enabled = enabled

            if not routing_enabled:
                # Routing disabled, use original function
                return func(*args, **kwargs)

            # Check if SLURM should be checked first
            if check_slurm_first:
                slurmify = kwargs.get("slurmify", False)
                if slurmify:
                    # Check if SLURM is available
                    try:
                        import subprocess

                        result = subprocess.run(
                            ["sbatch", "--version"],
                            capture_output=True,
                            timeout=2,
                        )
                        if result.returncode == 0:
                            # SLURM available, use original function
                            log.debug(
                                "SLURM available, using original function"
                            )
                            return func(*args, **kwargs)
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        # SLURM not available, continue to SchedArray
                        pass

            # Route through SchedArray
            try:
                from schedarray.integration.slurmify import schedarray_run

                log.debug(
                    f"Routing {func.__name__} call through SchedArray"
                )
                return schedarray_run(*args, **kwargs)
            except Exception as ex:
                log.warning(
                    f"SchedArray routing failed: {ex}, falling back to original"
                )
                if fallback_to_original:
                    return func(*args, **kwargs)
                raise

        return wrapper

    return decorator


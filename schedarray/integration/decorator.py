#!/usr/bin/env python3
"""
Decorator to route slurmify_run calls through SchedArray.

This module provides a powerful decorator that can intercept calls to
slurmify_run and transparently route them through schedarray_run,
enabling SchedArray integration without modifying calling code.
"""

import functools
import os
from typing import Callable, Optional

from decologr.logger import Logger as log

from schedarray.integration.slurmify import schedarray_run

def route_to_schedarray(
    enabled: Optional[bool] = None,
    check_slurm_first: bool = True,
    fallback_to_original: bool = True,
):
    """
    Decorator that routes slurmify_run calls through SchedArray.

    This decorator intercepts calls to slurmify_run and routes them
    through schedarray_run instead, providing transparent SchedArray
    integration without modifying calling code.

    :param enabled: If True, enable routing. If None, check environment variable.
    :param check_slurm_first: If True, check for SLURM availability first.
    :param fallback_to_original: If True, fall back to original function on error.

    Usage:
        # Apply decorator to slurmify_run
        from mxlib.adapters.environment.slurm.slurmify import slurmify_run
        from schedarray.integration.decorator import route_to_schedarray

        slurmify_run = route_to_schedarray()(slurmify_run)

        # Or with configuration
        slurmify_run = route_to_schedarray(enabled=True, check_slurm_first=False)(slurmify_run)
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
                                "SLURM available, using original slurmify_run"
                            )
                            return func(*args, **kwargs)
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        # SLURM not available, continue to SchedArray
                        pass

            # Route through SchedArray
            try:
                log.debug("Routing slurmify_run call through SchedArray")
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

def patch_slurmify_run(
    enabled: Optional[bool] = None,
    check_slurm_first: bool = True,
    fallback_to_original: bool = True,
):
    """
    Patch slurmify_run to route through SchedArray.

    This function patches the slurmify_run function in-place to route
    calls through SchedArray. This is a convenience function that
    applies the decorator automatically.

    :param enabled: If True, enable routing. If None, check environment variable.
    :param check_slurm_first: If True, check for SLURM availability first.
    :param fallback_to_original: If True, fall back to original function on error.

    Usage:
        # At application startup
        from schedarray.integration.decorator import patch_slurmify_run

        # Enable SchedArray routing
        patch_slurmify_run(enabled=True)

        # Now all slurmify_run calls go through SchedArray
    """
    import mxlib.adapters.environment.slurm.slurmify as slurmify_module

    # Store original function
    if not hasattr(slurmify_module, "_original_slurmify_run"):
        slurmify_module._original_slurmify_run = slurmify_module.slurmify_run

    # Apply decorator
    slurmify_module.slurmify_run = route_to_schedarray(
        enabled=enabled,
        check_slurm_first=check_slurm_first,
        fallback_to_original=fallback_to_original,
    )(slurmify_module._original_slurmify_run)

    log.info("Patched slurmify_run to route through SchedArray")

def unpatch_slurmify_run():
    """
    Restore original slurmify_run function.

    Usage:
        from schedarray.integration.decorator import unpatch_slurmify_run

        # Restore original behavior
        unpatch_slurmify_run()
    """
    import mxlib.adapters.environment.slurm.slurmify as slurmify_module

    if hasattr(slurmify_module, "_original_slurmify_run"):
        slurmify_module.slurmify_run = slurmify_module._original_slurmify_run
        log.info("Restored original slurmify_run")
    else:
        log.warning("No original slurmify_run found to restore")


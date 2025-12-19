"""Integration modules for schedarray with existing systems."""

from schedarray.integration.decorator import (
    patch_slurmify_run,
    route_to_schedarray,
    unpatch_slurmify_run,
)
from schedarray.integration.job_tracker import SchedArrayJobTrackerIntegration
from schedarray.integration.multiprocessing import SchedArrayMultiprocessingIntegration
from schedarray.integration.slurmify import schedarray_run

__all__ = [
    "SchedArrayJobTrackerIntegration",
    "SchedArrayMultiprocessingIntegration",
    "route_to_schedarray",
    "patch_slurmify_run",
    "unpatch_slurmify_run",
    "schedarray_run",
]


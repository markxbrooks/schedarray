#!/usr/bin/env python3
"""
Example demonstrating the power of the SchedArray decorator.

This example shows how a single line of code can route ALL slurmify_run
calls through SchedArray, without modifying any calling code.
"""

# Example 1: Simple one-line integration
from schedarray.integration.decorator import patch_slurmify_run

# Enable SchedArray routing - that's it!
patch_slurmify_run(enabled=True)

# Now ALL slurmify_run calls throughout your application
# will automatically route through SchedArray!

# Example usage (no changes needed in existing code)
from mxlib.adapters.environment.slurm.slurmify import slurmify_run

# This call now goes through SchedArray automatically
result = slurmify_run("echo 'Hello from SchedArray!'")
print(f"Return code: {result.returncode}")

# Example 2: Environment variable control
import os

# Set environment variable
os.environ["USE_SCHEDARRAY"] = "true"

# Patch will check environment variable
patch_slurmify_run()  # enabled=None checks env var

# Example 3: Conditional routing
import platform

if platform.system() in ["Windows", "Darwin"]:
    # Use SchedArray on Windows/Mac
    patch_slurmify_run(enabled=True, check_slurm_first=False)
else:
    # Check SLURM first on Linux
    patch_slurmify_run(enabled=True, check_slurm_first=True)

# Example 4: Application startup pattern
def initialize_application():
    """Initialize application with SchedArray routing."""
    from schedarray.integration.decorator import patch_slurmify_run

    # Enable SchedArray routing
    patch_slurmify_run(
        enabled=True,
        check_slurm_first=True,  # Use SLURM if available
        fallback_to_original=True,  # Fall back on error
    )
    print("✅ SchedArray routing enabled - all slurmify_run calls will use SchedArray")

if __name__ == "__main__":
    # Initialize
    initialize_application()

    # Use slurmify_run as normal - it's now routed through SchedArray!
    result = slurmify_run("echo 'This goes through SchedArray!'")
    print(f"✅ Command executed with return code: {result.returncode}")


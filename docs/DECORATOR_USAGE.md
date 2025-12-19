# SchedArray Decorator Usage

## Overview

The `route_to_schedarray` decorator provides a powerful way to transparently route all `slurmify_run` calls through SchedArray without modifying calling code.

## Basic Usage

### Option 1: Manual Decorator Application

```python
from mxlib.adapters.environment.slurm.slurmify import slurmify_run
from schedarray.integration.decorator import route_to_schedarray

# Apply decorator
slurmify_run = route_to_schedarray(enabled=True)(slurmify_run)

# Now all calls go through SchedArray
result = slurmify_run("echo hello")
```

### Option 2: Patch Function (Recommended)

```python
from schedarray.integration.decorator import patch_slurmify_run

# At application startup
patch_slurmify_run(enabled=True)

# Now all slurmify_run calls automatically route through SchedArray
# No code changes needed in calling code!
```

### Option 3: Environment Variable

```bash
# Set environment variable
export USE_SCHEDARRAY=true

# In Python code
from schedarray.integration.decorator import patch_slurmify_run

# Will check USE_SCHEDARRAY environment variable
patch_slurmify_run()
```

## Configuration Options

### enabled

Control whether routing is enabled:

```python
# Always enabled
patch_slurmify_run(enabled=True)

# Always disabled
patch_slurmify_run(enabled=False)

# Check environment variable (default)
patch_slurmify_run(enabled=None)
```

### check_slurm_first

Check for SLURM availability before routing:

```python
# Check SLURM first, use if available (default)
patch_slurmify_run(check_slurm_first=True)

# Always use SchedArray, ignore SLURM
patch_slurmify_run(check_slurm_first=False)
```

### fallback_to_original

Fall back to original function on error:

```python
# Fall back on error (default)
patch_slurmify_run(fallback_to_original=True)

# Raise exception on error
patch_slurmify_run(fallback_to_original=False)
```

## Integration Examples

### Application Startup

```python
# In your application's __init__.py or startup code
import os
from schedarray.integration.decorator import patch_slurmify_run

# Enable SchedArray routing based on configuration
use_schedarray = os.getenv("USE_SCHEDARRAY", "true").lower() == "true"
patch_slurmify_run(enabled=use_schedarray, check_slurm_first=True)
```

### Conditional Routing

```python
from schedarray.integration.decorator import patch_slurmify_run, unpatch_slurmify_run
import platform

# Enable SchedArray on Windows/Mac, use SLURM on Linux
if platform.system() in ["Windows", "Darwin"]:
    patch_slurmify_run(enabled=True, check_slurm_first=False)
else:
    # Use SLURM on Linux
    patch_slurmify_run(enabled=False)
```

### Testing

```python
# In test setup
from schedarray.integration.decorator import patch_slurmify_run, unpatch_slurmify_run

def setUp(self):
    # Enable SchedArray for tests
    patch_slurmify_run(enabled=True)

def tearDown(self):
    # Restore original
    unpatch_slurmify_run()
```

## Benefits

1. **Zero Code Changes**: No need to modify existing code
2. **Transparent**: Works exactly like original `slurmify_run`
3. **Configurable**: Can be enabled/disabled at runtime
4. **Fallback**: Automatically falls back to original on error
5. **SLURM Compatible**: Checks for SLURM availability first

## How It Works

1. Decorator intercepts calls to `slurmify_run`
2. Checks if routing is enabled
3. If enabled, routes call through `schedarray_run`
4. If disabled or SLURM available, uses original function
5. On error, falls back to original function (if configured)

## Unpatching

To restore original behavior:

```python
from schedarray.integration.decorator import unpatch_slurmify_run

# Restore original slurmify_run
unpatch_slurmify_run()
```

## Best Practices

1. **Application Startup**: Patch at application startup, not in individual modules
2. **Configuration**: Use environment variables for easy deployment control
3. **Testing**: Always unpatch in test teardown to avoid side effects
4. **Monitoring**: Monitor logs to ensure routing is working as expected
5. **Gradual Migration**: Start with specific workflows, then expand

## Example: Full Integration

```python
# application_startup.py
import os
from schedarray.integration.decorator import patch_slurmify_run

def initialize_schedarray():
    """Initialize SchedArray routing at application startup."""
    use_schedarray = os.getenv("USE_SCHEDARRAY", "true").lower() == "true"
    check_slurm = os.getenv("SCHEDARRAY_CHECK_SLURM", "true").lower() == "true"
    
    if use_schedarray:
        patch_slurmify_run(
            enabled=True,
            check_slurm_first=check_slurm,
            fallback_to_original=True
        )
        print("SchedArray routing enabled")
    else:
        print("SchedArray routing disabled, using original slurmify_run")

# Call at startup
initialize_schedarray()
```

Now all `slurmify_run` calls throughout your application will automatically route through SchedArray!


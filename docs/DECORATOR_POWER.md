# The Power of the SchedArray Decorator

## One Line to Rule Them All

The `route_to_schedarray` decorator is incredibly powerful - with **just one line of code**, you can route **ALL** `slurmify_run` calls throughout your entire application through SchedArray, without modifying a single line of calling code!

## The Magic

```python
from schedarray.integration.decorator import patch_slurmify_run

# That's it! One line!
patch_slurmify_run(enabled=True)

# Now EVERY slurmify_run call in your entire codebase
# automatically routes through SchedArray!
```

## What This Means

### Before (Without Decorator)

You would need to modify **every single call site**:

```python
# In mxlib/workflows/fillhkl/cad.py
from schedarray.integration.slurmify import schedarray_run  # Change import
result = schedarray_run(cmd, dry_run=dry_run, slurmify=slurmify)  # Change function

# In mxlib/workflows/fillhkl/mtzutils.py
from schedarray.integration.slurmify import schedarray_run  # Change import
result = schedarray_run(cmd, dry_run=dry_run, slurmify=slurmify)  # Change function

# In mxlib/workflows/fillhkl/buster.py
from schedarray.integration.slurmify import schedarray_run  # Change import
result = schedarray_run(cmd, dry_run=dry_run, slurmify=slurmify)  # Change function

# ... and so on for EVERY file that uses slurmify_run
```

**That's potentially 20+ files to modify!**

### After (With Decorator)

**Just one line at application startup:**

```python
# In your application startup code (e.g., __init__.py or main.py)
from schedarray.integration.decorator import patch_slurmify_run

patch_slurmify_run(enabled=True)

# That's it! No other changes needed!
# All existing slurmify_run calls now use SchedArray automatically
```

**Zero changes to calling code!**

## Real-World Impact

### FillHKL Workflows

All these workflows automatically use SchedArray:

- `fillhkl_cad()` - CAD operations
- `fillhkl_mtzutils()` - MTZ utilities
- `fillhkl_buster()` - Buster refinement
- `fillhkl_uniqueify()` - Uniqueify operations
- `fillhkl_snafucate()` - SNAFUCATE pipeline

**No code changes needed in any of these functions!**

### Any Future Code

Any new code that uses `slurmify_run` automatically gets SchedArray:

```python
# New developer writes this code
from mxlib.adapters.environment.slurm.slurmify import slurmify_run

result = slurmify_run("python new_script.py")

# Automatically uses SchedArray - no knowledge needed!
```

## Configuration Options

### Environment Variable Control

```python
# Set environment variable
export USE_SCHEDARRAY=true

# In code - checks environment variable automatically
patch_slurmify_run()  # enabled=None checks env var
```

### Conditional Routing

```python
import platform

if platform.system() in ["Windows", "Darwin"]:
    # Always use SchedArray on Windows/Mac
    patch_slurmify_run(enabled=True, check_slurm_first=False)
else:
    # Check SLURM first on Linux
    patch_slurmify_run(enabled=True, check_slurm_first=True)
```

### Runtime Control

```python
from schedarray.integration.decorator import patch_slurmify_run, unpatch_slurmify_run

# Enable SchedArray
patch_slurmify_run(enabled=True)

# ... do work ...

# Disable SchedArray (restore original)
unpatch_slurmify_run()

# ... do work with original slurmify_run ...

# Re-enable SchedArray
patch_slurmify_run(enabled=True)
```

## Benefits

1. **Zero Code Changes**: No modifications to existing code
2. **Transparent**: Works exactly like original `slurmify_run`
3. **Backward Compatible**: Can be disabled at any time
4. **Future Proof**: New code automatically benefits
5. **Configurable**: Can be controlled via environment variables
6. **Safe**: Falls back to original on error

## Use Cases

### Development

```python
# Enable SchedArray for better job tracking during development
patch_slurmify_run(enabled=True)
```

### Production

```python
# Use environment variable for easy deployment control
# export USE_SCHEDARRAY=true
patch_slurmify_run()  # Checks environment variable
```

### Testing

```python
# Enable SchedArray for tests
def setUp(self):
    patch_slurmify_run(enabled=True)

def tearDown(self):
    unpatch_slurmify_run()
```

### Cross-Platform Deployment

```python
# Automatically use SchedArray on Windows/Mac, SLURM on Linux
if platform.system() in ["Windows", "Darwin"]:
    patch_slurmify_run(enabled=True, check_slurm_first=False)
```

## The Bottom Line

**One line of code** gives you:
- ✅ Cross-platform job scheduling
- ✅ Persistent job tracking
- ✅ Priority scheduling
- ✅ Better resource management
- ✅ Job history and monitoring
- ✅ Zero code changes required

That's the power of a well-designed decorator! 🚀


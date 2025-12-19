# @schedarray.task Decorator

## Overview

The `@schedarray.task` decorator provides a clean, Pythonic way to route function calls through SchedArray by applying it directly to function definitions.

## Usage

### Basic Usage

Simply apply the decorator to `slurmify_run`:

```python
from schedarray import task
from mxlib.utils.timing import time_function

@task(enabled=None)  # Checks USE_SCHEDARRAY env var
@time_function
def slurmify_run(command, **kwargs):
    # Original implementation
    ...
```

### With Environment Variable

```bash
# Enable SchedArray routing
export USE_SCHEDARRAY=true
```

```python
@task()  # enabled=None checks env var automatically
def slurmify_run(command, **kwargs):
    ...
```

### Explicit Enable/Disable

```python
# Always enabled
@task(enabled=True)
def slurmify_run(command, **kwargs):
    ...

# Always disabled
@task(enabled=False)
def slurmify_run(command, **kwargs):
    ...
```

## How It Works

1. **Decorator Applied**: When `@task()` is applied to a function, it wraps the function
2. **Runtime Check**: On each call, the decorator checks if routing is enabled
3. **Route Decision**: 
   - If enabled → routes through `schedarray_run`
   - If disabled → uses original function
   - If SLURM available and `slurmify=True` → uses original function
4. **Fallback**: Falls back to original function on error (if configured)

## Configuration Options

### enabled

Control whether routing is enabled:

- `None` (default): Check `USE_SCHEDARRAY` environment variable
- `True`: Always enable routing
- `False`: Always disable routing

### check_slurm_first

Check for SLURM availability before routing:

- `True` (default): Check SLURM first, use if available
- `False`: Always use SchedArray, ignore SLURM

### fallback_to_original

Fall back to original function on error:

- `True` (default): Fall back on error
- `False`: Raise exception on error

## Example: slurmify_run Integration

```python
# In mxlib/adapters/environment/slurm/slurmify.py

# Lazy import to avoid circular dependency
def _get_schedarray_task():
    try:
        from schedarray import task
        return task
    except ImportError:
        return None

_schedarray_task = _get_schedarray_task()
if _schedarray_task:
    _task_decorator = _schedarray_task(enabled=None)  # Check env var
else:
    def _task_decorator(func):
        return func

@_task_decorator
@time_function
def slurmify_run(command, **kwargs):
    # Original implementation
    ...
```

## Benefits

1. **Clean Syntax**: Decorator pattern is Pythonic and explicit
2. **No Code Changes**: Existing calls work without modification
3. **Configurable**: Can be controlled via environment variable
4. **Safe**: Falls back to original on error
5. **SLURM Compatible**: Checks for SLURM availability first

## Comparison with patch_slurmify_run

| Feature | @schedarray.task | patch_slurmify_run |
|---------|------------------|-------------------|
| Syntax | Decorator on function | Function call at startup |
| Code Changes | One line in function definition | One line at startup |
| Explicit | Yes, visible in code | No, hidden at runtime |
| Import Time | Lazy import needed | Can import directly |
| Flexibility | Per-function control | Global control |

## Best Practices

1. **Use Lazy Import**: Import `task` inside a function to avoid circular dependencies
2. **Environment Variable**: Use `enabled=None` to check `USE_SCHEDARRAY` env var
3. **Fallback**: Always use `fallback_to_original=True` for safety
4. **SLURM Check**: Use `check_slurm_first=True` to respect SLURM availability

## Example: Multiple Functions

```python
from schedarray import task

@task(enabled=None)
def slurmify_run(command, **kwargs):
    ...

@task(enabled=None)
def run_local_or_slurm(command, **kwargs):
    ...

# Both functions now route through SchedArray when enabled
```

## Conclusion

The `@schedarray.task` decorator provides a clean, explicit way to route function calls through SchedArray. It's perfect for cases where you want the routing behavior to be visible in the code and controllable per-function.


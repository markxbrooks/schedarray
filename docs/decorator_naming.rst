Decorator Naming Convention Explanation
========================================

Why ``@_task_decorator`` has a leading underscore and no namespace
--------------------------------------------------------------------

Current Implementation
----------------------

.. code-block:: python

   # Lazy import to avoid circular dependency
   def _get_schedarray_task():
       try:
           from schedarray import task
           return task
       except ImportError:
           return None

   _schedarray_task = _get_schedarray_task()
   if _schedarray_task:
       _task_decorator = _schedarray_task(enabled=None)
   else:
       def _task_decorator(func):
           return func

   @_task_decorator
   @time_function
   def slurmify_run(...):
       ...

Why the Leading Underscore?
----------------------------

The leading underscore (``_``) is a Python convention indicating:

* **Private/Internal**: This is an implementation detail, not part of the public API
* **Module-level internal**: Should not be imported or used by other modules
* **Implementation detail**: Signals to other developers this is "behind the scenes"

Why No Namespace?
-----------------

The decorator is a **local variable**, not an imported name:

* We can't use ``@schedarray.task`` directly because of circular import issues
* We need to lazy-import to avoid the circular dependency
* The local variable holds the decorator instance after lazy import

Better Alternatives
-------------------

Option 1: Use ``@schedarray.task`` directly (if circular import resolved)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If we can resolve the circular import, we could use:

.. code-block:: python

   from schedarray import task

   @task(enabled=None)
   @time_function
   def slurmify_run(...):
       ...

**Problem**: This causes a circular import because:

* ``slurmify.py`` imports ``schedarray``
* ``schedarray`` imports ``mxlib`` (for logging, etc.)
* ``mxlib`` imports ``slurmify.py``

Option 2: Cleaner local variable name
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We could use a clearer name without the underscore:

.. code-block:: python

   # Lazy import
   def _get_schedarray_task():
       try:
           from schedarray import task
           return task
       except ImportError:
           return None

   # Use clearer name
   schedarray_task_decorator = _get_schedarray_task()
   if schedarray_task_decorator:
       task_decorator = schedarray_task_decorator(enabled=None)
   else:
       def task_decorator(func):
           return func

   @task_decorator
   @time_function
   def slurmify_run(...):
       ...

**Benefit**: More explicit, but still signals it's a local implementation detail

Option 3: Conditional decorator application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # At module level
   try:
       from schedarray import task as schedarray_task
       USE_SCHEDARRAY = True
   except ImportError:
       USE_SCHEDARRAY = False
       def schedarray_task(*args, **kwargs):
           def noop(func):
               return func
           return noop

   # Apply decorator conditionally
   if USE_SCHEDARRAY:
       @schedarray_task(enabled=None)
       @time_function
       def slurmify_run(...):
           ...
   else:
       @time_function
       def slurmify_run(...):
           ...

**Problem**: Duplicates function definition

Option 4: Use a helper function (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def apply_schedarray_task(func):
       """Apply schedarray.task decorator if available."""
       try:
           from schedarray import task
           return task(enabled=None)(func)
       except ImportError:
           return func

   @apply_schedarray_task
   @time_function
   def slurmify_run(...):
       ...

**Benefit**: 

* Clear intent
* No underscore needed (it's a helper function, not internal state)
* Single decorator application
* Easy to understand

Recommendation
--------------

Use **Option 4** - a helper function that clearly expresses intent:

.. code-block:: python

   def apply_schedarray_task(func):
       """Apply schedarray.task decorator if available, otherwise return function unchanged."""
       try:
           from schedarray import task
           return task(enabled=None)(func)
       except ImportError:
           return func

   @apply_schedarray_task
   @time_function
   def slurmify_run(...):
       ...

This is:

* ✅ Clear and explicit
* ✅ No confusing underscores
* ✅ Easy to understand
* ✅ Follows Python conventions
* ✅ Handles import errors gracefully


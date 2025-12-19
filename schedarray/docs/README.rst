SchedArray Documentation
=========================

This directory contains the Sphinx documentation for SchedArray.

Building the Documentation
--------------------------

Prerequisites
~~~~~~~~~~~~

Install required dependencies:

.. code-block:: bash

   pip install sphinx sphinx-rtd-theme myst-parser

Build HTML Documentation
~~~~~~~~~~~~~~~~~~~~~~~~

Using Make (Linux/macOS):

.. code-block:: bash

   make html

Using Sphinx directly:

.. code-block:: bash

   sphinx-build -b html . _build/html

Build PDF Documentation
~~~~~~~~~~~~~~~~~~~~~~~

Using Make:

.. code-block:: bash

   make latexpdf

Using Sphinx directly:

.. code-block:: bash

   sphinx-build -b latex . _build/latex
   cd _build/latex && make

Viewing the Documentation
-------------------------

After building, open ``_build/html/index.html`` in your web browser.

Documentation Structure
-----------------------

* ``index.rst`` - Main documentation index
* ``cli_usage.rst`` - CLI command reference
* ``cli_examples.rst`` - CLI usage examples
* ``task_decorator.rst`` - @schedarray.task decorator documentation
* ``slurm_comparison.rst`` - Comparison with SLURM
* ``slurmify_integration.rst`` - Integration with slurmify_run
* ``decorator_naming.rst`` - Decorator naming conventions
* ``decorator_power.rst`` - Decorator power and benefits
* ``decorator_usage.rst`` - Decorator usage guide
* ``phase3.rst`` - Phase 3 integration documentation

Configuration
-------------

The Sphinx configuration is in ``conf.py``. Key settings:

* **Project**: SchedArray
* **Theme**: sphinx_rtd_theme (Read the Docs theme)
* **Extensions**: autodoc, napoleon, myst_parser (for Markdown support)
* **Source**: RST files in this directory

Adding New Documentation
-------------------------

1. Create a new ``.rst`` file in this directory
2. Add it to the ``toctree`` in ``index.rst``
3. Rebuild the documentation

For Markdown files, you can also use ``.md`` extension - Sphinx will convert them using myst_parser.


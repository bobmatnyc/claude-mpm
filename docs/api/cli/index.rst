CLI API
=======

The CLI API provides command-line interface capabilities for Claude MPM, including command
implementations, argument parsing, and utility functions.

.. toctree::
   :maxdepth: 2

   commands
   parser
   utils

Overview
--------

The Claude MPM CLI is built with a modular architecture supporting:

* **Command Discovery**: Automatic registration of CLI commands
* **Argument Parsing**: Comprehensive argument parsing and validation
* **Service Integration**: Deep integration with the service container
* **Error Handling**: User-friendly error messages and recovery
* **Help System**: Auto-generated help and documentation

CLI Architecture
----------------

Command System
~~~~~~~~~~~~~~

The CLI uses a plugin-based command system where each command is implemented as a separate
module with automatic registration and discovery.

Parser Integration
~~~~~~~~~~~~~~~~~~

Argument parsing is handled through Click framework integration with custom extensions
for service container integration and configuration management.

Utility Functions
~~~~~~~~~~~~~~~~~

Common CLI utilities provide consistent user experience across all commands including
output formatting, progress indicators, and configuration management.

Key Features
------------

* **Modular Commands**: Each command is self-contained with its own module
* **Service Container Integration**: Commands can access all framework services
* **Configuration Support**: Commands inherit configuration management capabilities
* **Interactive Mode**: Support for interactive command execution
* **Batch Processing**: Commands support batch operations where applicable

.. Claude MPM API Reference documentation master file, created by
   sphinx-quickstart.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Claude MPM API Reference
=========================

Welcome to the Claude MPM API reference documentation. This documentation provides comprehensive 
coverage of all classes, methods, and interfaces in the Claude MPM framework.

Claude MPM (Multi-Agent Project Manager) is a framework that extends Claude Desktop with 
multi-agent orchestration capabilities, featuring a modern service-oriented architecture 
with interface-based contracts and dependency injection.

.. toctree::
   :maxdepth: 2
   :caption: Core API

   core/index
   services/index
   agents/index
   hooks/index
   cli/index

.. toctree::
   :maxdepth: 2
   :caption: Reference

   modules
   genindex
   modindex
   search

Quick Navigation
================

Core Components
---------------

* :doc:`core/interfaces` - Core service interfaces and contracts
* :doc:`core/container` - Dependency injection container
* :doc:`core/base_services` - Base service implementations
* :doc:`core/framework_loader` - Framework initialization and loading

Service Architecture
-------------------

* :doc:`services/agent_services` - Agent lifecycle and management
* :doc:`services/communication` - WebSocket and real-time communication
* :doc:`services/infrastructure` - Logging, monitoring, and infrastructure
* :doc:`services/project_services` - Project analysis and workspace management

Agent System
------------

* :doc:`agents/management` - Agent deployment and lifecycle management
* :doc:`agents/registry` - Agent discovery and metadata management
* :doc:`agents/loaders` - Agent loading and initialization
* :doc:`agents/validation` - Agent validation and schema checking

Hook System
-----------

* :doc:`hooks/base` - Base hook classes and interfaces
* :doc:`hooks/interceptors` - Tool call and validation interceptors
* :doc:`hooks/memory` - Memory integration hooks

CLI Interface
-------------

* :doc:`cli/commands` - CLI command implementations
* :doc:`cli/parser` - Command-line argument parsing
* :doc:`cli/utils` - CLI utilities and helpers

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
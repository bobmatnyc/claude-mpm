Services API
============

The services API provides the service-oriented architecture layer of Claude MPM,
organized into five specialized service domains:

.. toctree::
   :maxdepth: 2

   agent_services
   communication
   infrastructure
   project_services
   core_services

Overview
--------

The Claude MPM framework is built around a service-oriented architecture with clear
separation of concerns:

Service Domains
---------------

Agent Services
~~~~~~~~~~~~~~
Handle agent lifecycle, deployment, and management operations including:

* Agent deployment and validation
* Agent lifecycle management
* Agent versioning and updates
* Agent registry and discovery

Communication Services
~~~~~~~~~~~~~~~~~~~~~~
Provide real-time communication capabilities including:

* WebSocket and SocketIO servers
* Real-time event broadcasting
* Client connection management
* Dashboard communication

Infrastructure Services
~~~~~~~~~~~~~~~~~~~~~~~
Support framework operations with:

* Structured logging and monitoring
* Health monitoring and diagnostics
* Error handling and recovery
* Performance metrics collection

Project Services
~~~~~~~~~~~~~~~~
Analyze and manage project characteristics:

* Project structure analysis
* Technology stack detection
* Code pattern analysis
* Workspace management

Core Services
~~~~~~~~~~~~~
Provide foundational framework capabilities:

* Service container and dependency injection
* Configuration management
* Caching and performance optimization
* Template processing

Architecture Benefits
--------------------

* **Service Isolation**: Each domain has clear boundaries and responsibilities
* **Interface Contracts**: All services implement well-defined interfaces
* **Dependency Injection**: Automatic service resolution and lifecycle management
* **Performance Optimization**: Lazy loading, caching, and connection pooling
* **Extensibility**: Plugin architecture through interfaces and hooks

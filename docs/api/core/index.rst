Core API
========

The core API provides the foundation of the Claude MPM framework, including service interfaces,
dependency injection, and framework initialization components.

.. toctree::
   :maxdepth: 2

   interfaces
   container
   base_services
   framework_loader
   exceptions
   types

Overview
--------

The core API is built around a service-oriented architecture with the following key principles:

* **Interface-based contracts**: All services implement explicit interfaces
* **Dependency injection**: Automatic service resolution through the service container
* **Lazy loading**: Services are loaded only when needed for optimal performance
* **Type safety**: Strong typing throughout the framework

Key Components
--------------

Service Interfaces
~~~~~~~~~~~~~~~~~~

The framework defines core service interfaces that establish contracts for dependency injection,
service discovery, and framework orchestration. These interfaces reduce cyclomatic complexity
and establish clean separation of concerns.

Service Container
~~~~~~~~~~~~~~~~~

The dependency injection container manages service registration, resolution, and lifecycle.
It supports singleton and transient service lifetimes with automatic dependency resolution.

Framework Loader
~~~~~~~~~~~~~~~~

The framework loader is responsible for initializing the Claude MPM framework, loading
agent configurations, and setting up the runtime environment.

Architecture Benefits
--------------------

* **Better Testability**: Interface-based architecture enables easy mocking and testing
* **Improved Maintainability**: Clear separation of concerns and service boundaries  
* **Enhanced Reliability**: Comprehensive testing with 85%+ coverage target
* **Performance**: Intelligent caching and resource optimization foundations
* **Scalability**: Service-oriented design supports future growth
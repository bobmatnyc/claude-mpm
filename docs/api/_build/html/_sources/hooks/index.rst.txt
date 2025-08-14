Hooks API
=========

The hooks API provides extensibility points for the Claude MPM framework, allowing plugins
and extensions to modify behavior through a well-defined hook system.

.. toctree::
   :maxdepth: 2

   base
   interceptors
   memory
   validation

Overview
--------

The Claude MPM hook system provides:

* **Extensibility Points**: Pre and post-execution hooks for framework operations
* **Tool Interception**: Ability to intercept and modify tool calls
* **Memory Integration**: Hooks for memory management and persistence
* **Validation Hooks**: Custom validation logic integration
* **Event-Driven Architecture**: Hooks respond to framework events

Hook Types
----------

Base Hooks
~~~~~~~~~~

Core hook classes and interfaces that provide the foundation for all hook implementations.

Interceptors
~~~~~~~~~~~~

Tool call interceptors that can modify, validate, or enhance tool execution within the framework.

Memory Hooks
~~~~~~~~~~~~

Hooks that integrate with the memory system to provide persistence, optimization, and retrieval capabilities.

Validation Hooks
~~~~~~~~~~~~~~~~

Custom validation hooks that extend the framework's validation capabilities.

Architecture Benefits
--------------------

* **Plugin Architecture**: Clean extensibility without modifying core framework
* **Performance**: Hooks are executed only when registered and relevant  
* **Type Safety**: Strong typing throughout the hook system
* **Error Handling**: Comprehensive error handling and fallback mechanisms
* **Documentation**: Self-documenting hook interfaces and contracts
from typing import TypeVar, Type, Dict, Any

T = TypeVar("T")

_instances: Dict[Type, Any] = {}


def get_service(service_class: Type[T]) -> T:
    """
    Generic lazy service factory.

    Creates a single instance of the requested service class on first call,
    then returns the same instance on subsequent calls.

    Args:
        service_class: The service class to instantiate

    Returns:
        An instance of the service class
    """
    if service_class not in _instances:
        _instances[service_class] = service_class()
    return _instances[service_class]


def reset_service(service_class: Type[T]) -> None:
    """
    Reset a service instance.

    Args:
        service_class: The service class to reset
    """
    if service_class in _instances:
        del _instances[service_class]


def reset_all_services() -> None:
    """Reset all service instances."""
    _instances.clear()

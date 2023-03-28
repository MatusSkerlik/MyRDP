from threading import Lock
from typing import TypeVar, Generic

T = TypeVar("T")


class AutoLockingProxy:
    """
        A class that acts as a proxy for other objects and provides automatic locking and unlocking of the objects.

        This class intercepts attribute access using the __getattribute__ and __setattr__ methods to provide automatic locking
        and unlocking of the object attributes. If an attribute is an instance of AutoLockingValue, this class will automatically
        acquire and release a lock when accessing or modifying the attribute value.
    """

    def __getattribute__(self, item):
        attr = super().__getattribute__(item)
        if isinstance(attr, AutoLockingValue):
            return attr.get()
        else:
            return attr

    def __setattr__(self, key, value):
        try:
            attr = super().__getattribute__(key)
            if isinstance(attr, AutoLockingValue):
                attr.set(value)
                return
        except AttributeError:
            pass

        super().__setattr__(key, value)


class AutoLockingValue(Generic[T]):
    """
    A thread-safe class for managing a value with automatic locking and unlocking.

    This class provides a convenient way to protect access to a shared value
    between multiple threads. It ensures that read and write operations are
    atomic by automatically acquiring and releasing a lock whenever the value
    is accessed or modified.

    Example usage:

        shared_value = AutoLockingValue(initial_value=42)

        # Reading the value
        value = shared_value.get()

        # Writing a new value
        shared_value.set(84)

    Attributes:
        _value: The protected value.
        _lock: A threading.Lock object used to ensure atomic access to the value.
    """

    def __init__(self, value: T):
        self._value: T = value
        self._lock: Lock = Lock()

    def get(self) -> T:
        with self._lock:
            return self._value

    def set(self, value: T) -> None:
        with self._lock:
            self._value = value

    # Support for the `with` statement
    def __enter__(self):
        self._lock.acquire()
        return self._value

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()

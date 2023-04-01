import threading
from abc import abstractmethod

from lock import AutoLockingValue


class Task:
    """
    A class representing a background task that can be started and stopped.

    This class provides methods to start and stop a background thread that executes
    a `run` method. The `run` method should be overridden by subclasses to define
    the specific task that the thread should perform.

    Attributes:
    - running: An `AutoLockingValue` instance that tracks whether the task is running.
    - thread: A `threading.Thread` instance that represents the background thread.
    """

    def __init__(self):
        self.running = AutoLockingValue(False)
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True

    def start(self):
        self.running.setv(True)
        self.thread.start()

    def stop(self):
        self.running.setv(False)
        print(f"Exiting: {self}")
        self.thread.join()
        print(f"Exited: {self}")

    @abstractmethod
    def run(self):
        pass

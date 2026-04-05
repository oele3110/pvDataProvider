from abc import ABC, abstractmethod


class BaseReader(ABC):
    @abstractmethod
    async def start(self) -> None:
        """Start polling/subscribing. Should run until stop() is called."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully stop the reader."""
        ...

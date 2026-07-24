from abc import ABC, abstractmethod


class BasePlatformAdapter(ABC):
    @abstractmethod
    def publish(self, post_target):
        """Publish a scheduled post target. Return True when publishing succeeds."""

from abc import ABC, abstractmethod

class BaseSpeaker(ABC):
    @abstractmethod
    def speak(self, text: str):
        pass
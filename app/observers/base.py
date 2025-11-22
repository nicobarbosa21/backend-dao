from abc import ABC, abstractmethod
from typing import Any, List


class Observer(ABC):
    @abstractmethod
    def update(self, data: Any) -> None:
        raise NotImplementedError


class Subject:
    def __init__(self) -> None:
        self._observers: List[Observer] = []

    def attach(self, observer: Observer) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, data: Any) -> None:
        for observer in list(self._observers):
            observer.update(data)

from abc import ABC, abstractmethod


class GasProvider(ABC):

    @abstractmethod
    def gas_price(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def gas_limit(self) -> int:
        raise NotImplementedError


class StaticGasProvider(GasProvider, ABC):

    def __init__(self, price, limit):
        self.price = price
        self.limit = limit

    def gas_price(self) -> int:
        return self.price

    def gas_limit(self):
        return self.limit


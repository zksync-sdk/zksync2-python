from abc import ABC, abstractmethod

# INFO: gas price strategy (set_gas_price_strategy) method of Module
#       does not fit the requirements of custom set of Gas price & limit
#       So these types are used instead


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


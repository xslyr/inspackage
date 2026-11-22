"""Core module."""


class Base:
    """Base class."""

    class_var = 1
    typed_var: int = 2
    _hidden_var = 3

    def __init__(self, name):
        self.name = name

    @property
    def prop_value(self):
        return self.name

    @classmethod
    def from_name(cls, cls_name):
        return cls(cls_name)

    @staticmethod
    def static_helper(value):
        return value

    def public_method(self, itself, other: int = 1) -> str:
        return str(itself)

    def calls_super_marker(self):
        return super().__repr__()

    def _private_method(self):
        return None

    async def async_method(self, value):
        return value

    class Inner:
        """Nested class."""

        inner_var = 0

        def inner_method(self):
            return 1


class Child(Base):
    def __init__(self, name):
        super().__init__(name)

    def reset(self):
        super().__init__(self.name)

    def uses_inner_def(self):
        def _local():
            return 1

        return _local()


class _PrivateClass:
    pass


def top_level(a, b: int = 2) -> int:
    return a + b


async def top_level_async(x):
    return x


def _private_func():
    return None

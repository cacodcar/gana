"""An element in a set"""


class X:
    """A Member of an Ordered Set"""

    def __init__(self):
        self.parent: list = []
        self.name: str = None
        self.number: int = None

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

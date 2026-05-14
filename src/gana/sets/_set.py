"""A general set"""

from .index import I


class _X:
    """A general set

    :param index: Indices of contained elements.
    :type index: I
    :param tag: Tag/details
    :type tag: str, optional
    :param ltx: LaTeX representation. Defaults to empty string.
    :type ltx: str, optional
    :param mutable: If the parameter set is mutable. Defaults to False.
    :type mutable: bool, optional
    :param name: Name of the set, ideally set by Prg. Defaults to empty string.
    :type name: str, optional
    """

    def __init__(
        self,
        *index: I,
        tag: str = "",
        ltx: str = "",
        mutable: bool = False,
        name: str = "",
    ):
        self.tag = tag
        self._ltx = ltx
        self.mutable = mutable
        self.name = name

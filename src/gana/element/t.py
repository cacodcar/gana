"""Parametric variable
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sympy import IndexedBase


class T:
    """Parametric variable"""
    def __init__(self, name: str = 't'):
        self.name = name 

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

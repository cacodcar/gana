"""Shared numeric annotation aliases, preserving existing container shapes."""

# Preserve the existing one-element tuple annotation.
type Number = int | float
type NumericTuple = tuple[Number]
type NumericList = list[Number | NumericTuple]

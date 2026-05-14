from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class UndoStack(Generic[T]):
    """Generic undo/redo stack.

    Call ``push(state)`` to save the *current* state before a change.
    Call ``undo(current)`` to get the previous state (current is pushed
    onto the redo stack).  ``redo(current)`` mirrors it.
    """

    def __init__(self) -> None:
        self._undo: list[T] = []
        self._redo: list[T] = []
        self._dirty = False

    @property
    def dirty(self) -> bool:
        """True after ``push()`` until explicitly reset via ``dirty = False``
        or ``clear()``."""
        return self._dirty

    @dirty.setter
    def dirty(self, value: bool) -> None:
        self._dirty = value

    def push(self, state: T) -> None:
        """Save *state* and clear the redo history."""
        self._undo.append(state)
        self._redo.clear()
        self._dirty = True

    def undo(self, current: T) -> T | None:
        """Pop the last saved state, pushing *current* onto redo.
        Returns ``None`` if nothing to undo."""
        if not self._undo:
            return None
        self._redo.append(current)
        return self._undo.pop()

    def redo(self, current: T) -> T | None:
        """Pop the last undone state, pushing *current* onto undo.
        Returns ``None`` if nothing to redo."""
        if not self._redo:
            return None
        self._undo.append(current)
        return self._redo.pop()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
        self._dirty = False

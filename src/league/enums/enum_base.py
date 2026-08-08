from enum import IntEnum, StrEnum


class LookupEnum(IntEnum):
    """IntEnum with case-insensitive name lookup helpers."""

    @classmethod
    def from_name[T](cls: T, name: str) -> T:
        """Look up a member by name, case- and separator-insensitive."""
        key = name.strip().upper().replace(" ", "_").replace("-", "_")
        try:
            return cls[key]
        except KeyError:
            raise KeyError(f"{cls.__name__} has no member {name!r}") from None

    @classmethod
    def try_from_name[T](cls: T, name: str) -> T | None:
        """Like `from_name` but returns None instead of raising."""
        try:
            return cls.from_name(name)
        except KeyError:
            return None


class LookupStrEnum(StrEnum):
    """StrEnum with case-insensitive name lookup helpers."""

    @classmethod
    def from_name[T](cls: T, name: str) -> T:
        """Look up a member by name, case- and separator-insensitive."""
        key = name.strip().upper().replace(" ", "_").replace("-", "_")
        try:
            return cls[key]
        except KeyError:
            raise KeyError(f"{cls.__name__} has no member {name!r}") from None

    @classmethod
    def try_from_name[T](cls: T, name: str) -> T | None:
        """Like `from_name` but returns None instead of raising."""
        try:
            return cls.from_name(name)
        except KeyError:
            return None

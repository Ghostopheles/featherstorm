from enum import IntEnum, StrEnum


class LookupEnum(IntEnum):
    """IntEnum with case-insensitive name lookup helpers."""

    @classmethod
    def from_name[T](cls: T, name: str) -> T:
        """Look up a member by name, case- and separator-insensitive."""
        key = str(name).strip().upper().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.name.upper() == key:
                return member
        raise KeyError(f"{cls.__name__} has no member {name!r}")

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
        key = str(name).strip().upper().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.name.upper() == key:
                return member
        raise KeyError(f"{cls.__name__} has no member {name!r}")

    @classmethod
    def try_from_name[T](cls: T, name: str) -> T | None:
        """Like `from_name` but returns None instead of raising."""
        try:
            return cls.from_name(name)
        except KeyError:
            return None

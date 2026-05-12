import json

from pathlib import Path
from functools import wraps
from typing import Callable, Any

type RuleDefinition = Callable[..., bool]
type RuleRegistry = dict[str, PredicateFactory[Any]]

type PredicateFunc[T] = Callable[[T], bool]
type PredicateFactory[T] = Callable[..., Predicate[T]]

_RULES: RuleRegistry = {}


class Predicate[T]:
    """
    A composable predicate that supports &, |, and ~ operators.
    Wraps a function (T -> bool)
    """

    def __init__(self, fn: PredicateFunc[T]):
        self.fn = fn

    def __call__(self, obj: T, **kwargs) -> bool:
        return self.fn(obj, **kwargs)

    def __and__(self, other: "Predicate"[T]) -> "Predicate"[T]:
        return Predicate(lambda i, **kw: self(i, **kw) and other(i, **kw))

    def __or__(self, other: "Predicate"[T]) -> "Predicate"[T]:
        return Predicate(lambda i, **kw: self(i, **kw) or other(i, **kw))

    def __invert__(self) -> "Predicate"[T]:
        return Predicate(lambda i, **kw: not self(i, **kw))


def rule[T](fn: RuleDefinition) -> PredicateFactory[T]:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Predicate[T]:
        return Predicate(lambda obj, **kw: fn(*args, obj, **{**kwargs, **kw}))

    _RULES[fn.__name__] = wrapper
    return wrapper


def _build_predicate_from_dict(config: dict) -> Predicate[Any]:
    preds: list[Predicate[Any]] = []

    for cond in config["conditions"]:
        name = cond["name"]
        args = cond.get("args", [])

        if name not in _RULES:
            raise ValueError(f"Unknown rule: {name}")

        factory = _RULES[name]
        predicate_obj = factory(*args)
        preds.append(predicate_obj)

    combined = preds[0]
    logic = config["logic"]

    for p in preds[1:]:
        combined = (combined & p) if logic == "AND" else (combined | p)

    return combined


def load_rule_from_config(path: Path) -> Predicate[Any]:
    """
    Load rules from a JSON config file with the following structure:
    {
        "logic": "AND",
        "conditions": [
            {"name": "is_active", "args": []},
            {"name": "older_than", "args": [30]}
        ]
    }

    The returned object is a composed Predicate[Any].
    """

    assert path.exists(), "Invalid rule config path"

    with open(path) as f:
        config = json.load(f)

    return _build_predicate_from_dict(config)


def load_rule_from_dict(config: dict) -> Predicate[Any]:
    """
    Load rules from an already-parsed config dict. Same structure as load_rule_from_config
    but accepts a dict directly (e.g. from a database JSON column).
    """
    return _build_predicate_from_dict(config)

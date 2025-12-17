---
name: python-best-practices
description: >
  Provide Python coding best practices, design patterns, style guidelines,
  and performance optimization tips. Use when user asks about "Python best practices",
  "how to write better Python", "Python patterns", "PEP 8", "Python style guide",
  "Python optimization", "Pythonic code", or Python code quality questions.
license: CC-BY-4.0
metadata:
  topics:
    - style
    - patterns
    - performance
    - testing
    - typing
---

# Python Best Practices

Comprehensive guide to writing clean, efficient, and maintainable Python code.

## Code Style (PEP 8)

### Indentation & Spacing
- Use 4 spaces for indentation (never tabs)
- Maximum line length: 79 characters (99 for modern projects)
- Use blank lines to separate functions and classes

### Naming Conventions
```python
# Variables and functions: snake_case
user_name = "John"
def calculate_total():
    pass

# Classes: PascalCase
class UserAccount:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_CONNECTIONS = 100

# Private: leading underscore
_internal_value = 42

# "Really" private: double underscore
__very_private = "hidden"
```

### Imports
```python
# Standard library
import os
import sys

# Third-party
import numpy as np
import pandas as pd

# Local
from mypackage import mymodule

# Avoid: from module import *
```

## Type Hints (PEP 484)

```python
from typing import List, Dict, Optional, Union, Callable

def greet(name: str) -> str:
    return f"Hello, {name}!"

def process_items(items: List[int]) -> Dict[str, int]:
    return {"sum": sum(items), "count": len(items)}

def find_user(user_id: int) -> Optional[User]:
    """Returns User or None if not found."""
    pass

def handler(callback: Callable[[int, str], bool]) -> None:
    pass
```

## Design Patterns

### Factory Pattern
```python
class Animal:
    def speak(self) -> str:
        raise NotImplementedError

class Dog(Animal):
    def speak(self) -> str:
        return "Woof!"

class Cat(Animal):
    def speak(self) -> str:
        return "Meow!"

def animal_factory(animal_type: str) -> Animal:
    animals = {"dog": Dog, "cat": Cat}
    return animals[animal_type]()
```

### Singleton Pattern
```python
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### Context Manager
```python
from contextlib import contextmanager

@contextmanager
def managed_resource():
    resource = acquire_resource()
    try:
        yield resource
    finally:
        release_resource(resource)

# Usage
with managed_resource() as r:
    r.do_something()
```

## Performance Tips

### Use List Comprehensions
```python
# ❌ Slow
squares = []
for x in range(1000):
    squares.append(x ** 2)

# ✅ Fast
squares = [x ** 2 for x in range(1000)]
```

### Use Generators for Large Data
```python
# ❌ Memory-heavy
def get_all_lines(files):
    lines = []
    for f in files:
        lines.extend(open(f).readlines())
    return lines

# ✅ Memory-efficient
def get_all_lines(files):
    for f in files:
        yield from open(f)
```

### Use Built-in Functions
```python
# ❌ Manual
total = 0
for num in numbers:
    total += num

# ✅ Built-in
total = sum(numbers)

# Other useful built-ins
any([True, False, False])  # True
all([True, True, True])    # True
max(numbers), min(numbers)
sorted(items, key=lambda x: x.name)
```

### Use `collections` Module
```python
from collections import defaultdict, Counter, deque

# defaultdict - no KeyError
word_count = defaultdict(int)
for word in words:
    word_count[word] += 1

# Counter - even easier
word_count = Counter(words)

# deque - fast append/pop from both ends
queue = deque(maxlen=100)
```

## Error Handling

```python
# Specific exceptions
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
except IOError as e:
    logger.error(f"IO error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise

# Context managers for cleanup
try:
    f = open("file.txt")
    data = f.read()
finally:
    f.close()

# Better: use with statement
with open("file.txt") as f:
    data = f.read()
```

## Testing

```python
import pytest

# Basic test
def test_addition():
    assert add(2, 3) == 5

# Parametrized test
@pytest.mark.parametrize("input,expected", [
    (1, 1),
    (2, 4),
    (3, 9),
])
def test_square(input, expected):
    assert square(input) == expected

# Fixtures
@pytest.fixture
def sample_user():
    return User(name="Test", email="test@example.com")

def test_user_email(sample_user):
    assert "@" in sample_user.email
```

## Documentation

```python
def calculate_compound_interest(
    principal: float,
    rate: float,
    time: int,
    n: int = 12
) -> float:
    """
    Calculate compound interest.

    Args:
        principal: Initial investment amount
        rate: Annual interest rate (as decimal, e.g., 0.05 for 5%)
        time: Time period in years
        n: Number of times interest compounds per year

    Returns:
        Final amount after compound interest

    Example:
        >>> calculate_compound_interest(1000, 0.05, 10)
        1647.01

    Raises:
        ValueError: If principal or rate is negative
    """
    if principal < 0 or rate < 0:
        raise ValueError("Principal and rate must be non-negative")

    return principal * (1 + rate / n) ** (n * time)
```

## Modern Python Features

### f-strings (3.6+)
```python
name = "World"
print(f"Hello, {name}!")
print(f"{value:.2f}")  # Formatting
print(f"{name=}")      # Debug (3.8+)
```

### Walrus Operator (3.8+)
```python
# Assign and use in one expression
if (n := len(items)) > 10:
    print(f"Too many items: {n}")
```

### Pattern Matching (3.10+)
```python
match command:
    case "quit":
        sys.exit()
    case "help":
        show_help()
    case ["go", direction]:
        move(direction)
    case _:
        print("Unknown command")
```

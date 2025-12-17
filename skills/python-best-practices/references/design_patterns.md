# Python Design Patterns Reference

## Creational Patterns

### Factory Method
Create objects without specifying exact class.

```python
from abc import ABC, abstractmethod

class Creator(ABC):
    @abstractmethod
    def factory_method(self):
        pass

    def operation(self):
        product = self.factory_method()
        return f"Working with {product.operation()}"

class ConcreteCreatorA(Creator):
    def factory_method(self):
        return ConcreteProductA()

class ConcreteCreatorB(Creator):
    def factory_method(self):
        return ConcreteProductB()
```

### Builder
Construct complex objects step by step.

```python
class QueryBuilder:
    def __init__(self):
        self._select = []
        self._from = None
        self._where = []

    def select(self, *fields):
        self._select.extend(fields)
        return self

    def from_table(self, table):
        self._from = table
        return self

    def where(self, condition):
        self._where.append(condition)
        return self

    def build(self):
        query = f"SELECT {', '.join(self._select)} FROM {self._from}"
        if self._where:
            query += f" WHERE {' AND '.join(self._where)}"
        return query

# Usage
query = (QueryBuilder()
    .select("name", "email")
    .from_table("users")
    .where("active = true")
    .build())
```

## Structural Patterns

### Adapter
Convert interface of a class into another interface.

```python
class OldAPI:
    def old_request(self):
        return "Old API response"

class NewAPIAdapter:
    def __init__(self, old_api):
        self._old_api = old_api

    def request(self):
        return self._old_api.old_request()
```

### Decorator
Add behavior to objects dynamically.

```python
from functools import wraps

def log_calls(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Finished {func.__name__}")
        return result
    return wrapper

@log_calls
def process_data(data):
    return data.upper()
```

## Behavioral Patterns

### Observer
Define subscription mechanism for events.

```python
class Subject:
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        self._observers.append(observer)

    def notify(self, message):
        for observer in self._observers:
            observer.update(message)

class Observer:
    def update(self, message):
        print(f"Received: {message}")
```

### Strategy
Define family of algorithms and make them interchangeable.

```python
from abc import ABC, abstractmethod

class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount):
        pass

class CreditCardPayment(PaymentStrategy):
    def pay(self, amount):
        return f"Paid ${amount} via credit card"

class PayPalPayment(PaymentStrategy):
    def pay(self, amount):
        return f"Paid ${amount} via PayPal"

class ShoppingCart:
    def __init__(self, payment_strategy: PaymentStrategy):
        self._payment = payment_strategy

    def checkout(self, amount):
        return self._payment.pay(amount)
```

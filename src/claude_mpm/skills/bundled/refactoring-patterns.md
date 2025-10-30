---
skill_id: refactoring-patterns
skill_version: 0.1.0
description: Common refactoring techniques to improve code quality without changing behavior.
updated_at: 2025-10-30T17:00:00Z
tags: [refactoring, code-quality, patterns, maintainability]
---

# Refactoring Patterns

Common refactoring techniques to improve code quality without changing behavior.

## Extract Method
```python
# Before: Long method doing multiple things
def process_order(order):
    # Validate
    if not order.items:
        raise ValueError("Empty order")
    # Calculate
    total = sum(item.price for item in order.items)
    tax = total * 0.1
    # Save
    db.save(order)
    return total + tax

# After: Extracted into focused methods
def process_order(order):
    validate_order(order)
    total = calculate_total(order)
    save_order(order)
    return total

def validate_order(order):
    if not order.items:
        raise ValueError("Empty order")

def calculate_total(order):
    subtotal = sum(item.price for item in order.items)
    tax = subtotal * 0.1
    return subtotal + tax

def save_order(order):
    db.save(order)
```

## Extract Variable
```python
# Before: Complex expression
if (user.age >= 18 and user.has_license and
    user.insurance_valid and not user.suspended):
    allow_driving()

# After: Named variable
is_eligible_driver = (
    user.age >= 18 and
    user.has_license and
    user.insurance_valid and
    not user.suspended
)
if is_eligible_driver:
    allow_driving()
```

## Replace Magic Number
```python
# Before
if response.status == 200:
    process()

# After
HTTP_OK = 200
if response.status == HTTP_OK:
    process()
```

## Replace Conditional with Polymorphism
```python
# Before
class Animal:
    def make_sound(self):
        if self.type == "dog":
            return "Woof"
        elif self.type == "cat":
            return "Meow"

# After
class Dog(Animal):
    def make_sound(self):
        return "Woof"

class Cat(Animal):
    def make_sound(self):
        return "Meow"
```

## Extract Class
```python
# Before: God class doing too much
class User:
    def __init__(self):
        self.name = ""
        self.email = ""
        self.street = ""
        self.city = ""
        self.zip = ""

    def format_address(self):
        return f"{self.street}, {self.city} {self.zip}"

# After: Separate concerns
class Address:
    def __init__(self, street, city, zip_code):
        self.street = street
        self.city = city
        self.zip = zip_code

    def format(self):
        return f"{self.street}, {self.city} {self.zip}"

class User:
    def __init__(self, name, email, address):
        self.name = name
        self.email = email
        self.address = address
```

## Introduce Parameter Object
```python
# Before: Too many parameters
def create_user(name, email, street, city, zip_code, phone):
    pass

# After: Group related parameters
@dataclass
class UserData:
    name: str
    email: str
    address: Address
    phone: str

def create_user(user_data: UserData):
    pass
```

## Replace Loop with Pipeline
```python
# Before: Imperative loop
result = []
for item in items:
    if item.active:
        processed = process(item)
        result.append(processed)

# After: Functional pipeline
result = [
    process(item)
    for item in items
    if item.active
]
```

## When to Refactor
- Before adding new feature (make room)
- During code review (improve quality)
- When fixing bugs (prevent recurrence)
- When code smells emerge (tech debt)

## Refactoring Safety
1. Have tests in place
2. Make small changes
3. Test after each change
4. Commit frequently
5. Use IDE refactoring tools

## Remember
- Refactor or add feature, never both
- Tests must pass before and after
- Small steps are safer than big rewrites
- Leave code better than you found it

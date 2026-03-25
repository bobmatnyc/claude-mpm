# Common Findings and Fix Patterns

Scanners often surface the same classes of issues. Fix patterns are usually stable even as tooling changes.

## Injection

✅ **Correct: parameterized SQL**
```python
query = "SELECT * FROM users WHERE email = %s"
cursor.execute(query, (user_email,))
```

❌ **Incorrect: string interpolation**
```python
query = f"SELECT * FROM users WHERE email = '{user_email}'"
```

## Command Injection

✅ **Correct: structured subprocess invocation**
```python
import subprocess

subprocess.run(["ping", "-c", "1", user_input], check=True)
```

❌ **Incorrect: shell interpolation**
```python
import os

os.system(f"ping {user_input}")
```

## Authentication and Authorization

✅ **Correct: hash passwords**
```python
from werkzeug.security import generate_password_hash

password_hash = generate_password_hash(password)
```

✅ **Correct: enforce authorization server-side**
```python
def delete_user(user_id, current_user):
    if not current_user.is_admin:
        raise PermissionError()
    User.delete(user_id)
```

## Sensitive Data Exposure

✅ **Correct: do not log secrets**
```python
logger.info("User login attempt", extra={"email": email})
```

❌ **Incorrect: logging credentials**
```python
logger.info(f"User logged in: {email}, password: {password}")
```

✅ **Correct: load secrets from environment**
```python
import os

api_key = os.getenv("API_KEY")
```

## XXE (XML External Entities)

✅ **Correct: use hardened XML parsers**
```python
import defusedxml.ElementTree as ET

tree = ET.parse(user_supplied_xml)
```

## XSS

✅ **Correct: render untrusted strings safely**
```js
element.textContent = userInput;
```

❌ **Incorrect: HTML injection**
```js
element.innerHTML = userInput;
```

Framework notes:
- React: render strings as `{userInput}` (auto-escaped)
- Vue: render strings as `{{ userInput }}` (auto-escaped)

## Insecure Deserialization

✅ **Correct: parse structured data with validation**
```python
import json

data = json.loads(user_data)
```

❌ **Incorrect: deserialize untrusted pickles**
```python
import pickle

data = pickle.loads(user_data)
```

## Logging and Monitoring

Log security-relevant events (without secrets):
- auth failures and lockouts
- privilege changes and admin actions
- unusual access patterns (rate spikes, suspicious geos)

Include request IDs and actor identity in audit logs.


# django-translation-lint

Validate that Django translation strings start with lowercase.

## Example

Invalid:

```python
_("User not found")
```

Valid:

```python
_("user not found")
```

## Usage

```yaml
repos:
  - repo: https://github.com/YOUR_ORG/django-translation-lint
    rev: v0.1.0
    hooks:
      - id: django-translation-lint
```
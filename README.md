# django-translation-lint

Validate that Django translation strings are fully lowercase.

## Example

Invalid:

```python
_("User not found")
_("user Not found")
```

Valid:

```python
_("user not found")
_("hello %(name)s")
```

## Usage

```yaml
repos:
  - repo: https://github.com/YOUR_ORG/django-translation-lint
    rev: v0.1.0
    hooks:
      - id: django-translation-lint
```
---
name: code-review
description: >
  Perform comprehensive code review for pull requests, analyze code quality,
  identify bugs and security issues, suggest improvements, and check best practices.
  Use when user asks to "review code", "check PR", "analyze code quality",
  "find bugs in code", or mentions code review and code analysis.
license: MIT
metadata:
  languages:
    - python
    - javascript
    - typescript
    - go
    - rust
  categories:
    - development
    - quality
---

# Code Review Skill

Perform thorough code reviews following industry best practices.

## Review Process

When reviewing code, follow this systematic approach:

### 1. Initial Scan
- Read the code changes completely before commenting
- Understand the context and purpose of the changes
- Identify the scope and impact of modifications

### 2. Quality Checks

#### Correctness
- Does the code do what it's supposed to do?
- Are edge cases handled properly?
- Is the logic correct and complete?

#### Performance
- Are there any obvious performance issues?
- Could algorithms be more efficient?
- Are there unnecessary computations or memory usage?

#### Security
- Any potential security vulnerabilities?
- Is user input properly validated?
- Are secrets/credentials exposed?

#### Readability
- Is the code easy to understand?
- Are variable/function names descriptive?
- Is the code well-organized?

### 3. Best Practices

Check for adherence to:
- Naming conventions (camelCase, snake_case, etc.)
- Code structure and organization
- Error handling patterns
- Documentation and comments
- DRY (Don't Repeat Yourself) principle
- SOLID principles where applicable

### 4. Output Format

Provide your review in this structure:

```markdown
## Summary
[One-line summary of the overall code quality]

## Strengths
- [What's done well]

## Issues Found

### Critical (Must Fix)
- [ ] Issue 1: [Description and location]
- [ ] Issue 2: [Description and location]

### Medium (Should Fix)
- [ ] Issue 1: [Description]

### Minor (Nice to Have)
- [ ] Issue 1: [Description]

## Suggestions
- [Improvement ideas that aren't issues]

## Code Examples
[Show before/after for suggested improvements]
```

## Example Review

### Input Code
```python
def calc(x,y):
    return x+y
```

### Review Output

**Summary**: Function works but lacks type hints, docstring, and has poor naming.

**Issues**:
- ❌ Function name `calc` is too vague - use descriptive names like `calculate_sum`
- ❌ Missing type hints for parameters and return value
- ❌ Missing docstring explaining the function's purpose
- ⚠️ No input validation

**Suggested Improvement**:
```python
def calculate_sum(x: int, y: int) -> int:
    """
    Calculate the sum of two integers.

    Args:
        x: First integer
        y: Second integer

    Returns:
        Sum of x and y
    """
    return x + y
```

## Language-Specific Guidelines

### Python
- Follow PEP 8 style guide
- Use type hints (Python 3.5+)
- Prefer f-strings over .format()
- Use context managers for resources

### JavaScript/TypeScript
- Use const/let, avoid var
- Prefer async/await over callbacks
- Use TypeScript for type safety
- Follow ESLint recommendations

### Go
- Follow effective Go guidelines
- Handle all errors explicitly
- Use meaningful package names
- Write idiomatic Go code

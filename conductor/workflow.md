# Workflow

## TDD Policy

**Moderate** — Tests are encouraged but not a hard gate. Write tests for complex logic, protocol handlers, and API endpoints. Frontend visual changes may be verified manually.

## Commit Strategy

**Conventional Commits** with sign-off:

```
feat(scope): description      # New feature
fix(scope): description       # Bug fix
refactor(scope): description  # Code restructuring
test(scope): description      # Test additions/changes
docs(scope): description      # Documentation
chore(scope): description     # Maintenance
```

All commits must use `git commit -s` for developer sign-off.

## Code Review

**Required for non-trivial changes.** Trivial fixes (typos, formatting) can be self-reviewed.

## Verification Checkpoints

**At track completion only.** Individual tasks and phases do not require manual verification gates — verify when the full track is ready for merge.

## Task Lifecycle

1. **New** — Task created, not started
2. **In Progress** — Active development
3. **Review** — Code complete, awaiting review
4. **Complete** — Merged and verified

## Branch Strategy

- Feature branches: `feat/<track-name>`
- Bug fix branches: `fix/<description>`
- Branch from `main`, merge back to `main`

## Pre-commit Hooks

Automated on every commit:
- Trailing whitespace / end-of-file fixes
- Ruff format + lint (Python)
- Bandit security scanning (Python)
- Codespell (all files)
- JSON/YAML validation

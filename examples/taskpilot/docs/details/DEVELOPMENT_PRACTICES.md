# Development Practices

## Critical: Always Run Tests After Changes

**Rule**: **ALWAYS run unit tests when making any code changes.**

### Why This Matters

- Catches regressions immediately
- Verifies changes work as expected
- Prevents breaking existing functionality
- Ensures code quality before committing

### How to Run Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/test_<module>.py -v

# Run specific test
pytest tests/test_<module>.py::TestClass::test_method -v

# Quick test run (no coverage)
pytest tests/ -v --tb=short
```

### When to Run Tests

- ✅ After adding new code
- ✅ After modifying existing code
- ✅ After refactoring
- ✅ After fixing bugs
- ✅ Before committing changes
- ✅ After merging branches

### Test Execution Strategy

1. **After any code change**: Run relevant test file(s)
2. **Before committing**: Run full test suite
3. **For new features**: Add tests first (TDD), then run them
4. **For bug fixes**: Add regression test, then run all tests

### Notes

- Tests use in-memory metrics collectors to avoid file locking
- Some tests may require optional dependencies (FastAPI, OpenTelemetry)
- Tests should run independently and in parallel
- If tests hang, check for file I/O issues in MetricsCollector

---

*This is a critical development practice - never skip running tests after changes.*

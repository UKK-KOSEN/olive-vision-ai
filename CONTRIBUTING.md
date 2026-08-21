# Contributing to OliveVision AI

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch
4. Make your changes
5. Run tests
6. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/olive-vision-ai.git
cd olive-vision-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov ruff

# Run tests
pytest tests/ -v
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Keep functions focused and small
- Add docstrings for public functions

## Testing

All contributions should include tests:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test
pytest tests/test_runtime.py::RuntimeTest::test_analyze_returns_tree_id_when_qr_present -v
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update the improvement log if applicable
5. Request a review

## Reporting Issues

- Use GitHub Issues
- Include steps to reproduce
- Include expected vs actual behavior
- Include Python version and OS

## Code of Conduct

Be respectful and constructive in all interactions.

## Questions?

Open an issue or reach out to the maintainers.

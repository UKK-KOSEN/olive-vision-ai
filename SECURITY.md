# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| < 0.3   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within OliveVision AI, please send an email to the repository maintainers. All vulnerabilities will be promptly addressed.

**Please do NOT report security vulnerabilities through public GitHub issues.**

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Fix or mitigation**: Within 2 weeks for critical issues

## Security Measures

### Automated Scanning

- **Bandit**: Python security linter runs on every push/PR
- **Dependabot**: Weekly dependency vulnerability scanning
- **Dependency Review**: PR-level dependency vulnerability checks

### Best Practices

- No secrets or API keys in code
- All dependencies are pinned to specific versions
- Security headers in API responses
- Input validation on all user-provided data

### API Security

The soil moisture API uses:
- API key authentication (`X-Sensor-Api-Key` header)
- Timing-safe comparison for key validation
- CORS restricted to specific origins
- Rate limiting on public endpoints

## Configuration

### Environment Variables

Never commit these to the repository:

- `SENSOR_API_KEY` - API authentication key
- `RAW_DATA_PASSWORD` - Raw data access password
- `ADMIN_PASSWORD` - Admin API password

### Secrets Management

Use GitHub Secrets or environment variables for:
- API keys
- Database credentials
- Deployment tokens

## Updates

Security updates are released as patch versions (e.g., 0.3.1 → 0.3.2).

Subscribe to releases for notifications.

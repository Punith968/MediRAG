# Security Policy

## Reporting a vulnerability

Please do not disclose security vulnerabilities in a public GitHub issue.

For sensitive reports, contact the repository maintainer privately through the contact method listed on the GitHub profile. Include:
- affected component;
- reproduction steps;
- impact;
- relevant logs or screenshots with secrets removed.

Please allow reasonable time for investigation and remediation before public disclosure.

## Secrets and sensitive data

Never commit:
- API keys or tokens;
- credentials;
- private certificates;
- real patient/clinical records;
- personally identifiable information.

Use environment variables and the provided example environment file for local configuration.

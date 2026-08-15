# Security Policy

LocalMechAI is a local-first diagnostics application that can inspect system-health information and propose repair actions.

## Security Baseline

- Keep the local agent bound to localhost by default.
- Do not expose repair endpoints directly to the public internet.
- Require explicit user approval before any repair or high-impact system action.
- Keep repair actions allowlisted and conservative.
- Never commit Gemini/API credentials, tokens, private reports, or machine-specific sensitive data.
- Prefer Ollama or deterministic local reasoning when privacy is a priority.
- Clearly disclose when configuring a cloud AI provider changes the data boundary.
- Validate commands and reject actions outside the supported repair protocol.
- Avoid logging secrets or unnecessary system-sensitive information.

## Remote Access

Remote access requires a separate authenticated, encrypted, least-privilege design. Binding the local service to a non-local interface without those protections is not considered a supported secure deployment.

## Reporting

Do not publish credentials, private machine data, or actionable security weaknesses in a public issue. Report sensitive concerns privately to the project owner.

---

**Sponsored by CREIGNIFICENT LLC.**

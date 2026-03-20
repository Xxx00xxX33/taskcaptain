# Security Policy

## Supported deployment model

TaskCaptain is designed primarily for **trusted local environments**.

It is a local execution console for supervising Codex-driven work and may handle:

- local workspace paths
- execution logs
- agent configuration
- API endpoints and credentials supplied by the operator

The current implementation should be treated as a **single-operator local tool**, not a hardened multi-tenant web service.

## Security expectations

Before exposing TaskCaptain beyond localhost, add your own controls.

Recommended minimum controls:

- place it behind a reverse proxy
- require authentication
- enable HTTPS
- restrict source IPs where possible
- run with least privilege
- avoid sharing the writable workspace with unrelated processes
- protect `.env` and any local secret material

## Not currently provided by the application

The repository does not currently implement:

- built-in authentication
- multi-user authorization
- tenant isolation
- secret-management workflows
- hardened public-internet defaults

## Reporting a vulnerability

If you discover a security issue, please do **not** disclose it publicly first.

Preferred process:

1. Prepare a short report describing the issue, impact, and reproduction steps.
2. Include any suggested mitigation if available.
3. Send the report privately to the project maintainer.
4. Allow reasonable time for confirmation and remediation before public disclosure.

If a dedicated security contact is added later, this document should be updated accordingly.

## Operational advice

- Do not commit real API keys, tokens, or private endpoints.
- Do not expose the service directly to the public internet without compensating controls.
- Review logs before sharing them, since they may include operational details.
- If credentials were pasted into chat, logs, screenshots, or commits, assume exposure and rotate them.

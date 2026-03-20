# Contributing to TaskCaptain

Thanks for contributing.

TaskCaptain is intentionally small, local-first, and easy to inspect. Please keep changes aligned with that direction.

## Scope

Good contributions include:

- bug fixes
- documentation improvements
- runtime stability improvements
- UX improvements that keep the execution model clear
- portability improvements
- testability and maintainability improvements

Please avoid changes that make the project significantly heavier without a clear operational benefit.

## Development principles

- Keep task state on disk and inspectable.
- Preserve the separation between User ↔ Agent and Agent ↔ Codex.
- Prefer explicit control flow over hidden orchestration.
- Prefer standard-library or low-dependency solutions when practical.
- Avoid machine-specific assumptions in paths, ports, or credentials.
- Keep user-facing documentation accurate to the current implementation.

## Local setup

```bash
git clone https://github.com/LongWeihan/taskcaptain.git
cd taskcaptain
chmod +x run.sh restart.sh
```

Optional local environment file:

```bash
cp .env.example .env
set -a
source .env
set +a
```

## Minimum checks before submitting

Run at minimum:

```bash
python3 -m py_compile app/server.py
./restart.sh
```

If your change affects runtime behavior, also verify the relevant UI flow manually.

## Commit guidance

Please keep commits:

- small enough to review
- scoped to a single change when practical
- written with clear commit messages

Examples:

- `Fix hard-coded runtime root path`
- `Document security model for local deployment`
- `Improve README quick start and config docs`

## Pull requests

A good pull request should include:

- what changed
- why it changed
- any behavioral impact
- any manual verification performed
- screenshots if the UI changed materially

## Security issues

Please do **not** open a public issue for a sensitive security problem.

Instead, follow the reporting guidance in [SECURITY.md](./SECURITY.md).

## License

By contributing to this repository, you agree that your contributions will be licensed under the project's [MIT License](./LICENSE).

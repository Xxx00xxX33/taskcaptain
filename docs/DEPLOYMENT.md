# Deployment

This document covers practical deployment for TaskCaptain.

## 1. Intended deployment model

TaskCaptain is designed first for local, trusted environments.

Recommended targets:

- local Linux workstation
- WSL2 development environment
- private workstation or home-lab host behind access controls

It is **not** a hardened public web application by default.

---

## 2. Requirements

- Linux / WSL2 recommended
- Python 3.10+
- `bash`
- `ss`
- `acpx` on PATH, or `ACPX_BIN` set explicitly

---

## 3. Quick start

```bash
git clone https://github.com/LongWeihan/taskcaptain.git
cd taskcaptain
chmod +x run.sh restart.sh
./run.sh
```

Open:

```text
http://127.0.0.1:8765
```

---

## 4. Environment configuration

TaskCaptain reads its runtime defaults from environment variables.

### Supported variables

```bash
PRODUCTS_UI_HOST=127.0.0.1
PRODUCTS_UI_PORT=8765
PRODUCTS_UI_DEFAULT_LANG=zh
PRODUCTS_UI_DEFAULT_OPENAI_BASE_URL=http://127.0.0.1:8317/v1
PRODUCTS_UI_DEFAULT_PRODUCT_FOLDER=./workspace
PRODUCTS_UI_PROXY=
PRODUCTS_UI_NO_PROXY=127.0.0.1,localhost,::1
ACPX_BIN=/absolute/path/to/acpx
```

### Example

```bash
export PRODUCTS_UI_HOST=127.0.0.1
export PRODUCTS_UI_PORT=8877
export PRODUCTS_UI_DEFAULT_LANG=en
export PRODUCTS_UI_DEFAULT_OPENAI_BASE_URL=http://127.0.0.1:8317/v1
export PRODUCTS_UI_DEFAULT_PRODUCT_FOLDER="$PWD/workspace"
export ACPX_BIN=/absolute/path/to/acpx
./run.sh
```

### Using `.env`

```bash
cp .env.example .env
set -a
source .env
set +a
./run.sh
```

---

## 5. Runtime scripts

### `run.sh`

`run.sh` will:

- create required local directories
- detect whether the configured port is already in use
- avoid starting a duplicate instance
- start the server in the background when the port is free
- write logs to `logs/server.log`

### `restart.sh`

`restart.sh` will:

- stop the currently running process on the configured port
- wait for the port to be released
- force-kill lingering processes if needed
- clear the current server log
- start a fresh instance through `run.sh`

---

## 6. Reverse proxy deployment

If you need access beyond localhost, place TaskCaptain behind a reverse proxy such as:

- Nginx
- Caddy
- Traefik

At minimum, add:

- authentication
- HTTPS
- IP restrictions where possible

Also review [../SECURITY.md](../SECURITY.md) before exposing the service.

---

## 7. Operational notes

- Keep the writable workspace on a filesystem you trust.
- Protect `.env` and any local credentials.
- Prefer dedicated local accounts or isolated environments when running automation.
- Review logs periodically if the system is supervising long-running tasks.

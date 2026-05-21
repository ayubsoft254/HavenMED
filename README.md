# HavenMED
``` A comprehensive healthcare management system designed to streamline patient care, healthcare professional collaboration, and institutional operations. ```

# Features:

## Production Docker Deployment (Linux + External Nginx)

This repository now includes production deployment files designed for:
- Linux server hosting
- Dockerized Django/Gunicorn app
- External host-level Nginx (not containerized)
- Coexistence with other Nginx sites/vhosts on the same server

### Production files
- `docker-compose.prod.yml`: app-only production compose stack
- `Makefile`: operational commands for build/run/migrations/logs
- `nginx/havenmed.external.conf`: host Nginx vhost template

### 1. Prepare environment

```bash
cp .env.example .env
```

Update `.env` values, especially:
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `APP_PORT`
- `HOST_DATA_DIR`, `HOST_MEDIA_DIR`, `HOST_STATIC_DIR`

### 2. Create persistent directories

```bash
make init
```

### 3. Build and start app

```bash
make build
make up
```

The app listens on `127.0.0.1:${APP_PORT}` (default `127.0.0.1:18000`) so it is only reachable through Nginx.

### 4. Configure external Nginx

Copy `nginx/havenmed.external.conf` to your server's Nginx sites directory and update:
- `server_name`
- optional TLS config

Then enable and test:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

This vhost does not use `default_server`, so it can run alongside other existing Nginx configs.

### 5. Useful operations

```bash
make logs
make ps
make migrate
make collectstatic
make createsuperuser
make restart
make down
```
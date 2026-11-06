# Planetarium API

REST API for managing astronomy shows, show themes, planetarium domes, sessions, reservations and seats. Built with Django REST Framework.

## Features

- JWT registration, access and refresh tokens.
- Browse shows, themes, domes and sessions without signing in; filter and search listings.
- Authenticated users can create and view their reservations. Staff can view all reservations.
- Seat validation checks dome dimensions, duplicate bookings and future session times.
- Session availability and dome capacity are returned by the API.
- Django admin and interactive Swagger documentation.

## Run locally (Windows PowerShell)

Python 3.12+ is recommended. The default database is SQLite; no separate database server is required.

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/api/docs/` for Swagger, `http://127.0.0.1:8000/admin/` for the admin panel, or `http://127.0.0.1:8000/api/` for the API root.

## Docker

Docker Desktop and Docker Compose are required.

```powershell
docker compose up --build
```

The service will be available at `http://localhost:8000`. The SQLite database is persisted in the `planetarium_data` volume. Create an admin account inside the running container with:

```powershell
docker compose exec api python manage.py createsuperuser
```

The published image is available on Docker Hub:

```powershell
docker pull mriinyk/api-service-for-a-planetarium:latest
docker run --rm -p 8000:8000 `
  -e DJANGO_SECRET_KEY=change-this-secret `
  -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 `
  -e DJANGO_DB_PATH=/app/data/db.sqlite3 `
  -v planetarium_data:/app/data `
  mriinyk/api-service-for-a-planetarium:latest
```

The container applies Django migrations at startup. Its SQLite database is stored in the `planetarium_data` volume.

## Authentication

1. `POST /api/auth/register/` with `{"username":"viewer","email":"viewer@example.com","password":"strong-password"}`.
2. `POST /api/auth/token/` with username and password to receive `access` and `refresh` tokens.
3. Send `Authorization: Bearer <access>` on protected requests. Refresh an access token at `POST /api/auth/token/refresh/`.

## API endpoints

| Resource | Endpoints |
| --- | --- |
| Themes | `/api/themes/` |
| Astronomy shows | `/api/astronomy-shows/` |
| Domes | `/api/domes/` |
| Sessions | `/api/sessions/` |
| Reservations | `/api/reservations/` |
| Schema / Swagger | `/api/schema/`, `/api/docs/` |

Use `?search=...` for show search, `?themes=<id>` for show filtering, and `?astronomy_show=<id>`, `?planetarium_dome=<id>`, or `?ordering=show_time` for sessions. Browsing is public; catalog changes require a staff account.

Create a reservation with a list of tickets:

```json
{
  "tickets": [
    {"row": 2, "seat": 4, "show_session": 1},
    {"row": 2, "seat": 5, "show_session": 1}
  ]
}
```

## Configuration

Copy `.env.example` to `.env` for local settings. `DJANGO_SECRET_KEY` must be replaced with a private random value before deployment. Set `DJANGO_DEBUG=0` and configure `DJANGO_ALLOWED_HOSTS` outside development.

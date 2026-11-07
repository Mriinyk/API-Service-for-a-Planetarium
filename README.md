# Planetarium API

REST API for managing astronomy shows, themes, planetarium domes, sessions, reservations and seats, built with Django REST Framework.

## Features

- JWT registration and access/refresh tokens.
- Public, paginated show, theme, dome and session listings with search, filters and ordering.
- Staff-only catalogue management; authenticated reservations are private to their owner (staff can inspect all reservations).
- Seat bounds, future-session, duplicate-seat and duplicate-in-reservation validation.
- Atomic reservation creation with database uniqueness protection against simultaneous booking conflicts.
- Dome capacity and live session availability in API responses.
- Django admin and interactive Swagger documentation.

## Run locally

Python 3.12+ is recommended. SQLite is the default database, so no database server is needed.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API is at `http://127.0.0.1:8000/api/`, Swagger at `http://127.0.0.1:8000/api/docs/`, and admin at `http://127.0.0.1:8000/admin/`.

For local overrides, create `.env` with `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, and `DJANGO_ALLOWED_HOSTS`. The development defaults are suitable only for local use.

## Docker

Install Docker Desktop (Windows/macOS) or Docker Engine and the Compose plugin (Linux), then run:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`. SQLite data is persisted in the `planetarium_data` volume. In another terminal, create an admin account:

```bash
docker compose exec api python manage.py createsuperuser
```

To run the published image directly:

```bash
docker pull mriinyk/api-service-for-a-planetarium:latest
docker run --rm -p 8000:8000 \
  -e DJANGO_SECRET_KEY=change-this-secret \
  -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
  -e DJANGO_DB_PATH=/app/data/db.sqlite3 \
  -v planetarium_data:/app/data \
  mriinyk/api-service-for-a-planetarium:latest
```

The container applies migrations when it starts.

## Authentication and booking

1. Register with `POST /api/auth/register/`, for example:
   `{"username":"viewer","email":"viewer@example.com","password":"a-strong-password"}`.
2. Get JWT tokens from `POST /api/auth/token/` using username and password.
3. Send `Authorization: Bearer <access>` on protected requests; refresh at `POST /api/auth/token/refresh/`.
4. Create a reservation with `POST /api/reservations/`:

```json
{
  "tickets": [
    {"row": 2, "seat": 4, "show_session": 1},
    {"row": 2, "seat": 5, "show_session": 1}
  ]
}
```

A reservation must contain at least one ticket, all tickets must belong to one future session, and each seat can be booked only once for that session.

## API endpoints

| Resource | Endpoints |
| --- | --- |
| Registration / JWT | `/api/auth/register/`, `/api/auth/token/`, `/api/auth/token/refresh/` |
| Themes | `/api/themes/` |
| Astronomy shows | `/api/astronomy-shows/` |
| Domes | `/api/domes/` |
| Sessions | `/api/sessions/` |
| Reservations | `/api/reservations/` |
| Schema / Swagger | `/api/schema/`, `/api/docs/` |

Results are paginated (20 per page). Use `?search=...` on astronomy shows, `?themes=<id>` to filter shows, and `?astronomy_show=<id>`, `?planetarium_dome=<id>`, `?ordering=show_time`, or `?page=2` for sessions.

## Tests

```bash
python manage.py test service_for_a_planetarium
```

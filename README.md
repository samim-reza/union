# Union Ledger (Django + PostgreSQL)

A web app for a small friends union to manage deposits, borrowing requests, voting, and historical records.

## Features

- Admin-only user creation from in-app panel
- Login for all users
- Deposit money with timestamp and member identity
- Borrow/loan request submission
- Email notification to all members when a new loan request is created
- Member voting on loan requests (approve/reject)
- Automatic loan status updates based on majority vote
- Common portal with total balance and contribution percentages
- Personal portal with member-specific balance and history
- Action history timeline (who did what)
- Pagination for deposits, loans, and activity logs
- Responsive modern UI

## Local Setup

1. Create and activate virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and update values.
4. Run migrations:

```bash
python manage.py migrate
```

5. Create a superuser:

```bash
python manage.py createsuperuser
```

6. Run server:

```bash
python manage.py runserver
```

## PostgreSQL

Set `DATABASE_URL` in your `.env` using this format:

```bash
postgresql://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
```

Neon connection strings usually include pooling and SSL query params. Use the exact value provided in your Neon dashboard.

## Render Deployment

1. Create a PostgreSQL project/database in Neon.
2. Copy Neon connection string and keep `sslmode=require` in it.
3. In Render, create a new Blueprint/Web service from this repository.
4. In Render Environment Variables, set:
	- `DATABASE_URL` = your Neon connection string
	- `DJANGO_SECRET_KEY` = long random string
	- `DEBUG` = `False`
	- `ALLOWED_HOSTS` = `.onrender.com`
	- `CSRF_TRUSTED_ORIGINS` = `https://<your-render-app>.onrender.com`
5. Optional email variables for notifications:
	- `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`
6. Deploy. Migrations and static collection run during build as configured in `render.yaml`.

## Important Notes

- Users can only be created by staff/superuser from the app page (`/users/create/`) or Django admin.
- For production, set a strong `DJANGO_SECRET_KEY` and keep `DEBUG=False`.

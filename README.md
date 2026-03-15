# Union Ledger (Django + PostgreSQL)

A web app for a small friends union to manage deposits, loans, repayments, investments, approvals, and activity history.

## Features

- Role-gated admin portal (`samim` and `arafat`) for member management and cleanup actions
- User profile completion flow (first name, email, date of birth) before normal app use
- Deposit submission with approval voting and status tracking
- Loan request submission with member voting and automatic status updates
- Loan repayment submission with approval workflow
- Investment decision module:
	- Create/list/detail pages
	- Voting (approve/reject)
	- Automatic status updates by majority
- Unified Decisions page for pending:
	- Deposits
	- Loans
	- Repayments
	- Investments
- Decisions notification badge in top nav:
	- hidden when 0
	- shows count for 1-10
	- shows `10+` above 10
- Activity history timeline with admin delete actions
- Responsive UI across desktop/mobile

## Tech Stack

- Django 5.x
- PostgreSQL (Neon)
- Gunicorn
- WhiteNoise static serving
- Optional SMTP email notifications

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy env template and configure values:

```bash
cp .env.example .env
```

4. Run migrations:

```bash
python manage.py migrate
```

5. (Optional) Create a Django superuser:

```bash
python manage.py createsuperuser
```

6. Start the app:

```bash
python manage.py runserver
```

## Environment Variables

See `.env.example`.

Required in production:

- `DJANGO_SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`

Optional for email notifications:

- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`
- `EMAIL_TIMEOUT`

## Neon PostgreSQL

Set `DATABASE_URL` in `.env`:

```bash
postgresql://USER:PASSWORD@HOST.neon.tech/DBNAME?sslmode=require
```

Use the exact pooled/direct connection string from Neon dashboard.

## Render Deployment

The repository includes `render.yaml`.

Current build/start settings:

- Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
- Start: `gunicorn union_project.wsgi:application --workers 1 --threads 2 --timeout 120`

Set Render env vars:

- `DATABASE_URL` (Neon)
- `DJANGO_SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS=.onrender.com`
- `CSRF_TRUSTED_ORIGINS=https://<your-app>.onrender.com`

## Main Routes

- `/` dashboard
- `/my/` my portal
- `/deposits/` deposits
- `/loans/` loans
- `/investments/` investments
- `/decisions/` pending approvals
- `/history/` activity log
- `/admin/` custom admin portal

## Notes

- User creation in app is restricted to allowed admin users.
- Keep `DEBUG=False` in production.
- Rotate default/shared passwords after initial data seeding.

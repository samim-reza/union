import os
import django
import sys
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "union_project.settings")
django.setup()

from django.contrib.auth.models import User
from core.models import Deposit, LoanRequest, ActivityLog, LoanVote

def run():
    print("Clearing old data (except superuser)...")
    Deposit.objects.all().delete()
    LoanRequest.objects.all().delete()
    ActivityLog.objects.all().delete()
    # Delete users except superusers
    User.objects.filter(is_superuser=False).delete()

    users_data = {
        "rumman": ("Rumman", "Islam", 6000),
        "sifat": ("Nur E Alom", "Sifat", 5000),
        "nahian": ("Al", "Nahian", 2500),
        "reza": ("Kazi", "Reza", 3000),
        "tahsin": ("Tahsin", "Ahmed", 2500),
        "razeen": ("Razeen", "Faysal", 2500),
        "arafat": ("Arafat Hossen", "Kazi", 6000),
        "fauzia": ("Fauzia", "", 6000),
        "galib": ("Galib", "Ahsan", 500),
        "samim": ("Samim", "Reza", 2000), # This might be the current superuser?
        "foysal": ("Foysal Ahmed", "Akas", 1500),
    }

    user_objs = {}
    print("Creating users and their total deposits...")
    for username, (first, last, total_deposit) in users_data.items():
        user, created = User.objects.get_or_create(username=username, defaults={
            "first_name": first, "last_name": last, "email": f"{username}@test.com"
        })
        if created:
            user.set_password("password123")
            user.save()
        user_objs[username] = user

        if total_deposit > 0:
            Deposit.objects.create(
                user=user,
                amount=Decimal(str(total_deposit)),
                note="Aggregated initial deposit from historic records"
            )

    print("Creating loan records...")
    loans_data = [
        ("rumman", 1500, "Historical Loan (Received 06.30.25)"),
        ("reza", 5000, "Historical Loan (Received 08.25.25)"),
        ("sifat", 3000, "Historical Loan (Received 09.16.22)"),
        ("tahsin", 5000, "Historical Loan (Received 10.17.25)"),
        ("rumman", 5000, "Historical Loan (Received unknown)"),
        ("reza", 1000, "Historical Loan (Received 10.13.25)"),
        ("razeen", 3000, "Historical Loan (Received 16/11/25)"),
        ("arafat", 3000, "Historical Loan (Received 10/11/25)"),
        ("razeen", 1000, "Historical Loan (Received 16/11/25)"),
        ("arafat", 3000, "Historical Loan (Received 11/4/25)"),
        ("tahsin", 2000, "Historical Loan (Received 03/13/26)"),
        ("reza", 1000, "Historical Loan (Received 11/22/25)"),
        ("nahian", 2500, "Historical Loan (Received 11/23/25)"),
        ("razeen", 2000, "Historical Loan (Received 1/10/26)"),
        ("sifat", 1000, "Historical Loan (Received 3/1/26)"),
        ("arafat", 200, "Historical Loan (Received 2/14/26)"),
    ]

    for username, amount, note in loans_data:
        usr = user_objs[username]
        LoanRequest.objects.create(
            applicant=usr,
            amount=Decimal(str(amount)),
            purpose=note,
            status=LoanRequest.Status.APPROVED # Marking as approved since they were given
        )

    print("Data seeded successfully!")

if __name__ == "__main__":
    run()

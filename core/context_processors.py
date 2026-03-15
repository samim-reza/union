from .models import Deposit, InvestmentDecision, LoanRepayment, LoanRequest


def pending_decisions_count(request):
    if not request.user.is_authenticated:
        return {'pending_decisions_badge': ''}

    total_pending = (
        Deposit.objects.filter(status=Deposit.Status.PENDING).count()
        + LoanRequest.objects.filter(status=LoanRequest.Status.PENDING).count()
        + LoanRepayment.objects.filter(status=LoanRepayment.Status.PENDING).count()
        + InvestmentDecision.objects.filter(status=InvestmentDecision.Status.PENDING).count()
    )

    if total_pending <= 0:
        badge = ''
    elif total_pending > 10:
        badge = '10+'
    else:
        badge = str(total_pending)

    return {'pending_decisions_badge': badge}

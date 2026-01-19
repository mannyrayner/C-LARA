from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from .models import UserProfile
from .forms import AddCreditForm, ConfirmTransferForm
from .utils import get_user_config
from .utils import send_mail_or_print_trace
from .clara_utils import get_config
from decimal import Decimal
import logging
import uuid

config = get_config()
logger = logging.getLogger(__name__)

# Credit balance for money spent on API calls

@login_required
def credit_balance(request):
    credit_balance = request.user.userprofile.credit

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/credit_balance.html', {'credit_balance': credit_balance, 'clara_version': clara_version})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def credit_balances_admin(request):
    qs = (
        UserProfile.objects
        .select_related('user')
        .order_by('credit', 'user__username')
    )

    negatives = qs.filter(credit__lt=0)
    stats = qs.aggregate(
        total=Sum('credit'),
        n=Count('id'),
    )

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/credit_balances_admin.html', {
        'profiles': qs,
        'negative_profiles': negatives,
        'stats': stats,
        'clara_version': clara_version,
    })

# Add credit to account
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def add_credit(request):
    if request.method == 'POST':
        form = AddCreditForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            credit = form.cleaned_data['credit']
            user.userprofile.credit += credit
            user.userprofile.save()
            messages.success(request, "Credit added successfully")
    else:
        form = AddCreditForm()

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/add_credit.html', {'form': form, 'clara_version': clara_version})

# Transfer credit to another account
@login_required
def transfer_credit(request):
    if request.method == 'POST':
        form = AddCreditForm(request.POST)
        if form.is_valid():
            recipient_username = form.cleaned_data['user']
            amount = form.cleaned_data['credit']

            # Check if recipient exists
            try:
                recipient = User.objects.get(username=recipient_username)
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
                return render(request, 'clara_app/transfer_credit.html', {'form': form})

            # Check if user has enough credit
            if request.user.userprofile.credit < amount:
                messages.error(request, 'Insufficient credit.')
                return render(request, 'clara_app/transfer_credit.html', {'form': form})

            # Generate a unique confirmation code
            confirmation_code = str(uuid.uuid4())

            # Store the transfer details and confirmation code in the session
            request.session['credit_transfer'] = {
                'recipient_id': recipient.id,
                'amount': str(amount),  # Convert Decimal to string for session storage
                'confirmation_code': confirmation_code,
            }

            # Send confirmation email
            recipient_email = request.user.email
            send_mail_or_print_trace(
                'Confirm Credit Transfer',
                f'Please confirm your credit transfer of {amount} to {recipient.username} using this code: {confirmation_code}',
                'clara-no-reply@unisa.edu.au',
                [ recipient_email ],
                fail_silently=False,
            )

            anonymised_email = recipient_email[0:3] + '*' * ( len(recipient_email) - 10 ) + recipient_email[-7:]
            messages.info(request, f'A confirmation email has been sent to {anonymised_email}. Please check your email to complete the transfer.')
            return redirect('confirm_transfer')
    else:
        form = AddCreditForm()

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/transfer_credit.html', {'form': form, 'clara_version': clara_version})

@login_required
def confirm_transfer(request):
    if request.method == 'POST':
        form = ConfirmTransferForm(request.POST)
        if form.is_valid():
            confirmation_code = form.cleaned_data['confirmation_code']

            # Retrieve transfer details from the session
            transfer_details = request.session.get('credit_transfer')
            if not transfer_details:
                messages.error(request, 'Transfer details not found.')
                return redirect('transfer_credit')

            # Check if the confirmation code matches
            if confirmation_code != transfer_details['confirmation_code']:
                messages.error(request, 'Invalid confirmation code.')
                return render(request, 'confirm_transfer.html', {'form': form})

            # Complete the transfer
            recipient = User.objects.get(id=transfer_details['recipient_id'])
            amount = Decimal(transfer_details['amount'])
            request.user.userprofile.credit -= amount
            request.user.userprofile.save()
            recipient.userprofile.credit += amount
            recipient.userprofile.save()

            # Clear the transfer details from the session
            del request.session['credit_transfer']

            messages.success(request, f'Credit transfer of USD {amount} to {recipient.username} completed successfully.')
            return redirect('transfer_credit')
    else:
        form = ConfirmTransferForm()

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/confirm_transfer.html', {'form': form, 'clara_version': clara_version})

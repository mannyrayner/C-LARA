from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from .models import FundingRequest
from .forms import FundingRequestForm, FundingRequestSearchForm, ApproveFundingRequestFormSet
from .forms import ConfirmTransferForm
from .utils import send_mail_or_print_trace
from .clara_utils import get_config

from .constants import SUPPORTED_LANGUAGES_AND_OTHER
from decimal import Decimal
import logging
import uuid

config = get_config()
logger = logging.getLogger(__name__)

@login_required
def funding_request(request):
    if request.method == 'POST':
        form = FundingRequestForm(request.POST)
        if form.is_valid():
            funding_request = form.save(commit=False)
            funding_request.user = request.user
            funding_request.save()
            messages.success(request, 'Your funding request has been submitted.')
            return redirect('profile')  
    else:
        form = FundingRequestForm()

    return render(request, 'clara_app/funding_request.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.userprofile.is_funding_reviewer)
def review_funding_requests(request):
    own_credit_balance = request.user.userprofile.credit
    
    search_form = FundingRequestSearchForm(request.GET or None)
    query = Q()

    if search_form.is_valid():
        language = search_form.cleaned_data.get('language')
        native_or_near_native = search_form.cleaned_data.get('native_or_near_native')
        text_type = search_form.cleaned_data.get('text_type')
        purpose = search_form.cleaned_data.get('purpose')
        status = search_form.cleaned_data.get('status')

        if language and language != '':
            query &= Q(language=language)
        if native_or_near_native and native_or_near_native != '':
            query &= Q(native_or_near_native=native_or_near_native)
        if text_type and text_type != '':
            query &= Q(text_type=text_type)
        if purpose and purpose != '':
            query &= Q(purpose=purpose)
        if status and status != '':
            query &= Q(status=status)
    
    if request.method == 'POST':
        formset = ApproveFundingRequestFormSet(request.POST)
        n_filtered_requests = len(formset)
        #print(f'--- Found {n_filtered_requests} requests')
        transfers = []
        total_amount = 0
        for form in formset:
            if not form.is_valid():
                print(f'--- Invalid form data: {form}')
            else:
                request_id = int(form.cleaned_data.get('id'))
                status = form.cleaned_data.get('status')
                credit_assigned = int(form.cleaned_data.get('credit_assigned')) if form.cleaned_data.get('credit_assigned') else 0.0
                #print(f'--- id: {id}, status: {status}, credit_assigned: {credit_assigned}')
                #if status != 'Submitted' and credit_assigned >= 0.01:
                #    messages.error(request, f'Request {request_id}: not meaningful to fund a request with status "{status}"')
                if status == 'Submitted' and credit_assigned >= 0.01:
                    total_amount += credit_assigned
                    transfers.append({
                        'funding_request_id': request_id,
                        'amount': credit_assigned
                    })
        #print(f'--- total_amount = {total_amount}')
        if total_amount == 0:
            messages.error(request, 'No requests to approve.')
        elif total_amount > request.user.userprofile.credit:
            messages.error(request, 'Insufficient funds for these approvals.')
        else:
            confirmation_code = str(uuid.uuid4())
            request.session['funding_transfers'] = {
                'transfers': transfers,
                'total_amount': total_amount,
                'confirmation_code': confirmation_code,
            }
            # Send an email to the reviewer for confirmation
            recipient_email = request.user.email
            send_mail_or_print_trace('Confirm Funding Approvals',
                                     f'Please confirm your funding approvals totaling USD {total_amount:.2f} using this code: {confirmation_code}',
                                     'clara-no-reply@unisa.edu.au',
                                     [ recipient_email ],
                                     fail_silently=False)
            anonymised_email = recipient_email[0:3] + '*' * ( len(recipient_email) - 10 ) + recipient_email[-7:]
            messages.info(request, f'A confirmation email has been sent to {anonymised_email}. Please check your email to complete the approvals.')
            return redirect('confirm_funding_approvals')            

    else:
        # Populate the formset based on the search criteria etc
        filtered_requests = FundingRequest.objects.filter(query)
        n_filtered_requests = len(filtered_requests)
        initial_data = [{'id': fr.id,
                         'user': fr.user.username,
                         'language_native_or_near_native': f'{dict(SUPPORTED_LANGUAGES_AND_OTHER)[fr.language]}/{"Yes" if fr.native_or_near_native else "No"}',
                         'text_type': dict(FundingRequest.CONTENT_TYPE_CHOICES)[fr.text_type],
                         'purpose': dict(FundingRequest.PURPOSE_CHOICES)[fr.purpose],
                         'other_purpose': fr.other_purpose[:500],
                         'status': dict(FundingRequest.STATUS_CHOICES)[fr.status],
                         'credit_assigned': fr.credit_assigned,
                         }
                        for fr in filtered_requests]
        #print(f'--- initial_data from filtered_requests')
        #pprint.pprint(initial_data)
        formset = ApproveFundingRequestFormSet(initial=initial_data)

    return render(request, 'clara_app/review_funding_requests.html',
                  {'own_credit_balance': own_credit_balance, 'n_filtered_requests': n_filtered_requests,
                   'formset': formset, 'search_form': search_form})

@login_required
@user_passes_test(lambda u: u.userprofile.is_funding_reviewer)
def confirm_funding_approvals(request):
    if request.method == 'POST':
        form = ConfirmTransferForm(request.POST)  
        if form.is_valid():
            confirmation_code = form.cleaned_data['confirmation_code']
            session_data = request.session.get('funding_transfers')

            if not session_data:
                messages.error(request, 'No transfers found.')
            elif not confirmation_code == session_data['confirmation_code']:
                messages.error(request, 'Invalid confirmation code.')
            else:
                for transfer in session_data['transfers']:
                    # Update the funding_request
                    funding_request = FundingRequest.objects.get(id=transfer['funding_request_id'])
                    funding_request.status = 'accepted'
                    funding_request.credit_assigned = Decimal(transfer['amount'])
                    funding_request.decision_made_at = timezone.now()
                    funding_request.funder = request.user
                    funding_request.save()
                    # Perform the credit transfer
                    #print(f'Old requester credit ({funding_request.user.username}): {funding_request.user.userprofile.credit}')
                    #print(f'Old funder credit ({request.user.username}): {request.user.userprofile.credit}')
                    if funding_request.user != request.user:
                        funding_request.user.userprofile.credit += Decimal(transfer['amount'])
                        funding_request.user.userprofile.save()
                        request.user.userprofile.credit -= Decimal(transfer['amount'])
                        request.user.userprofile.save()
                    #print(f'New requester credit ({funding_request.user.username}): {funding_request.user.userprofile.credit}')
                    #print(f'New funder credit ({request.user.username}): {request.user.userprofile.credit}')
                    # Send an email to the requester to let them know the request has been approved
                    send_mail_or_print_trace('Your C-LARA funding request has been approved',
                                             f'Your C-LARA funding request was approved, and USD {transfer["amount"]:.2f} has been added to your account balance.',
                                             'clara-no-reply@unisa.edu.au',
                                             [ funding_request.user.email ],
                                             fail_silently=False)
                del request.session['funding_transfers']
                messages.success(request, 'Funding approvals confirmed and funds transferred.')
                return redirect('review_funding_requests')
    # GET request            
    else:
        form = ConfirmTransferForm()

    return render(request, 'clara_app/confirm_funding_approvals.html', {'form': form})

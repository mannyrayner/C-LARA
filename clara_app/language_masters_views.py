from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction

from .models import LanguageMaster, LocalisationBundle, BundleItem
from .forms import AssignLanguageMasterForm
from .utils import get_user_config, user_can_translate
from .clara_utils import get_config
import logging

config = get_config()
logger = logging.getLogger(__name__)

# Manage users declared as 'language masters', adding or withdrawing the 'language master' privilege   
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def manage_language_masters(request):
    language_masters = LanguageMaster.objects.all()
    if request.method == 'POST':
        form = AssignLanguageMasterForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            language = form.cleaned_data['language']
            LanguageMaster.objects.get_or_create(user=user, language=language)
            return redirect('manage_language_masters')
    else:
        form = AssignLanguageMasterForm()

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/manage_language_masters.html', {
        'language_masters': language_masters,
        'form': form, 'clara_version': clara_version,
    })

# Remove someone as a language master, asking for confirmation first
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def remove_language_master(request, pk):
    language_master = get_object_or_404(LanguageMaster, pk=pk)
    if request.method == 'POST':
        language_master.delete()
        return redirect('manage_language_masters')
    else:

        clara_version = get_user_config(request.user)['clara_version']
        
        return render(request, 'clara_app/remove_language_master_confirm.html', {'language_master': language_master, 'clara_version': clara_version})

##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def post_localisation_bundle(request):
##    if request.method == 'POST':
##        name = request.POST['name'].strip()
##        lines = [l.strip() for l in request.POST['strings'].splitlines() if l.strip()]
##        # Lines come as  key<TAB>English text
##        bundle, _ = LocalisationBundle.objects.get_or_create(name=name)
##        for ln in lines:
##            key, src = ln.split('\t', 1)
##            BundleItem.objects.update_or_create(
##                bundle=bundle, key=key, defaults={'src': src})
##        messages.success(request, f"Bundle '{name}' uploaded with {len(lines)} items.")
##        return redirect('bundle_list')
##    return render(request, 'clara_app/post_bundle.html')

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def post_localisation_bundle(request):
    # names for the <select>
    existing_names = list(
        LocalisationBundle.objects.order_by('name').values_list('name', flat=True)
    )

    # --- Handle "Load existing" action ---------------------------------
    if request.method == 'POST' and 'load' in request.POST:
        sel = request.POST.get('existing_name', '').strip()
        initial = {'name': '', 'strings': ''}

        if sel:
            try:
                b = LocalisationBundle.objects.get(name=sel)
                lines = '\n'.join(
                    f"{bi.key}\t{bi.src}"
                    for bi in b.bundleitem_set.order_by('key')
                )
                initial = {'name': b.name, 'strings': lines}
            except LocalisationBundle.DoesNotExist:
                messages.error(request, f"Bundle '{sel}' does not exist.")

        return render(request, 'clara_app/post_bundle.html', {
            'existing_names': existing_names,
            'initial': initial,
        })

    # --- Handle "Save bundle" action -----------------------------------
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        strings = request.POST.get('strings') or ''

        if not name:
            messages.error(request, "Please provide a bundle name.")
            return render(request, 'clara_app/post_bundle.html', {
                'existing_names': existing_names,
                'initial': {'name': name, 'strings': strings},
            })
        if not strings.strip():
            messages.error(request, "Please paste at least one key<TAB>text line.")
            return render(request, 'clara_app/post_bundle.html', {
                'existing_names': existing_names,
                'initial': {'name': name, 'strings': strings},
            })

        # Parse lines: key<TAB>English text
        parsed = []
        for i, raw in enumerate(strings.splitlines(), 1):
            if not raw.strip():
                continue
            if '\t' not in raw:
                messages.error(request, f"Line {i} is missing a TAB: {raw[:80]}")
                return render(request, 'clara_app/post_bundle.html', {
                    'existing_names': existing_names,
                    'initial': {'name': name, 'strings': strings},
                })
            key, src = raw.split('\t', 1)
            key, src = key.strip(), src.strip()
            if not key:
                messages.error(request, f"Line {i} has an empty key.")
                return render(request, 'clara_app/post_bundle.html', {
                    'existing_names': existing_names,
                    'initial': {'name': name, 'strings': strings},
                })
            parsed.append((key, src))

        with transaction.atomic():
            bundle, _ = LocalisationBundle.objects.get_or_create(name=name)
            for key, src in parsed:
                BundleItem.objects.update_or_create(
                    bundle=bundle, key=key, defaults={'src': src}
                )

        messages.success(request, f"Bundle '{name}' saved with {len(parsed)} items.")
        return redirect('bundle_list')

    # --- GET ------------------------------------------------------------
    return render(request, 'clara_app/post_bundle.html', {
        'existing_names': existing_names,
        'initial': {'name': '', 'strings': ''},
    })

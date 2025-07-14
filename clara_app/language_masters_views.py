from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

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

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def post_localisation_bundle(request):
    if request.method == 'POST':
        name = request.POST['name'].strip()
        lines = [l.strip() for l in request.POST['strings'].splitlines() if l.strip()]
        # Lines come as  key<TAB>English text
        bundle, _ = LocalisationBundle.objects.get_or_create(name=name)
        for ln in lines:
            key, src = ln.split('\t', 1)
            BundleItem.objects.update_or_create(
                bundle=bundle, key=key, defaults={'src': src})
        messages.success(request, f"Bundle '{name}' uploaded with {len(lines)} items.")
        return redirect('bundle_list')
    return render(request, 'clara_app/post_bundle.html')



from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

from .models import UserConfiguration

from .forms import UserConfigForm
from .utils import get_user_config
from .clara_utils import get_config
import logging

config = get_config()
logger = logging.getLogger(__name__)

@login_required
def user_config(request):
    # In the legacy case, we won't have a UserConfiguration object yet, so create one if necessary
    user_config, created = UserConfiguration.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserConfigForm(request.POST, instance=user_config)
        if form.is_valid():
            #open_ai_api_key = form.cleaned_data['open_ai_api_key']
            #print(f'open_ai_api_key = {open_ai_api_key}')
            form.save()
            messages.success(request, f'Configuration information has been updated')
            return redirect('user_config')
    else:
        form = UserConfigForm(instance=user_config)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/user_config.html', {'form': form, 'clara_version': clara_version})


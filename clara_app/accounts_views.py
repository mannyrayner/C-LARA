# accounts_views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import UserProfile, UserConfiguration
from .forms import RegistrationForm
from .utils import get_user_config

# Django’s built-in auth views are used for login/logout, so we typically
# only need explicit views for register, redirect_login, profile, etc.

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.email = form.cleaned_data.get('email')
            user.save()
            
            # Create UserProfile and UserConfiguration
            UserProfile.objects.create(user=user)
            UserConfiguration.objects.create(user=user)

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'clara_app/register.html', {'form': form})

@login_required
def profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    clara_version = get_user_config(request.user)['clara_version']
    
    return render(
        request,
        'clara_app/profile.html',
        {
            'profile': profile,
            'email': request.user.email,
            'clara_version': clara_version
        }
    )

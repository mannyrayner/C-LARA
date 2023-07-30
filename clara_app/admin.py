from django.contrib import admin
# Temporarily remove User
#from .models import User
from django.contrib.auth.models import User

admin.site.register(User)




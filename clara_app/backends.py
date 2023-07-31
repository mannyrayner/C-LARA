from django.contrib.auth.backends import ModelBackend
# Remove custom User
#from clara_app.models import User
from django.contrib.auth.models import User

class CustomUserModelBackend(ModelBackend):
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

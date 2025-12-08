import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_attendance.settings')
django.setup()

from django.contrib.auth.models import User

def reset_password():
    username = 'Hima@7079'
    password = '12345678'
    email = 'teacher@example.com'
    
    try:
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.save()
            print(f"Successfully reset password for user '{username}' to '{password}'")
        else:
            User.objects.create_superuser(username, email, password)
            print(f"Created new superuser '{username}' with password '{password}'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    reset_password()

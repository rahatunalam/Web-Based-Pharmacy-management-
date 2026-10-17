from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or reset the Peoples Pharma admin login."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", required=True)
        parser.add_argument("--email", default="")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        password = options["password"]
        email    = options["email"]

        user, created = User.objects.update_or_create(
            username=username,
            defaults={
                "email":        email,
                "is_staff":     True,
                "is_superuser": True,
                "is_active":    True,
            },
        )
        user.password = make_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} admin '{username}' successfully."
            )
        )
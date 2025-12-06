from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    # dependency should point to the last existing migration in pwd/migrations
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pwd', '0003_pwdprofile_fingerprint_slot'),
    ]

    operations = [
        migrations.AddField(
            model_name='pwdprofile',
            name='account',
            field=models.OneToOneField(
                to=settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                blank=True,
                related_name='pwd_account',
            ),
        ),
    ]
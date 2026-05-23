from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_storerequest_storerequestitem_storestaff_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('notif_type', models.CharField(choices=[
                    ('status_update', 'Status Updated'),
                    ('hod_action', 'HOD Action'),
                    ('store_action', 'Store Action'),
                    ('fulfillment', 'Fulfilment Update'),
                    ('general', 'General'),
                ], default='general', max_length=30)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('recipient', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='store_notifications',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('store_request', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='notifications',
                    to='core.storerequest',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]

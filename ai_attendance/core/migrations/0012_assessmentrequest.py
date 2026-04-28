from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_alter_attendancerecord_time"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AssessmentRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(max_length=100)),
                ("assessment_type", models.CharField(
                    choices=[
                        ("question_paper", "Question Paper"),
                        ("assignment", "Assignment"),
                        ("quiz", "Quiz / MCQ Set"),
                        ("lab_work", "Lab Work / Practical"),
                        ("project", "Project Topic"),
                        ("other", "Other"),
                    ],
                    default="question_paper",
                    max_length=30,
                )),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("year", models.CharField(blank=True, max_length=10)),
                ("section", models.CharField(blank=True, max_length=10)),
                ("status", models.CharField(
                    choices=[
                        ("Pending", "Pending"),
                        ("Approved", "Approved"),
                        ("Rejected", "Rejected"),
                    ],
                    default="Pending",
                    max_length=20,
                )),
                ("admin_remarks", models.TextField(blank=True, null=True, help_text="Admin response or remarks")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("teacher", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="assessment_requests",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

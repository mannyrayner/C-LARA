# Generated by Django 4.2.1 on 2024-03-16 03:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clara_app', '0064_acknowledgements_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_questionnaire_reviewer',
            field=models.BooleanField(default=False),
        ),
    ]

# Generated by Django 4.2.1 on 2024-03-13 00:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clara_app', '0063_alter_fundingrequest_other_purpose_acknowledgements'),
    ]

    operations = [
        migrations.AddField(
            model_name='acknowledgements',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='acknowledgements',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]

# Generated by Django 4.2.1 on 2023-05-26 05:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clara_app', '0007_content_project_alter_content_external_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='content',
            name='project',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='clara_app.claraproject'),
        ),
    ]

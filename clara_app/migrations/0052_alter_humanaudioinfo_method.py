# Generated by Django 4.2.1 on 2024-02-23 10:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clara_app', '0051_claraproject_simple_clara_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='humanaudioinfo',
            name='method',
            field=models.CharField(choices=[('tts_only', 'TTS only'), ('upload', 'Upload'), ('manual_align', 'Manual Align')], max_length=20),
        ),
    ]
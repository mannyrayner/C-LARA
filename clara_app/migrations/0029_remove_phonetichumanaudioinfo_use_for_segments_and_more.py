# Generated by Django 4.2.1 on 2023-11-29 08:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clara_app', '0028_phonetichumanaudioinfo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='phonetichumanaudioinfo',
            name='use_for_segments',
        ),
        migrations.RemoveField(
            model_name='phonetichumanaudioinfo',
            name='use_for_words',
        ),
        migrations.AddField(
            model_name='phonetichumanaudioinfo',
            name='method',
            field=models.CharField(choices=[('upload_individual', 'Upload single files'), ('upload_zipfile', 'Upload zipfile with metadata')], default='upload_individual', max_length=40),
        ),
        migrations.AlterField(
            model_name='humanaudioinfo',
            name='method',
            field=models.CharField(choices=[('upload', 'Upload'), ('record', 'Record'), ('manual_align', 'Manual Align'), ('automatic_align', 'Automatic Align')], max_length=20),
        ),
    ]

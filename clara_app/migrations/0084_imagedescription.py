# Generated by Django 4.2.1 on 2024-06-23 11:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clara_app', '0083_alter_imagemetadata_file_path'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImageDescription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project_id', models.CharField(max_length=255)),
                ('description_variable', models.CharField(max_length=255)),
                ('explanation', models.TextField(help_text='Explanation of the image element.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Image Description',
                'verbose_name_plural': 'Image Descriptions',
                'db_table': 'orm_image_description',
                'unique_together': {('project_id', 'description_variable')},
            },
        ),
    ]

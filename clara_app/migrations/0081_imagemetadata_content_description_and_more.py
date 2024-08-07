# Generated by Django 4.2.1 on 2024-05-21 07:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clara_app', '0080_claraproject_uses_coherent_image_set'),
    ]

    operations = [
        migrations.AddField(
            model_name='imagemetadata',
            name='content_description',
            field=models.TextField(blank=True, default='', help_text='AI-generated description of the image content.'),
        ),
        migrations.AddField(
            model_name='imagemetadata',
            name='style_description',
            field=models.TextField(blank=True, default='', help_text='AI-generated description of the image style.'),
        ),
        migrations.AddField(
            model_name='imagemetadata',
            name='user_prompt',
            field=models.TextField(blank=True, default='', help_text='Most recent user prompt for generating or modifying this image.'),
        ),
    ]

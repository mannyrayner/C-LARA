# Generated by Django 4.2.1 on 2024-11-09 04:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clara_app', '0089_alter_alignedphoneticlexicon_language_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='claraproject',
            name='uses_coherent_image_set_v2',
            field=models.BooleanField(default=False, help_text='Specifies whether the project uses a coherent AI-generated image set (V2).'),
        ),
        migrations.AddField(
            model_name='imagemetadata',
            name='advice',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='imagemetadata',
            name='image_type',
            field=models.CharField(choices=[('style', 'Style'), ('element', 'Element'), ('page', 'Page')], default='page', max_length=20),
        ),
        migrations.AlterField(
            model_name='imagemetadata',
            name='request_type',
            field=models.CharField(choices=[('image-generation', 'Generation'), ('image-understanding', 'Understanding')], default='image-generation', max_length=20),
        ),
        migrations.AlterField(
            model_name='userconfiguration',
            name='gpt_model',
            field=models.CharField(default='gpt-4o', max_length=50),
        ),
    ]

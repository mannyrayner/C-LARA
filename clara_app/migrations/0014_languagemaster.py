# Generated by Django 4.2.1 on 2023-06-22 03:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clara_app', '0013_projectpermissions'),
    ]

    operations = [
        migrations.CreateModel(
            name='LanguageMaster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(choices=[('arabic', 'Arabic'), ('bengali', 'Bengali'), ('bulgarian', 'Bulgarian'), ('chinese', 'Chinese'), ('croatian', 'Croatian'), ('czech', 'Czech'), ('danish', 'Danish'), ('dutch', 'Dutch'), ('english', 'English'), ('faroese', 'Faroese'), ('finnish', 'Finnish'), ('french', 'French'), ('german', 'German'), ('greek', 'Greek'), ('hebrew', 'Hebrew'), ('hindi', 'Hindi'), ('hungarian', 'Hungarian'), ('icelandic', 'Icelandic'), ('italian', 'Italian'), ('japanese', 'Japanese'), ('korean', 'Korean'), ('latin', 'Latin'), ('norwegian', 'Norwegian'), ('old norse', 'Old Norse'), ('polish', 'Polish'), ('portuguese', 'Portuguese'), ('romanian', 'Romanian'), ('russian', 'Russian'), ('serbian', 'Serbian'), ('slovak', 'Slovak'), ('slovenian', 'Slovenian'), ('spanish', 'Spanish'), ('swedish', 'Swedish'), ('thai', 'Thai'), ('turkish', 'Turkish'), ('ukrainian', 'Ukrainian'), ('vietnamese', 'Vietnamese')], max_length=50)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'language')},
            },
        ),
    ]

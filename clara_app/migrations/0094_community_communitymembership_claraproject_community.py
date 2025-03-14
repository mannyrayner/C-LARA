# Generated by Django 4.2.1 on 2024-12-24 03:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clara_app', '0093_archivedimagemetadata_element_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Community',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('language', models.CharField(choices=[('american english', 'American English'), ('ancient egyptian', 'Ancient Egyptian'), ('arabic', 'Arabic'), ('australian english', 'Australian English'), ('barngarla', 'Barngarla'), ('bengali', 'Bengali'), ('bulgarian', 'Bulgarian'), ('cantonese', 'Cantonese'), ('chinese', 'Chinese'), ('croatian', 'Croatian'), ('czech', 'Czech'), ('danish', 'Danish'), ('drehu', 'Drehu'), ('dutch', 'Dutch'), ('english', 'English'), ('esperanto', 'Esperanto'), ('estonian', 'Estonian'), ('faroese', 'Faroese'), ('farsi', 'Farsi'), ('finnish', 'Finnish'), ('french', 'French'), ('german', 'German'), ('greek', 'Greek'), ('hebrew', 'Hebrew'), ('hindi', 'Hindi'), ('hungarian', 'Hungarian'), ('iaai', 'Iaai'), ('icelandic', 'Icelandic'), ('indonesian', 'Indonesian'), ('irish', 'Irish'), ('italian', 'Italian'), ('japanese', 'Japanese'), ('kok kaper', 'Kok Kaper'), ('korean', 'Korean'), ('kunjen', 'Kunjen'), ('latin', 'Latin'), ('malay', 'Malay'), ('mandarin', 'Mandarin'), ('māori', 'Māori'), ('norwegian', 'Norwegian'), ('old norse', 'Old Norse'), ('paicî', 'Paicî'), ('pitjantjatjara', 'Pitjantjatjara'), ('polish', 'Polish'), ('portuguese', 'Portuguese'), ('romanian', 'Romanian'), ('russian', 'Russian'), ('serbian', 'Serbian'), ('slovak', 'Slovak'), ('slovenian', 'Slovenian'), ('spanish', 'Spanish'), ('swedish', 'Swedish'), ('thai', 'Thai'), ('turkish', 'Turkish'), ('ukrainian', 'Ukrainian'), ('vietnamese', 'Vietnamese'), ('welsh', 'Welsh'), ('west greenlandic', 'West Greenlandic'), ('yirr yorront', 'Yirr Yorront')], help_text='Language primarily associated with this community.', max_length=50)),
                ('description', models.TextField(blank=True, default='')),
            ],
        ),
        migrations.CreateModel(
            name='CommunityMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('COORDINATOR', 'Coordinator'), ('MEMBER', 'Member')], default='MEMBER', max_length=20)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='clara_app.community')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='claraproject',
            name='community',
            field=models.ForeignKey(blank=True, help_text='If set, this project belongs to the specified community.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='projects', to='clara_app.community'),
        ),
    ]

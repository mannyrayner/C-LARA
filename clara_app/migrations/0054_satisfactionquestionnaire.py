# Generated by Django 4.2.1 on 2024-02-29 12:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clara_app', '0053_humanaudioinfo_use_context'),
    ]

    operations = [
        migrations.CreateModel(
            name='SatisfactionQuestionnaire',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text_correspondence', models.IntegerField(choices=[(1, 'Strongly disagree'), (2, 'Disagree'), (3, 'Neutral or not applicable'), (4, 'Agree'), (5, 'Strongly agree')], verbose_name='The text C-LARA produced corresponded well to my request')),
                ('language_correctness', models.IntegerField(choices=[(1, 'Strongly disagree'), (2, 'Disagree'), (3, 'Neutral or not applicable'), (4, 'Agree'), (5, 'Strongly agree')], verbose_name='The language in the text was correct')),
                ('text_engagement', models.IntegerField(choices=[(1, 'Strongly disagree'), (2, 'Disagree'), (3, 'Neutral or not applicable'), (4, 'Agree'), (5, 'Strongly agree')], verbose_name='The text was engaging (funny/cute/moving)')),
                ('cultural_appropriateness', models.IntegerField(choices=[(1, 'Strongly disagree'), (2, 'Disagree'), (3, 'Neutral or not applicable'), (4, 'Agree'), (5, 'Strongly agree')], verbose_name='The text was culturally appropriate')),
                ('image_match', models.IntegerField(choices=[(1, 'Strongly disagree'), (2, 'Disagree'), (3, 'Neutral or not applicable'), (4, 'Agree'), (5, 'Strongly agree')], verbose_name='The image(s) matched the text well')),
                ('shared_text', models.IntegerField(choices=[(1, 'Strongly disagree'), (2, 'Disagree'), (3, 'Neutral or not applicable'), (4, 'Agree'), (5, 'Strongly agree')], verbose_name='I liked the text enough that I showed it to some other people')),
                ('functionality_improvement', models.TextField(blank=True, verbose_name="What do you think the most important thing is if we are to improve C-LARA's functionality?")),
                ('design_improvement', models.TextField(blank=True, verbose_name="What do you think the most important thing is if we are to improve C-LARA's design?")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='clara_app.claraproject')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

# Generated by Django 4.2.1 on 2024-01-14 10:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clara_app', '0038_alter_formatpreferences_font_size'),
    ]

    operations = [
        migrations.AddField(
            model_name='humanaudioinfo',
            name='preferred_tts_engine',
            field=models.CharField(choices=[('none', 'None'), ('google', 'Google TTS'), ('openai', 'OpenAI TTS'), ('abair', 'ABAIR')], default='none', max_length=20),
        ),
        migrations.AddField(
            model_name='humanaudioinfo',
            name='preferred_tts_voice',
            field=models.CharField(choices=[('none', 'None'), ('alloy', 'Alloy (OpenAI)'), ('echo', 'Echo (OpenAI)'), ('fable', 'Fable (OpenAI)'), ('onyx', 'Onyx (OpenAI)'), ('nova', 'Nova (OpenAI)'), ('shimmer', 'Shimmer (OpenAI)'), ('ga_UL_anb_nnmnkwii', 'ga_UL_anb_nnmnkwii (ABAIR)'), ('ga_MU_nnc_nnmnkwii', 'ga_MU_nnc_nnmnkwii (ABAIR)'), ('ga_MU_cmg_nnmnkwii', 'ga_MU_cmg_nnmnkwii (ABAIR)')], default='none', max_length=20),
        ),
    ]

# Generated by Django 4.2.1 on 2024-03-25 13:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clara_app', '0068_activity_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='category',
            field=models.CharField(choices=[('human_ai_interaction', 'Analysis of human/AI collaboration'), ('annotation', 'Annotation of texts by AI'), ('classroom', 'Classroom experiments'), ('multimodal_formatting', 'Formatting/behaviour of multimodal texts'), ('languages_covered_by_ai', 'Languages covered by AI'), ('languages_not_covered_by_ai', 'Languages not covered by AI'), ('legacy_content', 'Legacy content'), ('legacy_software', 'Legacy software'), ('phonetic_texts', 'Phonetic texts'), ('refactoring', 'Refactoring software'), ('simple_clara', 'Simple C-LARA'), ('social_network', 'Social network'), ('other', 'Other')], max_length=50),
        ),
    ]
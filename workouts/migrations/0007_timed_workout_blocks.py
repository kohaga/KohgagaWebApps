from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workouts", "0006_alter_exercise_movement_pattern"),
    ]

    operations = [
        migrations.AddField(
            model_name="exercise",
            name="default_duration_seconds",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Default duration for mobility/stretching/time-based exercises.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="workoutsession",
            name="warmup_duration_minutes",
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name="workoutsession",
            name="cooldown_duration_minutes",
            field=models.PositiveSmallIntegerField(default=4),
        ),
        migrations.AddField(
            model_name="workoutsessionexercise",
            name="target_duration_seconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]

from django.db import migrations, models


def set_default_timed_exercise_duration(apps, schema_editor):
    Exercise = apps.get_model("workouts", "Exercise")
    Exercise.objects.filter(
        movement_pattern__in=["mobility", "stretching"],
        default_duration_seconds__isnull=True,
    ).update(default_duration_seconds=60)


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
        migrations.RunPython(
            set_default_timed_exercise_duration,
            migrations.RunPython.noop,
        ),
    ]

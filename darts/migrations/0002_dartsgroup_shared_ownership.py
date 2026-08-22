import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def reset_darts_data(apps, schema_editor):
    Game = apps.get_model("darts", "Game")
    Player = apps.get_model("darts", "Player")
    Game.objects.all().delete()
    Player.objects.all().delete()


def create_default_group(apps, schema_editor):
    DartsGroup = apps.get_model("darts", "DartsGroup")
    DartsGroup.objects.get_or_create(name="Család")


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("darts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DartsGroup",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=80, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "members",
                    models.ManyToManyField(
                        blank=True,
                        related_name="darts_groups",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.RunPython(reset_darts_data, migrations.RunPython.noop),
        migrations.AddField(
            model_name="player",
            name="group",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="players",
                to="darts.dartsgroup",
            ),
        ),
        migrations.AddField(
            model_name="game",
            name="group",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="games",
                to="darts.dartsgroup",
            ),
        ),
        migrations.RunPython(create_default_group, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="player",
            name="group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="players",
                to="darts.dartsgroup",
            ),
        ),
        migrations.AlterField(
            model_name="game",
            name="group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="games",
                to="darts.dartsgroup",
            ),
        ),
        migrations.AlterField(
            model_name="player",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="darts_players",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="game",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="darts_games",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="player",
            unique_together={("group", "name")},
        ),
    ]

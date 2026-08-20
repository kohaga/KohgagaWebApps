import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Player",
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
                ("name", models.CharField(max_length=50)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="darts_players",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
                "unique_together": {("created_by", "name")},
            },
        ),
        migrations.CreateModel(
            name="Game",
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
                (
                    "game_type",
                    models.CharField(
                        choices=[("301", "301"), ("501", "501")],
                        default="301",
                        max_length=3,
                    ),
                ),
                (
                    "checkout_mode",
                    models.CharField(
                        choices=[
                            ("double", "Double out"),
                            ("straight", "Straight out"),
                        ],
                        default="double",
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Folyamatban"),
                            ("finished", "Lezárva"),
                        ],
                        default="active",
                        max_length=10,
                    ),
                ),
                ("current_player_order", models.PositiveSmallIntegerField(default=1)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="darts_games",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "winner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="won_darts_games",
                        to="darts.player",
                    ),
                ),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="GamePlayer",
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
                ("player_order", models.PositiveSmallIntegerField()),
                ("starting_score", models.PositiveSmallIntegerField()),
                ("current_score", models.PositiveSmallIntegerField()),
                (
                    "finishing_position",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                (
                    "game",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="game_players",
                        to="darts.game",
                    ),
                ),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="game_entries",
                        to="darts.player",
                    ),
                ),
            ],
            options={
                "ordering": ["player_order"],
                "unique_together": {
                    ("game", "player"),
                    ("game", "player_order"),
                },
            },
        ),
        migrations.CreateModel(
            name="Visit",
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
                ("visit_number", models.PositiveIntegerField()),
                ("starting_score", models.PositiveSmallIntegerField()),
                ("ending_score", models.PositiveSmallIntegerField()),
                ("bust", models.BooleanField(default=False)),
                ("checkout", models.BooleanField(default=False)),
                ("is_complete", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "game_player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="visits",
                        to="darts.gameplayer",
                    ),
                ),
            ],
            options={
                "ordering": ["visit_number"],
                "unique_together": {("game_player", "visit_number")},
            },
        ),
        migrations.CreateModel(
            name="DartThrow",
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
                ("dart_number", models.PositiveSmallIntegerField()),
                ("segment", models.PositiveSmallIntegerField()),
                ("multiplier", models.PositiveSmallIntegerField(default=1)),
                ("score", models.PositiveSmallIntegerField()),
                ("remaining_before", models.PositiveSmallIntegerField()),
                ("remaining_after", models.PositiveSmallIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "visit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="throws",
                        to="darts.visit",
                    ),
                ),
            ],
            options={
                "ordering": ["dart_number"],
                "unique_together": {("visit", "dart_number")},
            },
        ),
    ]

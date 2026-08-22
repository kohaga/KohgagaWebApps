from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class DartsGroup(models.Model):
    name = models.CharField(max_length=80, unique=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="darts_groups",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Player(models.Model):
    group = models.ForeignKey(
        DartsGroup,
        on_delete=models.CASCADE,
        related_name="players",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="darts_players",
    )
    name = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("group", "name")]

    def __str__(self):
        return self.name


class Game(models.Model):
    class GameType(models.TextChoices):
        GAME_301 = "301", "301"
        GAME_501 = "501", "501"

    class CheckoutMode(models.TextChoices):
        DOUBLE = "double", "Double out"
        STRAIGHT = "straight", "Straight out"

    class Status(models.TextChoices):
        ACTIVE = "active", "Folyamatban"
        FINISHED = "finished", "Lezárva"

    group = models.ForeignKey(
        DartsGroup,
        on_delete=models.CASCADE,
        related_name="games",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="darts_games",
    )
    game_type = models.CharField(
        max_length=3,
        choices=GameType.choices,
        default=GameType.GAME_301,
    )
    checkout_mode = models.CharField(
        max_length=10,
        choices=CheckoutMode.choices,
        default=CheckoutMode.DOUBLE,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    current_player_order = models.PositiveSmallIntegerField(default=1)
    winner = models.ForeignKey(
        Player,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="won_darts_games",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    @property
    def starting_score(self):
        return int(self.game_type)

    def __str__(self):
        return f"{self.game_type} - {self.started_at:%Y-%m-%d %H:%M}"


class GamePlayer(models.Model):
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="game_players",
    )
    player = models.ForeignKey(
        Player,
        on_delete=models.PROTECT,
        related_name="game_entries",
    )
    player_order = models.PositiveSmallIntegerField()
    starting_score = models.PositiveSmallIntegerField()
    current_score = models.PositiveSmallIntegerField()
    finishing_position = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["player_order"]
        unique_together = [
            ("game", "player"),
            ("game", "player_order"),
        ]

    def __str__(self):
        return f"{self.game} - {self.player}"


class Visit(models.Model):
    game_player = models.ForeignKey(
        GamePlayer,
        on_delete=models.CASCADE,
        related_name="visits",
    )
    visit_number = models.PositiveIntegerField()
    starting_score = models.PositiveSmallIntegerField()
    ending_score = models.PositiveSmallIntegerField()
    bust = models.BooleanField(default=False)
    checkout = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["visit_number"]
        unique_together = [("game_player", "visit_number")]

    @property
    def scored_points(self):
        if self.bust:
            return 0
        return self.starting_score - self.ending_score

    def __str__(self):
        return f"{self.game_player.player} - {self.visit_number}. kör"


class DartThrow(models.Model):
    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name="throws",
    )
    dart_number = models.PositiveSmallIntegerField()
    segment = models.PositiveSmallIntegerField()
    multiplier = models.PositiveSmallIntegerField(default=1)
    score = models.PositiveSmallIntegerField()
    remaining_before = models.PositiveSmallIntegerField()
    remaining_after = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["dart_number"]
        unique_together = [("visit", "dart_number")]

    def clean(self):
        if self.dart_number not in (1, 2, 3):
            raise ValidationError("A dart sorszáma 1, 2 vagy 3 lehet.")

        valid_segments = set(range(0, 21)) | {25}
        if self.segment not in valid_segments:
            raise ValidationError("Érvénytelen darts szektor.")

        if self.multiplier not in (1, 2, 3):
            raise ValidationError("A szorzó 1, 2 vagy 3 lehet.")

        if self.segment == 0 and self.multiplier != 1:
            raise ValidationError("A mellédobás nem lehet dupla vagy tripla.")

        if self.segment == 25 and self.multiplier not in (1, 2):
            raise ValidationError("A bull csak 25 vagy 50 pont lehet.")

    @property
    def display_value(self):
        if self.segment == 0:
            return "MISS"
        if self.segment == 25:
            return "BULL" if self.multiplier == 2 else "25"

        prefix = {1: "", 2: "D", 3: "T"}[self.multiplier]
        return f"{prefix}{self.segment}"

    def __str__(self):
        return self.display_value

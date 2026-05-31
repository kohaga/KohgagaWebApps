from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models


class Language(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Deck(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    source_language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name="source_decks",
    )

    target_language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name="target_decks",
    )

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Card(models.Model):
    CARD_TYPE_WORD = "word"
    CARD_TYPE_PHRASE = "phrase"
    CARD_TYPE_SENTENCE = "sentence"

    CARD_TYPE_CHOICES = [
        (CARD_TYPE_WORD, "Szó"),
        (CARD_TYPE_PHRASE, "Kifejezés"),
        (CARD_TYPE_SENTENCE, "Mondat"),
    ]

    deck = models.ForeignKey(
        Deck,
        on_delete=models.CASCADE,
        related_name="cards",
    )

    source_text = models.CharField(max_length=255)
    target_text = models.CharField(max_length=255)

    card_type = models.CharField(
        max_length=20,
        choices=CARD_TYPE_CHOICES,
        default=CARD_TYPE_WORD,
    )

    example_sentence = models.TextField(blank=True)
    note = models.TextField(blank=True)

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["source_text"]

    def __str__(self):
        return f"{self.source_text} → {self.target_text}"


class PracticeSessionResult(models.Model):
    DIRECTION_SOURCE_TO_TARGET = "source-to-target"
    DIRECTION_TARGET_TO_SOURCE = "target-to-source"

    DIRECTION_CHOICES = [
        (DIRECTION_SOURCE_TO_TARGET, "Forrás → Cél"),
        (DIRECTION_TARGET_TO_SOURCE, "Cél → Forrás"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="practice_session_results",
    )

    deck = models.ForeignKey(
        Deck,
        on_delete=models.CASCADE,
        related_name="practice_session_results",
    )

    direction = models.CharField(
        max_length=30,
        choices=DIRECTION_CHOICES,
    )

    requested_question_count = models.PositiveIntegerField()
    first_round_question_count = models.PositiveIntegerField()
    first_round_correct_count = models.PositiveIntegerField()
    first_round_wrong_count = models.PositiveIntegerField()

    accuracy_percent = models.PositiveIntegerField()

    repeated_wrong_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} | {self.deck} | {self.accuracy_percent}%"
from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Language, Deck, Card, PracticeSessionResult


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ("name", "source_language", "target_language", "active", "created_at")
    list_filter = ("source_language", "target_language", "active")
    search_fields = ("name", "description")


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("source_text", "target_text", "deck", "card_type", "active")
    list_filter = ("deck", "card_type", "active")
    search_fields = ("source_text", "target_text", "example_sentence", "note")


@admin.register(PracticeSessionResult)
class PracticeSessionResultAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "deck",
        "direction",
        "requested_question_count",
        "first_round_question_count",
        "first_round_correct_count",
        "first_round_wrong_count",
        "accuracy_percent",
        "repeated_wrong_count",
        "created_at",
    )

    list_filter = (
        "deck",
        "direction",
        "accuracy_percent",
        "created_at",
    )

    search_fields = (
        "user__username",
        "deck__name",
    )

    readonly_fields = (
        "user",
        "deck",
        "direction",
        "requested_question_count",
        "first_round_question_count",
        "first_round_correct_count",
        "first_round_wrong_count",
        "accuracy_percent",
        "repeated_wrong_count",
        "created_at",
    )
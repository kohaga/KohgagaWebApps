from django.contrib import admin

from .models import DartThrow, Game, GamePlayer, Player, Visit


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "active", "created_at"]
    list_filter = ["active"]
    search_fields = ["name", "created_by__username"]


class GamePlayerInline(admin.TabularInline):
    model = GamePlayer
    extra = 0


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = [
        "game_type",
        "checkout_mode",
        "status",
        "winner",
        "created_by",
        "started_at",
        "finished_at",
    ]
    list_filter = ["game_type", "checkout_mode", "status"]
    inlines = [GamePlayerInline]


@admin.register(GamePlayer)
class GamePlayerAdmin(admin.ModelAdmin):
    list_display = [
        "game",
        "player",
        "player_order",
        "starting_score",
        "current_score",
    ]


class DartThrowInline(admin.TabularInline):
    model = DartThrow
    extra = 0


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = [
        "game_player",
        "visit_number",
        "starting_score",
        "ending_score",
        "bust",
        "checkout",
        "is_complete",
    ]
    list_filter = ["bust", "checkout", "is_complete"]
    inlines = [DartThrowInline]


@admin.register(DartThrow)
class DartThrowAdmin(admin.ModelAdmin):
    list_display = [
        "visit",
        "dart_number",
        "segment",
        "multiplier",
        "score",
        "remaining_before",
        "remaining_after",
    ]

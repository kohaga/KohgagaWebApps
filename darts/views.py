from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .models import Game, GamePlayer, Player
from .services import (
    get_current_game_player,
    get_finish_options,
    get_player_stats,
    record_throw,
    undo_last_throw,
)


@login_required
def dashboard(request):
    players = Player.objects.filter(
        created_by=request.user,
        active=True,
    ).order_by("name")

    player_rows = [
        {
            "player": player,
            "stats": get_player_stats(player),
        }
        for player in players
    ]

    recent_games = (
        Game.objects
        .filter(created_by=request.user)
        .select_related("winner")
        .prefetch_related("game_players__player")
        .order_by("-started_at")[:5]
    )

    return render(
        request,
        "darts/dashboard.html",
        {
            "player_rows": player_rows,
            "recent_games": recent_games,
        },
    )


@login_required
def add_player(request):
    if request.method != "POST":
        return redirect("darts:dashboard")

    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Add meg a játékos nevét.")
        return redirect("darts:dashboard")

    player, created = Player.objects.get_or_create(
        created_by=request.user,
        name=name,
        defaults={"active": True},
    )

    if not created and not player.active:
        player.active = True
        player.save(update_fields=["active"])
        created = True

    if created:
        messages.success(request, f"{player.name} hozzáadva.")
    else:
        messages.info(request, "Ez a játékos már szerepel a listában.")

    return redirect("darts:dashboard")


@login_required
def player_detail(request, player_id):
    player = get_object_or_404(
        Player,
        id=player_id,
        created_by=request.user,
    )
    stats = get_player_stats(player)
    recent_entries = (
        GamePlayer.objects
        .filter(
            player=player,
            game__created_by=request.user,
            game__status=Game.Status.FINISHED,
        )
        .select_related("game", "game__winner")
        .order_by("-game__finished_at")[:10]
    )

    return render(
        request,
        "darts/player_detail.html",
        {
            "player": player,
            "stats": stats,
            "recent_entries": recent_entries,
        },
    )


@login_required
def new_game(request):
    players = list(
        Player.objects
        .filter(created_by=request.user, active=True)
        .order_by("name")
    )

    if request.method == "POST":
        game_type = request.POST.get("game_type", Game.GameType.GAME_301)
        checkout_mode = request.POST.get(
            "checkout_mode",
            Game.CheckoutMode.DOUBLE,
        )
        selected_ids = request.POST.getlist("players")

        valid_game_types = {value for value, _label in Game.GameType.choices}
        valid_checkout_modes = {
            value for value, _label in Game.CheckoutMode.choices
        }

        if game_type not in valid_game_types:
            game_type = Game.GameType.GAME_301
        if checkout_mode not in valid_checkout_modes:
            checkout_mode = Game.CheckoutMode.DOUBLE

        selected_players = [
            player
            for player in players
            if str(player.id) in selected_ids
        ]

        if not selected_players:
            messages.error(request, "Válassz legalább egy játékost.")
            return render(
                request,
                "darts/new_game.html",
                {"players": players},
            )

        with transaction.atomic():
            game = Game.objects.create(
                created_by=request.user,
                game_type=game_type,
                checkout_mode=checkout_mode,
            )

            starting_score = int(game_type)
            for order, player in enumerate(selected_players, start=1):
                GamePlayer.objects.create(
                    game=game,
                    player=player,
                    player_order=order,
                    starting_score=starting_score,
                    current_score=starting_score,
                )

        return redirect("darts:game", game_id=game.id)

    return render(
        request,
        "darts/new_game.html",
        {"players": players},
    )


@login_required
def game_detail(request, game_id):
    game = get_object_or_404(
        Game.objects.select_related("winner"),
        id=game_id,
        created_by=request.user,
    )

    game_players = list(
        game.game_players
        .select_related("player")
        .prefetch_related("visits__throws")
        .order_by("player_order")
    )

    scoreboard_rows = []
    for game_player in game_players:
        last_visit = (
            game_player.visits
            .filter(is_complete=True)
            .order_by("-visit_number")
            .first()
        )
        scoreboard_rows.append(
            {
                "game_player": game_player,
                "last_visit": last_visit,
            }
        )

    current_game_player = None
    current_visit = None
    current_throws = []
    finish_options = []
    darts_left = 3

    if game.status == Game.Status.ACTIVE:
        current_game_player = get_current_game_player(game)
        current_visit = (
            current_game_player.visits
            .filter(is_complete=False)
            .prefetch_related("throws")
            .order_by("visit_number")
            .first()
        )
        if current_visit:
            current_throws = list(current_visit.throws.all())
            darts_left = 3 - len(current_throws)

        finish_options = get_finish_options(
            current_game_player.current_score,
            darts_left=darts_left,
            checkout_mode=game.checkout_mode,
        )

    return render(
        request,
        "darts/game.html",
        {
            "game": game,
            "scoreboard_rows": scoreboard_rows,
            "current_game_player": current_game_player,
            "current_visit": current_visit,
            "current_throws": current_throws,
            "darts_left": darts_left,
            "finish_options": finish_options,
            "number_buttons": range(0, 21),
        },
    )


@login_required
def record_dart(request, game_id):
    if request.method != "POST":
        return redirect("darts:game", game_id=game_id)

    game = get_object_or_404(
        Game,
        id=game_id,
        created_by=request.user,
    )

    try:
        record_throw(
            game,
            segment=request.POST.get("segment"),
            multiplier=request.POST.get("multiplier", 1),
        )
    except ValueError as error:
        messages.error(request, str(error))

    return redirect("darts:game", game_id=game.id)


@login_required
def undo_dart(request, game_id):
    if request.method != "POST":
        return redirect("darts:game", game_id=game_id)

    game = get_object_or_404(
        Game,
        id=game_id,
        created_by=request.user,
    )

    try:
        undo_last_throw(game)
    except ValueError as error:
        messages.error(request, str(error))

    return redirect("darts:game", game_id=game.id)

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import DartThrow, Game, GamePlayer, Visit


TRIPLE_DARTS = [(value * 3, f"T{value}") for value in range(20, 0, -1)]
DOUBLE_DARTS = [(value * 2, f"D{value}") for value in range(20, 0, -1)]
SINGLE_DARTS = [(value, str(value)) for value in range(20, 0, -1)]
SCORING_DARTS = TRIPLE_DARTS + [(50, "BULL")] + DOUBLE_DARTS + SINGLE_DARTS + [(25, "25")]
FINISH_DARTS = [
    (40, "D20"),
    (32, "D16"),
    (36, "D18"),
    (24, "D12"),
    (20, "D10"),
    (16, "D8"),
    (8, "D4"),
    (4, "D2"),
    (2, "D1"),
    (50, "BULL"),
] + [
    (value * 2, f"D{value}")
    for value in range(20, 0, -1)
    if value not in {20, 16, 18, 12, 10, 8, 4, 2, 1}
]


def get_checkout_suggestion(remaining_score, darts_left=3):
    """Return a valid double-out route using at most darts_left darts."""
    try:
        remaining_score = int(remaining_score)
        darts_left = int(darts_left)
    except (TypeError, ValueError):
        return []

    if remaining_score < 2 or remaining_score > 170 or darts_left < 1:
        return []

    for finish_score, finish_label in FINISH_DARTS:
        if finish_score == remaining_score:
            return [finish_label]

    if darts_left >= 2:
        for first_score, first_label in SCORING_DARTS:
            needed = remaining_score - first_score
            for finish_score, finish_label in FINISH_DARTS:
                if finish_score == needed:
                    return [first_label, finish_label]

    if darts_left >= 3:
        for first_score, first_label in SCORING_DARTS:
            remaining_after_first = remaining_score - first_score
            if remaining_after_first < 2:
                continue

            for second_score, second_label in SCORING_DARTS:
                needed = remaining_after_first - second_score
                for finish_score, finish_label in FINISH_DARTS:
                    if finish_score == needed:
                        return [first_label, second_label, finish_label]

    return []


def _one_dart_finish_options(remaining_score, checkout_mode):
    options = []

    if checkout_mode == Game.CheckoutMode.STRAIGHT:
        if 1 <= remaining_score <= 20:
            options.append(str(remaining_score))
        elif remaining_score == 25:
            options.append("25")
        elif remaining_score == 50:
            options.append("BULL")

        if (
            remaining_score % 2 == 0
            and 1 <= remaining_score // 2 <= 20
        ):
            options.append(f"D{remaining_score // 2}")

        if (
            remaining_score % 3 == 0
            and 1 <= remaining_score // 3 <= 20
        ):
            options.append(f"T{remaining_score // 3}")

        return options[:3]

    if remaining_score == 50:
        return ["BULL"]

    if (
        remaining_score % 2 == 0
        and 1 <= remaining_score // 2 <= 20
    ):
        return [f"D{remaining_score // 2}"]

    return []


def get_finish_suggestion(remaining_score, darts_left=3, checkout_mode="double"):
    try:
        remaining_score = int(remaining_score)
        darts_left = int(darts_left)
    except (TypeError, ValueError):
        return []

    if remaining_score <= 0 or darts_left < 1:
        return []

    if checkout_mode == Game.CheckoutMode.STRAIGHT:
        return _find_straight_finish(remaining_score, darts_left)

    return get_checkout_suggestion(remaining_score, darts_left)


def get_finish_options(remaining_score, darts_left=3, checkout_mode="double"):
    """Return up to three compact finish targets for the scoring screen."""
    try:
        remaining_score = int(remaining_score)
        darts_left = int(darts_left)
    except (TypeError, ValueError):
        return []

    if remaining_score <= 0 or darts_left < 1:
        return []

    immediate_finishes = _one_dart_finish_options(
        remaining_score,
        checkout_mode,
    )
    if immediate_finishes:
        return immediate_finishes

    return get_finish_suggestion(
        remaining_score,
        darts_left=darts_left,
        checkout_mode=checkout_mode,
    )[:3]


def _find_straight_finish(remaining_score, darts_left):
    immediate_finishes = _one_dart_finish_options(
        remaining_score,
        Game.CheckoutMode.STRAIGHT,
    )
    if immediate_finishes:
        return [immediate_finishes[0]]

    if darts_left >= 2:
        for first_score, first_label in SCORING_DARTS:
            needed = remaining_score - first_score
            for second_score, second_label in SCORING_DARTS:
                if second_score == needed:
                    return [first_label, second_label]

    if darts_left >= 3:
        for first_score, first_label in SCORING_DARTS:
            remaining_after_first = remaining_score - first_score
            if remaining_after_first <= 0:
                continue

            for second_score, second_label in SCORING_DARTS:
                needed = remaining_after_first - second_score
                for third_score, third_label in SCORING_DARTS:
                    if third_score == needed:
                        return [first_label, second_label, third_label]

    return []


def get_current_game_player(game):
    return game.game_players.select_related("player").get(
        player_order=game.current_player_order,
    )


def _advance_player(game):
    orders = list(
        game.game_players.order_by("player_order").values_list(
            "player_order",
            flat=True,
        )
    )
    if not orders:
        return

    try:
        current_index = orders.index(game.current_player_order)
    except ValueError:
        game.current_player_order = orders[0]
    else:
        game.current_player_order = orders[(current_index + 1) % len(orders)]

    game.save(update_fields=["current_player_order"])


def _is_valid_double_finish(segment, multiplier):
    return multiplier == 2 and segment in set(range(1, 21)) | {25}


@transaction.atomic
def record_throw(game, segment, multiplier):
    if game.status != Game.Status.ACTIVE:
        raise ValueError("Ez a játék már le van zárva.")

    try:
        segment = int(segment)
        multiplier = int(multiplier)
    except (TypeError, ValueError):
        raise ValueError("Hibás dobásérték.")

    valid_segments = set(range(0, 21)) | {25}
    if segment not in valid_segments:
        raise ValueError("Érvénytelen szektor.")
    if multiplier not in (1, 2, 3):
        raise ValueError("Érvénytelen szorzó.")
    if segment == 0:
        multiplier = 1
    if segment == 25 and multiplier not in (1, 2):
        raise ValueError("A bull csak 25 vagy 50 pont lehet.")

    game_player = get_current_game_player(game)
    visit = game_player.visits.filter(is_complete=False).order_by("visit_number").first()

    if visit is None:
        visit_number = game_player.visits.count() + 1
        visit = Visit.objects.create(
            game_player=game_player,
            visit_number=visit_number,
            starting_score=game_player.current_score,
            ending_score=game_player.current_score,
        )

    dart_number = visit.throws.count() + 1
    if dart_number > 3:
        raise ValueError("Egy körben legfeljebb három dart dobható.")

    score = segment * multiplier
    remaining_before = game_player.current_score
    prospective_score = remaining_before - score

    if game.checkout_mode == Game.CheckoutMode.DOUBLE:
        is_checkout = (
            prospective_score == 0
            and _is_valid_double_finish(segment, multiplier)
        )
        is_bust = (
            prospective_score < 0
            or prospective_score == 1
            or (prospective_score == 0 and not is_checkout)
        )
    else:
        is_checkout = prospective_score == 0
        is_bust = prospective_score < 0

    if is_bust:
        remaining_after = visit.starting_score
    else:
        remaining_after = prospective_score

    throw = DartThrow(
        visit=visit,
        dart_number=dart_number,
        segment=segment,
        multiplier=multiplier,
        score=score,
        remaining_before=remaining_before,
        remaining_after=remaining_after,
    )
    throw.full_clean()
    throw.save()

    if is_bust:
        game_player.current_score = visit.starting_score
        game_player.save(update_fields=["current_score"])

        visit.ending_score = visit.starting_score
        visit.bust = True
        visit.is_complete = True
        visit.completed_at = timezone.now()
        visit.save(
            update_fields=[
                "ending_score",
                "bust",
                "is_complete",
                "completed_at",
            ]
        )
        _advance_player(game)
        return throw

    game_player.current_score = prospective_score
    game_player.save(update_fields=["current_score"])
    visit.ending_score = prospective_score

    if is_checkout:
        visit.checkout = True
        visit.is_complete = True
        visit.completed_at = timezone.now()
        visit.save(
            update_fields=[
                "ending_score",
                "checkout",
                "is_complete",
                "completed_at",
            ]
        )

        game.status = Game.Status.FINISHED
        game.winner = game_player.player
        game.finished_at = timezone.now()
        game.save(update_fields=["status", "winner", "finished_at"])
        game_player.finishing_position = 1
        game_player.save(update_fields=["finishing_position"])
        return throw

    if dart_number == 3:
        visit.is_complete = True
        visit.completed_at = timezone.now()
        visit.save(update_fields=["ending_score", "is_complete", "completed_at"])
        _advance_player(game)
    else:
        visit.save(update_fields=["ending_score"])

    return throw


@transaction.atomic
def undo_last_throw(game):
    throw = (
        DartThrow.objects
        .filter(visit__game_player__game=game)
        .select_related("visit__game_player")
        .order_by("-id")
        .first()
    )
    if throw is None:
        raise ValueError("Még nincs visszavonható dobás.")

    visit = throw.visit
    game_player = visit.game_player

    game.current_player_order = game_player.player_order
    if game.status == Game.Status.FINISHED:
        game.status = Game.Status.ACTIVE
        game.winner = None
        game.finished_at = None
        game.save(
            update_fields=[
                "current_player_order",
                "status",
                "winner",
                "finished_at",
            ]
        )
        game_player.finishing_position = None
        game_player.save(update_fields=["finishing_position"])
    else:
        game.save(update_fields=["current_player_order"])

    game_player.current_score = throw.remaining_before
    game_player.save(update_fields=["current_score"])

    throw.delete()

    if not visit.throws.exists():
        visit.delete()
        return

    visit.ending_score = game_player.current_score
    visit.bust = False
    visit.checkout = False
    visit.is_complete = False
    visit.completed_at = None
    visit.save(
        update_fields=[
            "ending_score",
            "bust",
            "checkout",
            "is_complete",
            "completed_at",
        ]
    )


def calculate_three_dart_average(visits):
    total_points = 0
    total_darts = 0

    for visit in visits:
        throws = list(visit.throws.all())
        total_darts += len(throws)
        total_points += visit.scored_points

    if not total_darts:
        return None

    return round((total_points / total_darts) * 3, 1)


def get_player_stats(player):
    completed_entries = list(
        GamePlayer.objects
        .filter(
            player=player,
            game__status=Game.Status.FINISHED,
        )
        .select_related("game")
        .order_by("-game__finished_at")
    )

    all_visits = list(
        Visit.objects
        .filter(
            game_player__player=player,
            game_player__game__status=Game.Status.FINISHED,
            is_complete=True,
        )
        .prefetch_related("throws")
        .order_by("created_at")
    )

    last_game_average = None
    if completed_entries:
        last_entry = completed_entries[0]
        last_visits = list(
            last_entry.visits
            .filter(is_complete=True)
            .prefetch_related("throws")
            .order_by("visit_number")
        )
        last_game_average = calculate_three_dart_average(last_visits)

    since = timezone.now() - timedelta(days=30)
    visits_30 = [
        visit
        for visit in all_visits
        if visit.game_player.game.finished_at
        and visit.game_player.game.finished_at >= since
    ]

    checkout_visits = [visit for visit in all_visits if visit.checkout]
    scored_visits = [visit.scored_points for visit in all_visits]

    return {
        "games_played": len(completed_entries),
        "games_won": sum(
            1
            for entry in completed_entries
            if entry.game.winner_id == player.id
        ),
        "last_game_average": last_game_average,
        "average_30_days": calculate_three_dart_average(visits_30),
        "all_time_average": calculate_three_dart_average(all_visits),
        "highest_visit": max(scored_visits, default=None),
        "highest_checkout": max(
            (visit.scored_points for visit in checkout_visits),
            default=None,
        ),
        "visits_100_plus": sum(1 for score in scored_visits if score >= 100),
        "visits_140_plus": sum(1 for score in scored_visits if score >= 140),
        "visits_180": sum(1 for score in scored_visits if score == 180),
    }

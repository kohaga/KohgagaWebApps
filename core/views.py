from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from workouts.models import WorkoutSession


XP_PER_WORKOUT = 100
XP_PER_LEVEL = 500
MIN_XP_WORKOUT_SECONDS = 10 * 60
FULL_XP_WORKOUT_SECONDS = 30 * 60
CONSISTENCY_BONUS_MULTIPLIER = 1.3
CONSISTENCY_BONUS_MAX_GAP_SECONDS = 2 * 24 * 60 * 60


def _calculate_workout_xp(duration_seconds, has_consistency_bonus=False):
    if not duration_seconds or duration_seconds <= MIN_XP_WORKOUT_SECONDS:
        return 0

    if duration_seconds >= FULL_XP_WORKOUT_SECONDS:
        duration_multiplier = 1.0
    else:
        duration_multiplier = (
            (duration_seconds - MIN_XP_WORKOUT_SECONDS)
            / (FULL_XP_WORKOUT_SECONDS - MIN_XP_WORKOUT_SECONDS)
        )

    consistency_multiplier = (
        CONSISTENCY_BONUS_MULTIPLIER
        if has_consistency_bonus
        else 1.0
    )

    return round(
        XP_PER_WORKOUT
        * duration_multiplier
        * consistency_multiplier
    )


def get_workout_xp_summary(user):
    completed_workouts = list(
        WorkoutSession.objects
        .filter(
            user=user,
            status=WorkoutSession.Status.COMPLETED,
            actual_duration_seconds__isnull=False,
            finished_at__isnull=False,
        )
        .order_by("finished_at")
        .only("finished_at", "actual_duration_seconds")
    )

    total_xp = 0
    previous_finished_at = None

    for workout in completed_workouts:
        has_consistency_bonus = False

        if previous_finished_at is not None:
            gap_seconds = (
                workout.finished_at - previous_finished_at
            ).total_seconds()
            has_consistency_bonus = (
                gap_seconds <= CONSISTENCY_BONUS_MAX_GAP_SECONDS
            )

        total_xp += _calculate_workout_xp(
            workout.actual_duration_seconds,
            has_consistency_bonus=has_consistency_bonus,
        )
        previous_finished_at = workout.finished_at

    level = (total_xp // XP_PER_LEVEL) + 1
    xp_in_level = total_xp % XP_PER_LEVEL
    xp_to_next_level = XP_PER_LEVEL - xp_in_level

    progress_percent = int(
        (xp_in_level / XP_PER_LEVEL) * 100
    )

    return {
        "level": level,
        "total_xp": total_xp,
        "xp_in_level": xp_in_level,
        "xp_to_next_level": xp_to_next_level,
        "progress_percent": progress_percent,
    }


@login_required
def home_view(request):
    workout_xp = get_workout_xp_summary(request.user)

    return render(
        request,
        "core/home.html",
        {
            "workout_xp": workout_xp,
        },
    )

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from workouts.models import WorkoutSession


XP_PER_WORKOUT = 100
XP_PER_LEVEL = 500
MIN_XP_WORKOUT_SECONDS = 30 * 60


def get_workout_xp_summary(user):
    valid_workouts = WorkoutSession.objects.filter(
        user=user,
        status=WorkoutSession.Status.COMPLETED,
        actual_duration_seconds__gte=MIN_XP_WORKOUT_SECONDS,
    ).count()

    total_xp = valid_workouts * XP_PER_WORKOUT

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
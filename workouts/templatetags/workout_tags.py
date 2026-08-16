from django import template

from workouts.models import WorkoutSession

register = template.Library()

DEFAULT_WARMUP_MINUTES = 4
DEFAULT_COOLDOWN_MINUTES = 4


@register.simple_tag
def last_training_goal(user):
    if not getattr(user, "is_authenticated", False):
        return WorkoutSession.TrainingGoal.CALORIE_BURN

    last_session = (
        WorkoutSession.objects
        .filter(user=user)
        .exclude(training_goal="")
        .order_by("-created_at")
        .only("training_goal")
        .first()
    )

    if last_session:
        return last_session.training_goal

    return WorkoutSession.TrainingGoal.CALORIE_BURN


@register.simple_tag
def last_muscle_gain_block_durations(user):
    defaults = {
        "warmup": DEFAULT_WARMUP_MINUTES,
        "cooldown": DEFAULT_COOLDOWN_MINUTES,
    }

    if not getattr(user, "is_authenticated", False):
        return defaults

    last_session = (
        WorkoutSession.objects
        .filter(
            user=user,
            training_goal=WorkoutSession.TrainingGoal.MUSCLE_GAIN,
        )
        .order_by("-created_at")
        .only("warmup_duration_minutes", "cooldown_duration_minutes")
        .first()
    )

    if not last_session:
        return defaults

    return {
        "warmup": last_session.warmup_duration_minutes or DEFAULT_WARMUP_MINUTES,
        "cooldown": last_session.cooldown_duration_minutes or DEFAULT_COOLDOWN_MINUTES,
    }

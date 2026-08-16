from django import template

from workouts.models import WorkoutSession

register = template.Library()


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

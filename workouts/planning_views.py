from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from .models import WorkoutSession, WorkoutSessionExercise
from .services import replace_session_exercise_for_user


@login_required
def replace_planned_exercise(request, session_id, session_exercise_id):
    if request.method != "POST":
        return redirect("workouts:workout_session_detail", session_id=session_id)

    session = get_object_or_404(
        WorkoutSession,
        id=session_id,
        user=request.user,
    )

    if session.status != WorkoutSession.Status.PLANNED:
        messages.error(
            request,
            "Gyakorlatot csak az edzés indítása előtt lehet ezen a képernyőn cserélni.",
        )
        return redirect("workouts:workout_session_detail", session_id=session.id)

    session_exercise = get_object_or_404(
        WorkoutSessionExercise.objects.select_related("exercise", "session"),
        id=session_exercise_id,
        session=session,
    )

    original_name = session_exercise.exercise.name

    try:
        replacement = replace_session_exercise_for_user(
            request.user,
            session_exercise,
        )
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("workouts:workout_session_detail", session_id=session.id)

    messages.success(
        request,
        f"{original_name} lecserélve erre: {replacement.name}.",
    )
    return redirect("workouts:workout_session_detail", session_id=session.id)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import WorkoutSession
from .services import generate_workout_for_user
from .timed_blocks import (
    DEFAULT_COOLDOWN_MINUTES,
    DEFAULT_WARMUP_MINUTES,
    apply_timed_muscle_gain_blocks,
    parse_block_minutes,
)


@login_required
def generate_workout(request):
    if request.method != "POST":
        return redirect("workouts:exercise_list")

    open_session = (
        WorkoutSession.objects
        .filter(
            user=request.user,
            status__in=[
                WorkoutSession.Status.PLANNED,
                WorkoutSession.Status.IN_PROGRESS,
            ],
        )
        .order_by("-created_at")
        .first()
    )

    if open_session:
        messages.info(
            request,
            "Már van egy nyitott edzésed. Először azt fejezd be vagy töröld.",
        )
        return redirect(
            "workouts:workout_session_detail",
            session_id=open_session.id,
        )

    workout_profile = request.POST.get("workout_profile", "full_body")
    training_goal = request.POST.get(
        "training_goal",
        WorkoutSession.TrainingGoal.CALORIE_BURN,
    )
    circuit_rounds = request.POST.get("circuit_rounds", 3)
    circuit_exercise_count = request.POST.get("circuit_exercise_count", 3)

    warmup_minutes = parse_block_minutes(
        request.POST.get("warmup_duration_minutes"),
        DEFAULT_WARMUP_MINUTES,
    )
    cooldown_minutes = parse_block_minutes(
        request.POST.get("cooldown_duration_minutes"),
        DEFAULT_COOLDOWN_MINUTES,
    )

    try:
        session = generate_workout_for_user(
            user=request.user,
            planned_duration_minutes=45,
            workout_profile=workout_profile,
            training_goal=training_goal,
            circuit_rounds=circuit_rounds,
            circuit_exercise_count=circuit_exercise_count,
        )

        if (
            training_goal == WorkoutSession.TrainingGoal.MUSCLE_GAIN
            and workout_profile != "aerobic_video"
        ):
            session.warmup_duration_minutes = warmup_minutes
            session.cooldown_duration_minutes = cooldown_minutes
            session.save(
                update_fields=[
                    "warmup_duration_minutes",
                    "cooldown_duration_minutes",
                ]
            )
            apply_timed_muscle_gain_blocks(
                session=session,
                user=request.user,
                warmup_minutes=warmup_minutes,
                cooldown_minutes=cooldown_minutes,
            )
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("workouts:exercise_list")

    messages.success(request, "A mai edzés elkészült.")
    return redirect("workouts:workout_session_detail", session_id=session.id)

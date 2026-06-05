import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import (
    Exercise,
    UserExerciseProfile,
    WorkoutSession,
    WorkoutSessionExercise,
)


def generate_workout_for_user(user, planned_duration_minutes=45):
    """
    Generates a simple circuit workout:
    warmup -> 3 circuit exercises x 3 rounds -> cooldown.
    """

    excluded_exercise_ids = set(
        UserExerciseProfile.objects
        .filter(user=user, is_excluded=True)
        .values_list("exercise_id", flat=True)
    )

    recent_since = timezone.now() - timedelta(days=7)

    recent_exercise_ids = set(
        WorkoutSessionExercise.objects
        .filter(
            session__user=user,
            session__created_at__gte=recent_since,
        )
        .values_list("exercise_id", flat=True)
    )

    selected_exercises = []

    warmup = _select_exercise(
        movement_pattern=Exercise.MovementPattern.CARDIO,
        excluded_exercise_ids=excluded_exercise_ids,
        recent_exercise_ids=set(),
        already_selected_ids=set(),
    )

    circuit_patterns = [
        Exercise.MovementPattern.SQUAT,
        Exercise.MovementPattern.PUSH,
        Exercise.MovementPattern.PULL,
    ]

    circuit_exercises = []

    for movement_pattern in circuit_patterns:
        exercise = _select_exercise(
            movement_pattern=movement_pattern,
            excluded_exercise_ids=excluded_exercise_ids,
            recent_exercise_ids=recent_exercise_ids,
            already_selected_ids={item.id for item in selected_exercises if item},
        )

        if exercise:
            circuit_exercises.append(exercise)
            selected_exercises.append(exercise)

    cooldown = _select_exercise(
        movement_pattern=Exercise.MovementPattern.CARDIO,
        excluded_exercise_ids=excluded_exercise_ids,
        recent_exercise_ids=set(),
        already_selected_ids={warmup.id} if warmup else set(),
    )

    if not cooldown:
        cooldown = warmup

    if not warmup and not circuit_exercises:
        raise ValueError("No exercises available for workout generation.")

    with transaction.atomic():
        session = WorkoutSession.objects.create(
            user=user,
            title="Mai köredzés",
            status=WorkoutSession.Status.PLANNED,
            generation_type=WorkoutSession.GenerationType.GENERATED,
            planned_duration_minutes=planned_duration_minutes,
        )

        position = 1

        if warmup:
            _create_session_exercise(
                session=session,
                exercise=warmup,
                position=position,
                block_type=WorkoutSessionExercise.BlockType.WARMUP,
                target_sets=1,
                rest_seconds=30,
                user=user,
            )
            position += 1

        for exercise in circuit_exercises:
            _create_session_exercise(
                session=session,
                exercise=exercise,
                position=position,
                block_type=WorkoutSessionExercise.BlockType.CIRCUIT,
                target_sets=3,
                rest_seconds=60,
                user=user,
            )
            position += 1

        if cooldown:
            _create_session_exercise(
                session=session,
                exercise=cooldown,
                position=position,
                block_type=WorkoutSessionExercise.BlockType.COOLDOWN,
                target_sets=1,
                rest_seconds=0,
                user=user,
            )

    return session

def _create_session_exercise(
    session,
    exercise,
    position,
    block_type,
    target_sets,
    rest_seconds,
    user,
):
    user_profile = UserExerciseProfile.objects.filter(
        user=user,
        exercise=exercise,
    ).first()

    target_weight = None

    if user_profile:
        target_weight = (
            user_profile.preferred_weight_kg
            or user_profile.last_weight_kg
            or None
        )

    return WorkoutSessionExercise.objects.create(
        session=session,
        exercise=exercise,
        position=position,
        block_type=block_type,
        target_sets=target_sets,
        target_reps_min=exercise.default_reps_min,
        target_reps_max=exercise.default_reps_max,
        target_weight_kg=target_weight,
        rest_seconds=rest_seconds,
    )

def _select_exercise(
    movement_pattern,
    excluded_exercise_ids,
    recent_exercise_ids,
    already_selected_ids,
):
    base_queryset = Exercise.objects.filter(
        is_active=True,
        movement_pattern=movement_pattern,
    ).exclude(
        id__in=excluded_exercise_ids,
    ).exclude(
        id__in=already_selected_ids,
    )

    preferred_queryset = base_queryset.exclude(
        id__in=recent_exercise_ids,
    )

    exercises = list(preferred_queryset)

    if not exercises:
        exercises = list(base_queryset)

    if not exercises:
        return None

    return random.choice(exercises)
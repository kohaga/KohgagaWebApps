import random

from django.db import transaction
from django.db.models import F

from .models import (
    Exercise,
    ExerciseMuscle,
    UserExerciseProfile,
    WorkoutSession,
    WorkoutSessionExercise,
)


DEFAULT_WARMUP_MINUTES = 4
DEFAULT_COOLDOWN_MINUTES = 4
MIN_BLOCK_MINUTES = 1
MAX_BLOCK_MINUTES = 10
DEFAULT_EXERCISE_DURATION_SECONDS = 60


def parse_block_minutes(value, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default

    return max(MIN_BLOCK_MINUTES, min(value, MAX_BLOCK_MINUTES))


def apply_timed_muscle_gain_blocks(
    session,
    user,
    warmup_minutes=DEFAULT_WARMUP_MINUTES,
    cooldown_minutes=DEFAULT_COOLDOWN_MINUTES,
):
    """Replace generic muscle-gain warmup/cooldown with timed, muscle-specific blocks."""

    if session.training_goal != WorkoutSession.TrainingGoal.MUSCLE_GAIN:
        return session

    circuit_items = list(
        session.session_exercises
        .filter(block_type=WorkoutSessionExercise.BlockType.CIRCUIT)
        .select_related("exercise")
        .order_by("position")
    )

    if not circuit_items:
        return session

    circuit_exercise_ids = [item.exercise_id for item in circuit_items]
    primary_muscle_ids = set(
        ExerciseMuscle.objects
        .filter(
            exercise_id__in=circuit_exercise_ids,
            role=ExerciseMuscle.MuscleRole.PRIMARY,
        )
        .values_list("muscle_group_id", flat=True)
    )

    excluded_exercise_ids = set(
        UserExerciseProfile.objects
        .filter(user=user, is_excluded=True)
        .values_list("exercise_id", flat=True)
    )
    excluded_exercise_ids.update(circuit_exercise_ids)

    existing_warmups = list(
        session.session_exercises
        .filter(block_type=WorkoutSessionExercise.BlockType.WARMUP)
        .select_related("exercise")
        .order_by("position")
    )
    existing_cooldowns = list(
        session.session_exercises
        .filter(block_type=WorkoutSessionExercise.BlockType.COOLDOWN)
        .select_related("exercise")
        .order_by("position")
    )

    warmup_plan = _build_timed_plan(
        movement_pattern=Exercise.MovementPattern.MOBILITY,
        primary_muscle_ids=primary_muscle_ids,
        excluded_exercise_ids=excluded_exercise_ids,
        target_seconds=warmup_minutes * 60,
    )

    cooldown_plan = _build_timed_plan(
        movement_pattern=Exercise.MovementPattern.STRETCHING,
        primary_muscle_ids=primary_muscle_ids,
        excluded_exercise_ids=excluded_exercise_ids,
        target_seconds=cooldown_minutes * 60,
    )

    # Keep the previous generator's fallback behavior if a dedicated catalog
    # has not been populated yet.
    if not warmup_plan:
        warmup_plan = _plan_from_existing_items(
            existing_warmups,
            warmup_minutes * 60,
        )

    if not cooldown_plan:
        cooldown_plan = _build_timed_plan(
            movement_pattern=Exercise.MovementPattern.MOBILITY,
            primary_muscle_ids=primary_muscle_ids,
            excluded_exercise_ids=excluded_exercise_ids,
            target_seconds=cooldown_minutes * 60,
        )

    if not cooldown_plan:
        cooldown_plan = _plan_from_existing_items(
            existing_cooldowns,
            cooldown_minutes * 60,
        )

    with transaction.atomic():
        session.session_exercises.filter(
            block_type__in=[
                WorkoutSessionExercise.BlockType.WARMUP,
                WorkoutSessionExercise.BlockType.COOLDOWN,
            ]
        ).delete()

        # Move circuit rows out of the way before re-numbering because
        # (session, position) is unique.
        session.session_exercises.filter(
            block_type=WorkoutSessionExercise.BlockType.CIRCUIT,
        ).update(position=F("position") + 100)

        position = 1

        for exercise, duration_seconds in warmup_plan:
            _create_timed_session_exercise(
                session=session,
                exercise=exercise,
                position=position,
                block_type=WorkoutSessionExercise.BlockType.WARMUP,
                duration_seconds=duration_seconds,
                rest_seconds=15,
            )
            position += 1

        for item in circuit_items:
            item.position = position
            item.save(update_fields=["position"])
            position += 1

        for exercise, duration_seconds in cooldown_plan:
            _create_timed_session_exercise(
                session=session,
                exercise=exercise,
                position=position,
                block_type=WorkoutSessionExercise.BlockType.COOLDOWN,
                duration_seconds=duration_seconds,
                rest_seconds=0,
            )
            position += 1

    return session


def _build_timed_plan(
    movement_pattern,
    primary_muscle_ids,
    excluded_exercise_ids,
    target_seconds,
):
    candidates = list(
        Exercise.objects
        .filter(
            is_active=True,
            movement_pattern=movement_pattern,
        )
        .exclude(id__in=excluded_exercise_ids)
        .prefetch_related("exercise_muscles")
        .distinct()
    )

    if not candidates or target_seconds <= 0:
        return []

    random.shuffle(candidates)
    uncovered_muscle_ids = set(primary_muscle_ids)
    selected = []
    remaining_seconds = target_seconds

    while candidates and remaining_seconds > 0:
        best_index = 0
        best_score = -1

        for index, exercise in enumerate(candidates):
            exercise_primary_ids = {
                item.muscle_group_id
                for item in exercise.exercise_muscles.all()
                if item.role == ExerciseMuscle.MuscleRole.PRIMARY
            }
            score = len(exercise_primary_ids & uncovered_muscle_ids)

            if score > best_score:
                best_index = index
                best_score = score

        exercise = candidates.pop(best_index)
        exercise_primary_ids = {
            item.muscle_group_id
            for item in exercise.exercise_muscles.all()
            if item.role == ExerciseMuscle.MuscleRole.PRIMARY
        }
        uncovered_muscle_ids.difference_update(exercise_primary_ids)

        default_duration = (
            exercise.default_duration_seconds
            or DEFAULT_EXERCISE_DURATION_SECONDS
        )
        duration_seconds = min(default_duration, remaining_seconds)
        selected.append([exercise, duration_seconds])
        remaining_seconds -= duration_seconds

    if selected and remaining_seconds > 0:
        selected[-1][1] += remaining_seconds

    return [(exercise, duration) for exercise, duration in selected]


def _plan_from_existing_items(items, target_seconds):
    exercises = [item.exercise for item in items]

    if not exercises or target_seconds <= 0:
        return []

    selected = []
    remaining_seconds = target_seconds

    for exercise in exercises:
        if remaining_seconds <= 0:
            break

        default_duration = (
            exercise.default_duration_seconds
            or DEFAULT_EXERCISE_DURATION_SECONDS
        )
        duration_seconds = min(default_duration, remaining_seconds)
        selected.append([exercise, duration_seconds])
        remaining_seconds -= duration_seconds

    if selected and remaining_seconds > 0:
        selected[-1][1] += remaining_seconds

    return [(exercise, duration) for exercise, duration in selected]


def _create_timed_session_exercise(
    session,
    exercise,
    position,
    block_type,
    duration_seconds,
    rest_seconds,
):
    return WorkoutSessionExercise.objects.create(
        session=session,
        exercise=exercise,
        block_type=block_type,
        position=position,
        target_sets=1,
        target_reps_min=exercise.default_reps_min,
        target_reps_max=exercise.default_reps_max,
        target_weight_kg=None,
        target_duration_seconds=duration_seconds,
        rest_seconds=rest_seconds,
    )

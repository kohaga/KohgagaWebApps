import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import (
    Exercise,
    ExerciseMuscle,
    UserExerciseProfile,
    WorkoutSession,
    WorkoutSessionExercise,
)


WORKOUT_PROFILES = {
    "full_body": {
        "label": "Teljes test",
        "focus": [
            {"movement_patterns": [Exercise.MovementPattern.SQUAT, Exercise.MovementPattern.HINGE]},
            {"movement_patterns": [Exercise.MovementPattern.PUSH]},
            {"movement_patterns": [Exercise.MovementPattern.PULL]},
            {"muscle_groups": ["Törzs"]},
        ],
    },
    "chest_arms": {
        "label": "Mell + kar",
        "focus": [
            {"muscle_groups": ["Mell"], "movement_patterns": [Exercise.MovementPattern.PUSH]},
            {"muscle_groups": ["Bicepsz"]},
            {"muscle_groups": ["Tricepsz"]},
            {"movement_patterns": [Exercise.MovementPattern.ARMS]},
        ],
    },
    "back_shoulders": {
        "label": "Hát + váll",
        "focus": [
            {"muscle_groups": ["Hát", "Széles hátizom"], "movement_patterns": [Exercise.MovementPattern.PULL]},
            {"muscle_groups": ["Váll"]},
            {"muscle_groups": ["Törzs"]},
            {"movement_patterns": [Exercise.MovementPattern.PULL]},
        ],
    },
    "legs_core": {
        "label": "Láb + törzs",
        "focus": [
            {"movement_patterns": [Exercise.MovementPattern.SQUAT]},
            {"movement_patterns": [Exercise.MovementPattern.HINGE]},
            {"muscle_groups": ["Farizom", "Comb elülső része", "Comb hátsó része"]},
            {"muscle_groups": ["Törzs"]},
        ],
    },
    "push": {
        "label": "Push",
        "focus": [
            {"muscle_groups": ["Mell"], "movement_patterns": [Exercise.MovementPattern.PUSH]},
            {"muscle_groups": ["Váll"]},
            {"muscle_groups": ["Tricepsz"]},
            {"movement_patterns": [Exercise.MovementPattern.PUSH]},
        ],
    },
    "pull": {
        "label": "Pull",
        "focus": [
            {"muscle_groups": ["Hát", "Széles hátizom"], "movement_patterns": [Exercise.MovementPattern.PULL]},
            {"muscle_groups": ["Bicepsz"]},
            {"movement_patterns": [Exercise.MovementPattern.PULL]},
            {"muscle_groups": ["Törzs"]},
        ],
    },
}


SUPPLEMENTARY_SELECTORS = [
    {"muscle_groups": ["Törzs"]},
    {"movement_patterns": [Exercise.MovementPattern.CORE]},
    {"movement_patterns": [Exercise.MovementPattern.ARMS]},
    {"movement_patterns": [Exercise.MovementPattern.PULL]},
    {"movement_patterns": [Exercise.MovementPattern.PUSH]},
    {"movement_patterns": [Exercise.MovementPattern.HINGE]},
    {"movement_patterns": [Exercise.MovementPattern.SQUAT]},
]


def get_workout_profile_choices():
    return [
        {
            "value": key,
            "label": profile["label"],
        }
        for key, profile in WORKOUT_PROFILES.items()
    ]


def generate_workout_for_user(
    user,
    planned_duration_minutes=45,
    workout_profile="full_body",
    circuit_rounds=3,
    circuit_exercise_count=3,
):
    """
    Generates a circuit workout:
    warmup -> selected circuit exercises x selected rounds -> cooldown.
    If the selected profile does not have enough focus exercises,
    supplementary exercises are used as fallback.
    """

    profile = WORKOUT_PROFILES.get(workout_profile, WORKOUT_PROFILES["full_body"])

    circuit_rounds = _clamp_int(circuit_rounds, min_value=2, max_value=4, default=3)
    circuit_exercise_count = _clamp_int(
        circuit_exercise_count,
        min_value=3,
        max_value=5,
        default=3,
    )

    excluded_exercise_ids = _get_excluded_exercise_ids(user)
    recent_exercise_ids = _get_recent_exercise_ids(user)

    warmup = _select_exercise_by_selector(
        selector={"movement_patterns": [Exercise.MovementPattern.CARDIO]},
        excluded_exercise_ids=excluded_exercise_ids,
        recent_exercise_ids=set(),
        already_selected_ids=set(),
    )

    selected_exercise_ids = set()
    circuit_exercises = []

    focus_selectors = profile["focus"]

    for selector in focus_selectors:
        if len(circuit_exercises) >= circuit_exercise_count:
            break

        exercise = _select_exercise_by_selector(
            selector=selector,
            excluded_exercise_ids=excluded_exercise_ids,
            recent_exercise_ids=recent_exercise_ids,
            already_selected_ids=selected_exercise_ids,
        )

        if exercise:
            circuit_exercises.append(exercise)
            selected_exercise_ids.add(exercise.id)

    while len(circuit_exercises) < circuit_exercise_count:
        exercise = _select_supplementary_exercise(
            excluded_exercise_ids=excluded_exercise_ids,
            recent_exercise_ids=recent_exercise_ids,
            already_selected_ids=selected_exercise_ids,
        )

        if not exercise:
            break

        circuit_exercises.append(exercise)
        selected_exercise_ids.add(exercise.id)

    cooldown_excluded_ids = set(selected_exercise_ids)

    if warmup:
        cooldown_excluded_ids.add(warmup.id)

    cooldown = _select_exercise_by_selector(
        selector={"movement_patterns": [Exercise.MovementPattern.CARDIO]},
        excluded_exercise_ids=excluded_exercise_ids,
        recent_exercise_ids=set(),
        already_selected_ids=cooldown_excluded_ids,
    )

    if not cooldown:
        cooldown = warmup

    if not warmup and not circuit_exercises:
        raise ValueError("Nincs elérhető gyakorlat az edzés generálásához.")

    with transaction.atomic():
        session = WorkoutSession.objects.create(
            user=user,
            title=f"Mai köredzés - {profile['label']}",
            status=WorkoutSession.Status.PLANNED,
            generation_type=WorkoutSession.GenerationType.GENERATED,
            workout_profile=workout_profile,
            circuit_rounds=circuit_rounds,
            circuit_exercise_count=circuit_exercise_count,
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
                target_sets=circuit_rounds,
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


def _clamp_int(value, min_value, max_value, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default

    return max(min_value, min(value, max_value))


def _get_excluded_exercise_ids(user):
    return set(
        UserExerciseProfile.objects
        .filter(user=user, is_excluded=True)
        .values_list("exercise_id", flat=True)
    )


def _get_recent_exercise_ids(user):
    recent_since = timezone.now() - timedelta(days=7)

    return set(
        WorkoutSessionExercise.objects
        .filter(
            session__user=user,
            session__created_at__gte=recent_since,
            session__status__in=[
                WorkoutSession.Status.PLANNED,
                WorkoutSession.Status.IN_PROGRESS,
                WorkoutSession.Status.COMPLETED,
            ],
        )
        .values_list("exercise_id", flat=True)
    )


def _select_exercise_by_selector(
    selector,
    excluded_exercise_ids,
    recent_exercise_ids,
    already_selected_ids,
):
    base_queryset = Exercise.objects.filter(is_active=True)

    movement_patterns = selector.get("movement_patterns") or []
    muscle_groups = selector.get("muscle_groups") or []

    if movement_patterns:
        base_queryset = base_queryset.filter(
            movement_pattern__in=movement_patterns,
        )

    if muscle_groups:
        base_queryset = base_queryset.filter(
            exercise_muscles__muscle_group__name__in=muscle_groups,
        )

    base_queryset = (
        base_queryset
        .exclude(id__in=excluded_exercise_ids)
        .exclude(id__in=already_selected_ids)
        .distinct()
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


def _select_supplementary_exercise(
    excluded_exercise_ids,
    recent_exercise_ids,
    already_selected_ids,
):
    for selector in SUPPLEMENTARY_SELECTORS:
        exercise = _select_exercise_by_selector(
            selector=selector,
            excluded_exercise_ids=excluded_exercise_ids,
            recent_exercise_ids=recent_exercise_ids,
            already_selected_ids=already_selected_ids,
        )

        if exercise:
            return exercise

    base_queryset = (
        Exercise.objects
        .filter(is_active=True)
        .exclude(id__in=excluded_exercise_ids)
        .exclude(id__in=already_selected_ids)
        .exclude(movement_pattern=Exercise.MovementPattern.CARDIO)
        .distinct()
    )

    exercises = list(base_queryset.exclude(id__in=recent_exercise_ids))

    if not exercises:
        exercises = list(base_queryset)

    if not exercises:
        return None

    return random.choice(exercises)


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
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
    "aerobic_video": {
        "label": "Aerobic videó",
        "focus": [
            {
                "movement_patterns": [
                    Exercise.MovementPattern.AEROBIC_VIDEO
                ]
            },
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


MAIN_WORKOUT_EXCLUDED_PATTERNS = [
    Exercise.MovementPattern.CARDIO,
    Exercise.MovementPattern.MOBILITY,
    Exercise.MovementPattern.STRETCHING,
]


def get_workout_profile_choices():
    return [
        {
            "value": key,
            "label": profile["label"],
        }
        for key, profile in WORKOUT_PROFILES.items()
    ]


def get_training_goal_choices():
    return [
        {
            "value": value,
            "label": label,
        }
        for value, label in WorkoutSession.TrainingGoal.choices
    ]


def generate_workout_for_user(
    user,
    planned_duration_minutes=45,
    workout_profile="full_body",
    training_goal=WorkoutSession.TrainingGoal.CALORIE_BURN,
    circuit_rounds=3,
    circuit_exercise_count=3,
):
    """
    Generates a workout with two execution modes:
    - calorie burn: warmup -> A-B-C by rounds -> cooldown
    - muscle gain: warmup -> all sets of A, then B, then C -> cooldown

    If the selected profile does not have enough focus exercises,
    supplementary exercises are used as fallback.
    """

    profile = WORKOUT_PROFILES.get(workout_profile, WORKOUT_PROFILES["full_body"])
    if workout_profile == "aerobic_video":
        return _generate_aerobic_video_workout(
            user=user,
            planned_duration_minutes=planned_duration_minutes,
        )

    valid_training_goals = {
        value for value, _label in WorkoutSession.TrainingGoal.choices
    }
    if training_goal not in valid_training_goals:
        training_goal = WorkoutSession.TrainingGoal.CALORIE_BURN

    circuit_rounds = _clamp_int(circuit_rounds, min_value=2, max_value=4, default=3)
    circuit_exercise_count = _clamp_int(
        circuit_exercise_count,
        min_value=3,
        max_value=5,
        default=3,
    )

    excluded_exercise_ids = _get_excluded_exercise_ids(user)
    recent_exercise_ids = _get_recent_exercise_ids(user)

    warmup_movement_pattern = (
        Exercise.MovementPattern.MOBILITY
        if training_goal == WorkoutSession.TrainingGoal.MUSCLE_GAIN
        else Exercise.MovementPattern.CARDIO
    )

    warmup = _select_exercise_by_selector(
        selector={"movement_patterns": [warmup_movement_pattern]},
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
            excluded_movement_patterns=MAIN_WORKOUT_EXCLUDED_PATTERNS,
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

    cooldown_movement_pattern = (
        Exercise.MovementPattern.STRETCHING
        if training_goal == WorkoutSession.TrainingGoal.MUSCLE_GAIN
        else Exercise.MovementPattern.CARDIO
    )

    cooldown = _select_exercise_by_selector(
        selector={"movement_patterns": [cooldown_movement_pattern]},
        excluded_exercise_ids=excluded_exercise_ids,
        recent_exercise_ids=set(),
        already_selected_ids=cooldown_excluded_ids,
    )

    # Backward-compatible fallback: if no stretching exercise exists yet,
    # use a mobility exercise instead of dropping the cooldown completely.
    if not cooldown and training_goal == WorkoutSession.TrainingGoal.MUSCLE_GAIN:
        cooldown = _select_exercise_by_selector(
            selector={"movement_patterns": [Exercise.MovementPattern.MOBILITY]},
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
            title=f"Mai edzés - {profile['label']}",
            status=WorkoutSession.Status.PLANNED,
            generation_type=WorkoutSession.GenerationType.GENERATED,
            workout_profile=workout_profile,
            training_goal=training_goal,
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



def replace_session_exercise_for_user(user, session_exercise):
    """
    Replaces an unstarted circuit exercise with a similar active exercise.

    Selection priority:
    1. same movement pattern and same primary muscle group,
    2. same movement pattern,
    3. same primary muscle group.

    Exercises already present in the same workout and exercises excluded by
    the user are not selected. The number of sets and rest time stay unchanged,
    while reps and target weight are refreshed for the replacement exercise.
    """

    if session_exercise.session.user_id != user.id:
        raise ValueError("Ez a gyakorlat nem ehhez a felhasználóhoz tartozik.")

    if session_exercise.block_type != WorkoutSessionExercise.BlockType.CIRCUIT:
        raise ValueError("Csak a fő edzésblokk gyakorlatai cserélhetők.")

    if session_exercise.set_results.filter(is_completed=True).exists():
        raise ValueError(
            "Ez a gyakorlat már elkezdődött, ezért az edzésnapló védelmében nem cserélhető."
        )

    current_exercise = session_exercise.exercise

    excluded_exercise_ids = _get_excluded_exercise_ids(user)
    excluded_exercise_ids.update(
        session_exercise.session.session_exercises.values_list(
            "exercise_id",
            flat=True,
        )
    )

    recent_exercise_ids = _get_recent_exercise_ids(user)

    primary_muscle_group_ids = list(
        current_exercise.exercise_muscles
        .filter(role=ExerciseMuscle.MuscleRole.PRIMARY)
        .values_list("muscle_group_id", flat=True)
    )

    base_queryset = (
        Exercise.objects
        .filter(is_active=True)
        .exclude(id__in=excluded_exercise_ids)
        .exclude(movement_pattern__in=MAIN_WORKOUT_EXCLUDED_PATTERNS)
        .distinct()
    )

    replacement = None

    if primary_muscle_group_ids:
        replacement = _choose_replacement_exercise(
            base_queryset.filter(
                movement_pattern=current_exercise.movement_pattern,
                exercise_muscles__role=ExerciseMuscle.MuscleRole.PRIMARY,
                exercise_muscles__muscle_group_id__in=primary_muscle_group_ids,
            ).distinct(),
            recent_exercise_ids,
        )

    if not replacement:
        replacement = _choose_replacement_exercise(
            base_queryset.filter(
                movement_pattern=current_exercise.movement_pattern,
            ),
            recent_exercise_ids,
        )

    if not replacement and primary_muscle_group_ids:
        replacement = _choose_replacement_exercise(
            base_queryset.filter(
                exercise_muscles__role=ExerciseMuscle.MuscleRole.PRIMARY,
                exercise_muscles__muscle_group_id__in=primary_muscle_group_ids,
            ).distinct(),
            recent_exercise_ids,
        )

    if not replacement:
        raise ValueError("Nem találtam megfelelő cseregyakorlatot.")

    user_profile = UserExerciseProfile.objects.filter(
        user=user,
        exercise=replacement,
    ).first()

    target_weight = None
    if user_profile:
        target_weight = (
            user_profile.preferred_weight_kg
            or user_profile.last_weight_kg
            or None
        )

    with transaction.atomic():
        session_exercise.exercise = replacement
        session_exercise.target_reps_min = replacement.default_reps_min
        session_exercise.target_reps_max = replacement.default_reps_max
        session_exercise.target_weight_kg = target_weight
        session_exercise.save(
            update_fields=[
                "exercise",
                "target_reps_min",
                "target_reps_max",
                "target_weight_kg",
            ]
        )

    return replacement


def _choose_replacement_exercise(queryset, recent_exercise_ids):
    preferred_exercises = list(
        queryset.exclude(id__in=recent_exercise_ids)
    )

    if preferred_exercises:
        return random.choice(preferred_exercises)

    exercises = list(queryset)

    if not exercises:
        return None

    return random.choice(exercises)


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
    excluded_movement_patterns=None,
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

    if excluded_movement_patterns:
        base_queryset = base_queryset.exclude(
            movement_pattern__in=excluded_movement_patterns,
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
            excluded_movement_patterns=MAIN_WORKOUT_EXCLUDED_PATTERNS,
        )

        if exercise:
            return exercise

    base_queryset = (
        Exercise.objects
        .filter(is_active=True)
        .exclude(id__in=excluded_exercise_ids)
        .exclude(id__in=already_selected_ids)
        .exclude(movement_pattern__in=MAIN_WORKOUT_EXCLUDED_PATTERNS)
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


def _generate_aerobic_video_workout(
    user,
    planned_duration_minutes=45,
):
    excluded_exercise_ids = _get_excluded_exercise_ids(user)
    recent_exercise_ids = _get_recent_exercise_ids(user)

    exercise = _select_exercise_by_selector(
        selector={
            "movement_patterns": [
                Exercise.MovementPattern.AEROBIC_VIDEO
            ]
        },
        excluded_exercise_ids=excluded_exercise_ids,
        recent_exercise_ids=recent_exercise_ids,
        already_selected_ids=set(),
    )

    if not exercise:
        raise ValueError(
            "Nincs elérhető Aerobic videó az adatbázisban."
        )

    with transaction.atomic():
        session = WorkoutSession.objects.create(
            user=user,
            title=f"Aerobic - {exercise.name}",
            status=WorkoutSession.Status.PLANNED,
            generation_type=WorkoutSession.GenerationType.GENERATED,
            workout_profile="aerobic_video",
            circuit_rounds=1,
            circuit_exercise_count=1,
            planned_duration_minutes=planned_duration_minutes,
        )

        _create_session_exercise(
            session=session,
            exercise=exercise,
            position=1,
            block_type=WorkoutSessionExercise.BlockType.CIRCUIT,
            target_sets=1,
            rest_seconds=0,
            user=user,
        )

    return session
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse

from .models import (
    Exercise,
    UserExerciseProfile,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSetResult,
)
from .services import generate_workout_for_user


@login_required
def exercise_list(request):
    exercises = (
        Exercise.objects
        .filter(is_active=True)
        .prefetch_related(
            "equipment",
            "exercise_muscles__muscle_group",
        )
        .order_by("movement_pattern", "name")
    )

    return render(
        request,
        "workouts/exercise_list.html",
        {
            "exercises": exercises,
        },
    )


@login_required
def exercise_detail(request, exercise_id):
    exercise = get_object_or_404(
        Exercise.objects.prefetch_related(
            "equipment",
            "exercise_muscles__muscle_group",
        ),
        id=exercise_id,
        is_active=True,
    )

    return render(
        request,
        "workouts/exercise_detail.html",
        {
            "exercise": exercise,
        },
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
            "Már van egy nyitott edzésed. Először azt fejezd be vagy töröld."
        )
        return redirect(
            "workouts:workout_session_detail",
            session_id=open_session.id,
        )

    try:
        session = generate_workout_for_user(
            user=request.user,
            planned_duration_minutes=45,
        )
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("workouts:exercise_list")

    messages.success(request, "A mai edzés elkészült.")
    return redirect("workouts:workout_session_detail", session_id=session.id)


@login_required
def workout_session_detail(request, session_id):
    session = get_object_or_404(
        WorkoutSession.objects.prefetch_related(
            "session_exercises__exercise",
            "session_exercises__exercise__equipment",
            "session_exercises__exercise__exercise_muscles__muscle_group",
            "session_exercises__set_results",
        ),
        id=session_id,
        user=request.user,
    )

    return render(
        request,
        "workouts/workout_session_detail.html",
        {
            "session": session,
        },
    )


@login_required
def start_workout(request, session_id):
    if request.method != "POST":
        return redirect("workouts:train_workout", session_id=session_id)

    session = get_object_or_404(
        WorkoutSession,
        id=session_id,
        user=request.user,
    )

    if session.status == WorkoutSession.Status.PLANNED:
        session.status = WorkoutSession.Status.IN_PROGRESS
        session.started_at = timezone.now()
        session.save(update_fields=["status", "started_at"])

    messages.success(request, "Edzés elindítva.")
    return redirect("workouts:workout_session_detail", session_id=session.id)


@login_required
def finish_workout(request, session_id):
    if request.method != "POST":
        return redirect("workouts:workout_session_detail", session_id=session_id)

    session = get_object_or_404(
        WorkoutSession,
        id=session_id,
        user=request.user,
    )

    now = timezone.now()
    session.status = WorkoutSession.Status.COMPLETED
    session.finished_at = now

    if session.started_at:
        session.actual_duration_seconds = int((now - session.started_at).total_seconds())

    session.save(
        update_fields=[
            "status",
            "finished_at",
            "actual_duration_seconds",
        ]
    )

    messages.success(request, "Edzés lezárva.")
    return redirect("workouts:workout_session_detail", session_id=session.id)


@login_required
def workout_exercise_result(request, session_id, session_exercise_id):
    session = get_object_or_404(
        WorkoutSession,
        id=session_id,
        user=request.user,
    )

    session_exercise = get_object_or_404(
        WorkoutSessionExercise.objects.select_related("exercise", "session"),
        id=session_exercise_id,
        session=session,
    )

    if request.method == "POST":
        try:
            _save_set_results(request, session_exercise)
        except ValueError as error:
            messages.error(request, str(error))
            return redirect(
                "workouts:workout_exercise_result",
                session_id=session.id,
                session_exercise_id=session_exercise.id,
            )

        _update_user_exercise_profile(request.user, session_exercise)

        next_action = request.POST.get("next_action")

        if next_action == "next":
            next_exercise = (
                WorkoutSessionExercise.objects
                .filter(
                    session=session,
                    position__gt=session_exercise.position,
                )
                .order_by("position")
                .first()
            )

            if next_exercise:
                messages.success(request, "Gyakorlat eredménye mentve.")
                return redirect(
                    "workouts:workout_exercise_result",
                    session_id=session.id,
                    session_exercise_id=next_exercise.id,
                )

            messages.info(request, "Ez volt az utolsó gyakorlat.")
            return redirect("workouts:workout_session_detail", session_id=session.id)

        messages.success(request, "Gyakorlat eredménye mentve.")
        return redirect("workouts:workout_session_detail", session_id=session.id)

    existing_results = {
        item.set_number: item
        for item in session_exercise.set_results.all()
    }

    set_rows = []

    for set_number in range(1, session_exercise.target_sets + 1):
        set_rows.append(
            {
                "set_number": set_number,
                "result": existing_results.get(set_number),
            }
        )

    return render(
        request,
        "workouts/workout_exercise_result.html",
        {
            "session": session,
            "session_exercise": session_exercise,
            "set_rows": set_rows,
        },
    )


@login_required
def train_workout(request, session_id, session_exercise_id=None):
    session = get_object_or_404(
        WorkoutSession,
        id=session_id,
        user=request.user,
    )

    if session.status == WorkoutSession.Status.COMPLETED:
        messages.info(request, "Ez az edzés már le van zárva.")
        return redirect("workouts:workout_session_detail", session_id=session.id)

    if session.status == WorkoutSession.Status.PLANNED:
        session.status = WorkoutSession.Status.IN_PROGRESS
        session.started_at = timezone.now()
        session.save(update_fields=["status", "started_at"])

    current_step = _get_current_workout_step(session)

    if not current_step:
        messages.info(request, "Minden lépés rögzítve lett. Zárd le az edzést.")
        return redirect("workouts:workout_session_detail", session_id=session.id)

    session_exercise = current_step["session_exercise"]
    round_number = current_step["round_number"]

    if request.method == "POST":
        try:
            _save_step_result(request, session_exercise, round_number)
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("workouts:train_workout", session_id=session.id)

        _update_user_exercise_profile(request.user, session_exercise)

        next_step = _get_current_workout_step(session)

        if next_step:
            rest_url = (
                f"{reverse('workouts:workout_rest', kwargs={'session_id': session.id})}"
                f"?seconds={session_exercise.rest_seconds}"
            )
            return redirect(rest_url)

        messages.success(request, "Ez volt az utolsó lépés. Az edzés lezárható.")
        return redirect("workouts:workout_session_detail", session_id=session.id)

    result = WorkoutSetResult.objects.filter(
        session_exercise=session_exercise,
        set_number=round_number,
    ).first()

    total_steps = _count_total_workout_steps(session)
    completed_steps = _count_completed_workout_steps(session)

    progress_percent = 0
    if total_steps:
        progress_percent = int(((completed_steps + 1) / total_steps) * 100)

    user_profile = UserExerciseProfile.objects.filter(
        user=request.user,
        exercise=session_exercise.exercise,
    ).first()

    initial_reps = ""
    initial_weight_kg = ""
    initial_rpe = ""
    initial_note = ""

    if result:
        initial_reps = result.reps or ""
        initial_weight_kg = result.weight_kg or ""
        initial_rpe = result.rpe or ""
        initial_note = result.note or ""
    elif user_profile:
        initial_reps = user_profile.last_reps or ""
        initial_weight_kg = user_profile.last_weight_kg or ""

    return render(
        request,
        "workouts/train_exercise.html",
        {
            "session": session,
            "session_exercise": session_exercise,
            "round_number": round_number,
            "total_rounds": current_step["total_rounds"],
            "block_label": current_step["block_label"],
            "result": result,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "progress_percent": progress_percent,
            "initial_reps": initial_reps,
            "initial_weight_kg": initial_weight_kg,
            "initial_rpe": initial_rpe,
            "initial_note": initial_note,
        },
    )


@login_required
def workout_rest(request, session_id):
    session = get_object_or_404(
        WorkoutSession,
        id=session_id,
        user=request.user,
    )

    if session.status != WorkoutSession.Status.IN_PROGRESS:
        return redirect("workouts:workout_session_detail", session_id=session.id)

    next_step = _get_current_workout_step(session)

    if not next_step:
        return redirect("workouts:workout_session_detail", session_id=session.id)

    try:
        rest_seconds = int(request.GET.get("seconds", "60"))
    except ValueError:
        rest_seconds = 60

    return render(
        request,
        "workouts/rest.html",
        {
            "session": session,
            "next_step": next_step,
            "next_session_exercise": next_step["session_exercise"],
            "rest_seconds": rest_seconds,
        },
    )


def _has_any_set_data(request, target_sets):
    for set_number in range(1, target_sets + 1):
        reps_raw = request.POST.get(f"reps_{set_number}", "").strip()
        weight_raw = request.POST.get(f"weight_{set_number}", "").strip()
        rpe_raw = request.POST.get(f"rpe_{set_number}", "").strip()
        note = request.POST.get(f"note_{set_number}", "").strip()

        if reps_raw or weight_raw or rpe_raw or note:
            return True

    return False

def _save_set_results(request, session_exercise):
    has_completed_set = False

    for set_number in range(1, session_exercise.target_sets + 1):
        reps_raw = request.POST.get(f"reps_{set_number}", "").strip()
        weight_raw = request.POST.get(f"weight_{set_number}", "").strip()
        rpe_raw = request.POST.get(f"rpe_{set_number}", "").strip()
        note = request.POST.get(f"note_{set_number}", "").strip()

        if not reps_raw and not weight_raw and not rpe_raw and not note:
            WorkoutSetResult.objects.filter(
                session_exercise=session_exercise,
                set_number=set_number,
            ).delete()
            continue

        reps = _parse_int(reps_raw, "Ismétlés")
        weight_kg = _parse_decimal(weight_raw, "Súly")
        rpe = _parse_int(rpe_raw, "RPE")

        if rpe is not None and not 1 <= rpe <= 10:
            raise ValueError("Az RPE értéke 1 és 10 között lehet.")

        WorkoutSetResult.objects.update_or_create(
            session_exercise=session_exercise,
            set_number=set_number,
            defaults={
                "reps": reps,
                "weight_kg": weight_kg,
                "rpe": rpe,
                "is_completed": True,
                "note": note,
            },
        )

        has_completed_set = True

    session_exercise.is_completed = has_completed_set
    session_exercise.save(update_fields=["is_completed"])


def _update_user_exercise_profile(user, session_exercise):
    completed_sets = list(
        session_exercise.set_results
        .filter(is_completed=True)
        .order_by("set_number")
    )

    if not completed_sets:
        return

    profile, _ = UserExerciseProfile.objects.get_or_create(
        user=user,
        exercise=session_exercise.exercise,
    )

    last_set_with_weight = next(
        (item for item in reversed(completed_sets) if item.weight_kg is not None),
        None,
    )
    last_set_with_reps = next(
        (item for item in reversed(completed_sets) if item.reps is not None),
        None,
    )

    max_weight = max(
        [item.weight_kg for item in completed_sets if item.weight_kg is not None],
        default=None,
    )

    if last_set_with_weight:
        profile.last_weight_kg = last_set_with_weight.weight_kg

    if last_set_with_reps:
        profile.last_reps = last_set_with_reps.reps

    if max_weight is not None:
        if profile.best_weight_kg is None or max_weight > profile.best_weight_kg:
            profile.best_weight_kg = max_weight

    profile.save()


def _parse_int(value, field_name):
    if value == "":
        return None

    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Hibás számformátum: {field_name}.")


def _parse_decimal(value, field_name):
    if value == "":
        return None

    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"Hibás számformátum: {field_name}.")

@login_required
def delete_workout_session(request, session_id):
    if request.method != "POST":
        return redirect("workouts:workout_session_detail", session_id=session_id)

    session = get_object_or_404(
        WorkoutSession,
        id=session_id,
        user=request.user,
    )

    if session.status == WorkoutSession.Status.COMPLETED:
        messages.error(
            request,
            "Lezárt edzést most nem törlünk a felületről, hogy ne vesszen el a teljesítménytörténet."
        )
        return redirect("workouts:workout_session_detail", session_id=session.id)

    session.delete()

    messages.success(request, "Az edzés törölve lett.")
    return redirect("workouts:exercise_list")

def _get_current_workout_step(session):
    session_exercises = list(
        session.session_exercises
        .select_related("exercise")
        .prefetch_related("set_results")
        .order_by("position")
    )

    warmup_items = [
        item for item in session_exercises
        if item.block_type == WorkoutSessionExercise.BlockType.WARMUP
    ]

    for item in warmup_items:
        if not _has_completed_round(item, 1):
            return {
                "session_exercise": item,
                "round_number": 1,
                "total_rounds": 1,
                "block_label": "Bemelegítés",
            }

    circuit_items = [
        item for item in session_exercises
        if item.block_type == WorkoutSessionExercise.BlockType.CIRCUIT
    ]

    max_rounds = max(
        [item.target_sets for item in circuit_items],
        default=0,
    )

    for round_number in range(1, max_rounds + 1):
        for item in circuit_items:
            if round_number <= item.target_sets and not _has_completed_round(item, round_number):
                return {
                    "session_exercise": item,
                    "round_number": round_number,
                    "total_rounds": item.target_sets,
                    "block_label": "Köredzés",
                }

    cooldown_items = [
        item for item in session_exercises
        if item.block_type == WorkoutSessionExercise.BlockType.COOLDOWN
    ]

    for item in cooldown_items:
        if not _has_completed_round(item, 1):
            return {
                "session_exercise": item,
                "round_number": 1,
                "total_rounds": 1,
                "block_label": "Levezetés",
            }

    return None


def _has_completed_round(session_exercise, round_number):
    return any(
        item.set_number == round_number and item.is_completed
        for item in session_exercise.set_results.all()
    )


def _save_step_result(request, session_exercise, round_number):
    reps_raw = request.POST.get("reps", "").strip()
    weight_raw = request.POST.get("weight", "").strip()
    rpe_raw = request.POST.get("rpe", "").strip()
    note = request.POST.get("note", "").strip()

    reps = _parse_int(reps_raw, "Ismétlés")
    weight_kg = _parse_decimal(weight_raw, "Súly")
    rpe = _parse_int(rpe_raw, "RPE")

    if rpe is not None and not 1 <= rpe <= 10:
        raise ValueError("Az RPE értéke 1 és 10 között lehet.")

    WorkoutSetResult.objects.update_or_create(
        session_exercise=session_exercise,
        set_number=round_number,
        defaults={
            "reps": reps,
            "weight_kg": weight_kg,
            "rpe": rpe,
            "is_completed": True,
            "note": note,
        },
    )

    completed_rounds = set(
        session_exercise.set_results
        .filter(is_completed=True)
        .values_list("set_number", flat=True)
    )
    completed_rounds.add(round_number)

    required_rounds = set(range(1, session_exercise.target_sets + 1))

    session_exercise.is_completed = required_rounds.issubset(completed_rounds)
    session_exercise.save(update_fields=["is_completed"])


def _count_total_workout_steps(session):
    return sum(
        item.target_sets
        for item in session.session_exercises.all()
    )


def _count_completed_workout_steps(session):
    total = 0

    session_exercises = (
        session.session_exercises
        .prefetch_related("set_results")
        .all()
    )

    for item in session_exercises:
        completed_rounds = {
            result.set_number
            for result in item.set_results.all()
            if result.is_completed
        }

        for round_number in range(1, item.target_sets + 1):
            if round_number in completed_rounds:
                total += 1

    return total
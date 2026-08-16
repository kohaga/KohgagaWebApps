from django.contrib import admin

from .models import (
    Equipment,
    Exercise,
    ExerciseMuscle,
    MuscleGroup,
    UserExerciseProfile,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSetResult,
)


class ExerciseMuscleInline(admin.TabularInline):
    model = ExerciseMuscle
    extra = 1


class WorkoutSetResultInline(admin.TabularInline):
    model = WorkoutSetResult
    extra = 1


class WorkoutSessionExerciseInline(admin.TabularInline):
    model = WorkoutSessionExercise
    extra = 1
    autocomplete_fields = ["exercise"]


@admin.register(MuscleGroup)
class MuscleGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]
    search_fields = ["name", "description"]


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]
    search_fields = ["name", "description"]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "movement_pattern",
        "difficulty",
        "default_sets",
        "default_reps_min",
        "default_reps_max",
        "default_rest_seconds",
        "default_duration_seconds",
        "is_bodyweight",
        "is_active",
    ]
    list_filter = [
        "movement_pattern",
        "difficulty",
        "is_bodyweight",
        "is_unilateral",
        "is_active",
        "equipment",
        "muscle_groups",
    ]
    search_fields = [
        "name",
        "description",
        "coaching_cues",
    ]
    filter_horizontal = ["equipment"]
    inlines = [ExerciseMuscleInline]


@admin.register(ExerciseMuscle)
class ExerciseMuscleAdmin(admin.ModelAdmin):
    list_display = ["exercise", "muscle_group", "role"]
    list_filter = ["role", "muscle_group"]
    search_fields = ["exercise__name", "muscle_group__name"]


@admin.register(UserExerciseProfile)
class UserExerciseProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "exercise",
        "preferred_weight_kg",
        "last_weight_kg",
        "best_weight_kg",
        "preferred_reps",
        "last_reps",
        "is_favorite",
        "is_excluded",
    ]
    list_filter = [
        "is_favorite",
        "is_excluded",
        "exercise__movement_pattern",
    ]
    search_fields = [
        "user__username",
        "exercise__name",
        "note",
    ]
    autocomplete_fields = ["exercise"]


@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "title",
        "status",
        "generation_type",
        "workout_profile",
        "circuit_rounds",
        "circuit_exercise_count",
        "warmup_duration_minutes",
        "cooldown_duration_minutes",
        "created_at",
        "started_at",
        "finished_at",
        "planned_duration_minutes",
        "actual_duration_seconds",
    ]
    list_filter = [
        "status",
        "generation_type",
        "created_at",
    ]
    search_fields = [
        "user__username",
        "title",
        "note",
    ]
    inlines = [WorkoutSessionExerciseInline]


@admin.register(WorkoutSessionExercise)
class WorkoutSessionExerciseAdmin(admin.ModelAdmin):
    list_display = [
        "session",
        "block_type",
        "position",
        "exercise",
        "target_sets",
        "target_reps_min",
        "target_reps_max",
        "target_weight_kg",
        "target_duration_seconds",
        "rest_seconds",
        "is_completed",
    ]
    list_filter = [
        "is_completed",
        "exercise__movement_pattern",
        "block_type",
    ]
    search_fields = [
        "session__title",
        "exercise__name",
        "note",
    ]
    autocomplete_fields = ["exercise"]
    inlines = [WorkoutSetResultInline]


@admin.register(WorkoutSetResult)
class WorkoutSetResultAdmin(admin.ModelAdmin):
    list_display = [
        "session_exercise",
        "set_number",
        "reps",
        "weight_kg",
        "rpe",
        "is_completed",
        "created_at",
    ]
    list_filter = [
        "is_completed",
        "rpe",
        "created_at",
    ]
    search_fields = [
        "session_exercise__exercise__name",
        "note",
    ]

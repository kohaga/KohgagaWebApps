from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from urllib.parse import parse_qs, urlparse


class MuscleGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Equipment(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Exercise(models.Model):
    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Kezdő"
        INTERMEDIATE = "intermediate", "Középhaladó"
        ADVANCED = "advanced", "Haladó"

    class MovementPattern(models.TextChoices):
        CARDIO = "cardio", "Kardió"
        SQUAT = "squat", "Guggolás"
        HINGE = "hinge", "Csípőhajlítás / hátsó lánc"
        PUSH = "push", "Nyomás"
        PULL = "pull", "Húzás"
        CORE = "core", "Törzs"
        ARMS = "arms", "Kar"
        MOBILITY = "mobility", "Mobilitás"
        STRETCHING = "stretching", "Nyújtás"
        AEROBIC_VIDEO = "aerobic_video", "Aerobic videó"
        OTHER = "other", "Egyéb"

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField()
    coaching_cues = models.TextField(blank=True)
    video_url = models.URLField(blank=True)

    movement_pattern = models.CharField(
        max_length=30,
        choices=MovementPattern.choices,
        default=MovementPattern.OTHER,
    )

    difficulty = models.CharField(
        max_length=30,
        choices=Difficulty.choices,
        default=Difficulty.BEGINNER,
    )

    default_sets = models.PositiveSmallIntegerField(default=3)
    default_reps_min = models.PositiveSmallIntegerField(default=8)
    default_reps_max = models.PositiveSmallIntegerField(default=12)
    default_rest_seconds = models.PositiveSmallIntegerField(default=90)

    is_bodyweight = models.BooleanField(default=False)
    is_unilateral = models.BooleanField(
        default=False,
        help_text="True if the exercise is performed separately for left/right side.",
    )
    is_active = models.BooleanField(default=True)

    muscle_groups = models.ManyToManyField(
        MuscleGroup,
        through="ExerciseMuscle",
        related_name="exercises",
        blank=True,
    )

    equipment = models.ManyToManyField(
        Equipment,
        related_name="exercises",
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    @property
    def video_embed_url(self):
        if not self.video_url:
            return ""

        parsed_url = urlparse(self.video_url)

        if "youtube.com" in parsed_url.netloc:
            if parsed_url.path == "/watch":
                video_id = parse_qs(parsed_url.query).get("v", [""])[0]
                if video_id:
                    return f"https://www.youtube.com/embed/{video_id}"

            if parsed_url.path.startswith("/shorts/"):
                video_id = parsed_url.path.split("/shorts/")[-1].split("/")[0]
                if video_id:
                    return f"https://www.youtube.com/embed/{video_id}"

            if parsed_url.path.startswith("/embed/"):
                return self.video_url

        if "youtu.be" in parsed_url.netloc:
            video_id = parsed_url.path.strip("/")
            if video_id:
                return f"https://www.youtube.com/embed/{video_id}"

        return ""

    def __str__(self):
        return self.name


class ExerciseMuscle(models.Model):
    class MuscleRole(models.TextChoices):
        PRIMARY = "primary", "Elsődleges"
        SECONDARY = "secondary", "Másodlagos"
        STABILIZER = "stabilizer", "Stabilizáló"

    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="exercise_muscles",
    )
    muscle_group = models.ForeignKey(
        MuscleGroup,
        on_delete=models.CASCADE,
        related_name="exercise_muscles",
    )
    role = models.CharField(
        max_length=20,
        choices=MuscleRole.choices,
        default=MuscleRole.PRIMARY,
    )

    class Meta:
        unique_together = ["exercise", "muscle_group"]
        ordering = ["exercise__name", "role", "muscle_group__name"]

    def __str__(self):
        return f"{self.exercise} - {self.muscle_group} ({self.role})"


class UserExerciseProfile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exercise_profiles",
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="user_profiles",
    )

    preferred_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    last_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    best_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    preferred_reps = models.PositiveSmallIntegerField(null=True, blank=True)
    last_reps = models.PositiveSmallIntegerField(null=True, blank=True)

    is_favorite = models.BooleanField(default=False)
    is_excluded = models.BooleanField(
        default=False,
        help_text="If true, this exercise should not be generated for this user.",
    )

    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "exercise"]
        ordering = ["user", "exercise__name"]

    def __str__(self):
        return f"{self.user} - {self.exercise}"


class WorkoutSession(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class GenerationType(models.TextChoices):
        MANUAL = "manual", "Manual"
        GENERATED = "generated", "Generated"

    class TrainingGoal(models.TextChoices):
        CALORIE_BURN = "calorie_burn", "Kalóriaégetés"
        MUSCLE_GAIN = "muscle_gain", "Izomtömeg-növelés"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workout_sessions",
    )

    title = models.CharField(max_length=150, blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    generation_type = models.CharField(
        max_length=30,
        choices=GenerationType.choices,
        default=GenerationType.GENERATED,
    )

    workout_profile = models.CharField(
        max_length=50,
        blank=True,
    )

    training_goal = models.CharField(
        max_length=20,
        choices=TrainingGoal.choices,
        default=TrainingGoal.CALORIE_BURN,
    )

    circuit_rounds = models.PositiveSmallIntegerField(
        default=3,
    )

    circuit_exercise_count = models.PositiveSmallIntegerField(
        default=3,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    planned_duration_minutes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    actual_duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.title or 'Workout'} - {self.created_at:%Y-%m-%d}"


class WorkoutSessionExercise(models.Model):
    class BlockType(models.TextChoices):
        WARMUP = "warmup", "Bemelegítés"
        CIRCUIT = "circuit", "Köredzés"
        COOLDOWN = "cooldown", "Levezetés"

    session = models.ForeignKey(
        WorkoutSession,
        on_delete=models.CASCADE,
        related_name="session_exercises",
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.PROTECT,
        related_name="session_exercises",
    )
    block_type = models.CharField(
        max_length=20,
        choices=BlockType.choices,
        default=BlockType.CIRCUIT,
    )

    position = models.PositiveSmallIntegerField()

    target_sets = models.PositiveSmallIntegerField(default=3)
    target_reps_min = models.PositiveSmallIntegerField(default=8)
    target_reps_max = models.PositiveSmallIntegerField(default=12)
    target_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    rest_seconds = models.PositiveSmallIntegerField(default=90)

    is_completed = models.BooleanField(default=False)
    note = models.TextField(blank=True)

    class Meta:
        unique_together = ["session", "position"]
        ordering = ["session", "position"]

    def __str__(self):
        return f"{self.session} - {self.position}. {self.exercise}"


class WorkoutSetResult(models.Model):
    session_exercise = models.ForeignKey(
        WorkoutSessionExercise,
        on_delete=models.CASCADE,
        related_name="set_results",
    )

    set_number = models.PositiveSmallIntegerField()
    reps = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    rpe = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10),
        ],
        help_text="Rate of perceived exertion, 1-10.",
    )

    is_completed = models.BooleanField(default=True)
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["session_exercise", "set_number"]
        ordering = ["session_exercise", "set_number"]

    def __str__(self):
        return f"{self.session_exercise} - Set {self.set_number}"

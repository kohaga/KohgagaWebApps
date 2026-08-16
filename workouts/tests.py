from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import (
    Exercise,
    ExerciseMuscle,
    MuscleGroup,
    WorkoutSession,
    WorkoutSessionExercise,
)
from .timed_blocks import apply_timed_muscle_gain_blocks, parse_block_minutes


class TimedBlockPlanningTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="timed-block-test",
            password="test-password",
        )
        self.chest = MuscleGroup.objects.create(name="Mell")

        self.main_exercise = Exercise.objects.create(
            name="Teszt fekvenyomás",
            description="Fő gyakorlat",
            movement_pattern=Exercise.MovementPattern.PUSH,
        )
        ExerciseMuscle.objects.create(
            exercise=self.main_exercise,
            muscle_group=self.chest,
            role=ExerciseMuscle.MuscleRole.PRIMARY,
        )

        self.mobility = Exercise.objects.create(
            name="Teszt mellkas mobilizálás",
            description="Mobilizálás",
            movement_pattern=Exercise.MovementPattern.MOBILITY,
            default_duration_seconds=90,
        )
        ExerciseMuscle.objects.create(
            exercise=self.mobility,
            muscle_group=self.chest,
            role=ExerciseMuscle.MuscleRole.PRIMARY,
        )

        self.stretching = Exercise.objects.create(
            name="Teszt mellizom nyújtás",
            description="Nyújtás",
            movement_pattern=Exercise.MovementPattern.STRETCHING,
            default_duration_seconds=120,
        )
        ExerciseMuscle.objects.create(
            exercise=self.stretching,
            muscle_group=self.chest,
            role=ExerciseMuscle.MuscleRole.PRIMARY,
        )

        self.session = WorkoutSession.objects.create(
            user=self.user,
            title="Teszt izomépítő edzés",
            status=WorkoutSession.Status.PLANNED,
            training_goal=WorkoutSession.TrainingGoal.MUSCLE_GAIN,
            workout_profile="push",
        )
        WorkoutSessionExercise.objects.create(
            session=self.session,
            exercise=self.main_exercise,
            block_type=WorkoutSessionExercise.BlockType.CIRCUIT,
            position=1,
            target_sets=3,
        )

    def test_block_minutes_are_clamped(self):
        self.assertEqual(parse_block_minutes("0", 4), 1)
        self.assertEqual(parse_block_minutes("4", 3), 4)
        self.assertEqual(parse_block_minutes("99", 4), 10)
        self.assertEqual(parse_block_minutes("invalid", 4), 4)

    def test_muscle_gain_blocks_match_requested_total_time(self):
        apply_timed_muscle_gain_blocks(
            session=self.session,
            user=self.user,
            warmup_minutes=4,
            cooldown_minutes=5,
        )

        warmups = self.session.session_exercises.filter(
            block_type=WorkoutSessionExercise.BlockType.WARMUP,
        )
        cooldowns = self.session.session_exercises.filter(
            block_type=WorkoutSessionExercise.BlockType.COOLDOWN,
        )
        circuit = self.session.session_exercises.get(
            block_type=WorkoutSessionExercise.BlockType.CIRCUIT,
        )

        self.assertEqual(
            sum(item.target_duration_seconds for item in warmups),
            4 * 60,
        )
        self.assertEqual(
            sum(item.target_duration_seconds for item in cooldowns),
            5 * 60,
        )
        self.assertTrue(
            all(
                item.exercise.movement_pattern == Exercise.MovementPattern.MOBILITY
                for item in warmups
            )
        )
        self.assertTrue(
            all(
                item.exercise.movement_pattern == Exercise.MovementPattern.STRETCHING
                for item in cooldowns
            )
        )
        self.assertGreater(circuit.position, warmups.count())

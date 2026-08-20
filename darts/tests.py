from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Game, GamePlayer, Player
from .services import (
    get_checkout_suggestion,
    get_finish_options,
    get_finish_suggestion,
    record_throw,
    undo_last_throw,
)


class DartsScoringTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="darts-test",
            password="test-password",
        )
        self.player = Player.objects.create(
            created_by=self.user,
            name="Teszt játékos",
        )
        self.game = Game.objects.create(
            created_by=self.user,
            game_type=Game.GameType.GAME_301,
            checkout_mode=Game.CheckoutMode.DOUBLE,
        )
        self.game_player = GamePlayer.objects.create(
            game=self.game,
            player=self.player,
            player_order=1,
            starting_score=301,
            current_score=32,
        )

    def test_double_checkout_finishes_game(self):
        record_throw(self.game, segment=16, multiplier=2)

        self.game.refresh_from_db()
        self.game_player.refresh_from_db()

        self.assertEqual(self.game.status, Game.Status.FINISHED)
        self.assertEqual(self.game.winner, self.player)
        self.assertEqual(self.game_player.current_score, 0)

    def test_bust_restores_visit_starting_score(self):
        record_throw(self.game, segment=20, multiplier=3)

        self.game_player.refresh_from_db()
        visit = self.game_player.visits.get()

        self.assertTrue(visit.bust)
        self.assertEqual(self.game_player.current_score, 32)
        self.assertEqual(visit.scored_points, 0)

    def test_undo_reopens_checkout(self):
        record_throw(self.game, segment=16, multiplier=2)
        undo_last_throw(self.game)

        self.game.refresh_from_db()
        self.game_player.refresh_from_db()

        self.assertEqual(self.game.status, Game.Status.ACTIVE)
        self.assertIsNone(self.game.winner)
        self.assertEqual(self.game_player.current_score, 32)
        self.assertFalse(self.game_player.visits.exists())

    def test_170_checkout(self):
        self.assertEqual(
            get_checkout_suggestion(170, darts_left=3),
            ["T20", "T20", "BULL"],
        )

    def test_straight_out_21_with_one_dart_suggests_t7(self):
        self.assertEqual(
            get_finish_suggestion(
                21,
                darts_left=1,
                checkout_mode=Game.CheckoutMode.STRAIGHT,
            ),
            ["T7"],
        )

    def test_straight_out_18_with_one_dart_has_three_options(self):
        self.assertEqual(
            get_finish_options(
                18,
                darts_left=1,
                checkout_mode=Game.CheckoutMode.STRAIGHT,
            ),
            ["18", "D9", "T6"],
        )

    def test_double_out_18_with_one_dart_only_has_d9(self):
        self.assertEqual(
            get_finish_options(
                18,
                darts_left=1,
                checkout_mode=Game.CheckoutMode.DOUBLE,
            ),
            ["D9"],
        )

    def test_double_out_21_with_one_dart_has_no_finish(self):
        self.assertEqual(
            get_finish_suggestion(
                21,
                darts_left=1,
                checkout_mode=Game.CheckoutMode.DOUBLE,
            ),
            [],
        )

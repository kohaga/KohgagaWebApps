from django.urls import path

from . import views

app_name = "darts"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("players/add/", views.add_player, name="add_player"),
    path("players/<int:player_id>/", views.player_detail, name="player_detail"),
    path("new/", views.new_game, name="new_game"),
    path("games/<int:game_id>/", views.game_detail, name="game"),
    path("games/<int:game_id>/throw/", views.record_dart, name="record_dart"),
    path("games/<int:game_id>/undo/", views.undo_dart, name="undo_dart"),
]

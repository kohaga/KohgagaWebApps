from django.urls import path

from . import views

app_name = "vocabulary"

urlpatterns = [
    path("", views.vocabulary_home_view, name="home"),
    path("import/", views.card_import_view, name="card_import"),
    path("decks/<int:deck_id>/", views.deck_detail_view, name="deck_detail"),
    path("decks/<int:deck_id>/practice/", views.practice_start_view, name="practice_start"),
    path("decks/<int:deck_id>/practice/setup/", views.practice_setup_view, name="practice_setup"),
    path("decks/<int:deck_id>/practice/start-session/", views.practice_session_start_view, name="practice_session_start"),
    path("decks/<int:deck_id>/practice/session/", views.practice_session_question_view, name="practice_session_question"),
]
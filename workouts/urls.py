from django.urls import path

from . import generation_views, planning_views, views

app_name = "workouts"

urlpatterns = [
    path("", views.exercise_list, name="exercise_list"),
    path("history/", views.workout_history, name="workout_history"),
    path("exercises/<int:exercise_id>/", views.exercise_detail, name="exercise_detail"),

    path("generate/", generation_views.generate_workout, name="generate_workout"),
    path("sessions/<int:session_id>/", views.workout_session_detail, name="workout_session_detail"),
    path("sessions/<int:session_id>/start/", views.start_workout, name="start_workout"),
    path("sessions/<int:session_id>/finish/", views.finish_workout, name="finish_workout"),
    path("sessions/<int:session_id>/delete/", views.delete_workout_session, name="delete_workout_session"),
    path(
        "sessions/<int:session_id>/exercises/<int:session_exercise_id>/replace/",
        planning_views.replace_planned_exercise,
        name="replace_planned_exercise",
    ),
    path("sessions/<int:session_id>/train/", views.train_workout, name="train_workout"),
    path("sessions/<int:session_id>/train/<int:session_exercise_id>/", views.train_workout, name="train_workout_exercise"),
    path("sessions/<int:session_id>/rest/", views.workout_rest, name="workout_rest"),
    path(
        "sessions/<int:session_id>/exercises/<int:session_exercise_id>/result/",
        views.workout_exercise_result,
        name="workout_exercise_result",
    ),
]

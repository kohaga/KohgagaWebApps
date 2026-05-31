import random
import csv
import io

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Avg

from .models import Deck, Card, PracticeSessionResult
from .forms import CardImportForm

@login_required
def vocabulary_home_view(request):
    decks = Deck.objects.filter(active=True)

    context = {
        "decks": decks,
    }

    return render(request, "vocabulary/home.html", context)


@login_required
def deck_detail_view(request, deck_id):
    deck = get_object_or_404(Deck, id=deck_id, active=True)

    cards = Card.objects.filter(
        deck=deck,
        active=True,
    )

    session_results = PracticeSessionResult.objects.filter(
        user=request.user,
        deck=deck,
    )

    session_count = session_results.count()
    last_session_result = session_results.first()

    average_accuracy = session_results.aggregate(
        average=Avg("accuracy_percent")
    )["average"]

    if average_accuracy is not None:
        average_accuracy_percent = round(average_accuracy)
    else:
        average_accuracy_percent = None

    context = {
        "deck": deck,
        "cards": cards,
        "card_count": cards.count(),
        "can_practice": cards.count() >= 3,

        "session_count": session_count,
        "average_accuracy_percent": average_accuracy_percent,
        "last_session_result": last_session_result,
    }

    return render(request, "vocabulary/deck_detail.html", context)

@login_required
def practice_start_view(request, deck_id):
    deck = get_object_or_404(Deck, id=deck_id, active=True)

    cards = Card.objects.filter(
        deck=deck,
        active=True,
    )

    context = {
        "deck": deck,
        "card_count": cards.count(),
        "can_practice": cards.count() >= 3,
    }

    return render(request, "vocabulary/practice_start.html", context)


def is_staff_user(user):
    return user.is_staff


@login_required
@user_passes_test(is_staff_user)
def card_import_view(request):
    result = None

    if request.method == "POST":
        form = CardImportForm(request.POST, request.FILES)

        if form.is_valid():
            deck = form.cleaned_data["deck"]
            csv_file = form.cleaned_data["csv_file"]

            raw_data = csv_file.read().decode("utf-8-sig")
            text_stream = io.StringIO(raw_data)

            first_line = raw_data.splitlines()[0] if raw_data.splitlines() else ""

            try:
                dialect = csv.Sniffer().sniff(first_line, delimiters=",;\t")
            except csv.Error:
                delimiter = ";" if ";" in first_line else ","
                dialect = csv.excel
                dialect.delimiter = delimiter

            reader = csv.DictReader(text_stream, dialect=dialect)

            imported_count = 0
            skipped_count = 0
            error_rows = []

            valid_card_types = dict(Card.CARD_TYPE_CHOICES).keys()

            for row_number, row in enumerate(reader, start=2):
                source_text = (row.get("source_text") or "").strip()
                target_text = (row.get("target_text") or "").strip()
                card_type = (row.get("card_type") or Card.CARD_TYPE_WORD).strip()
                example_sentence = (row.get("example_sentence") or "").strip()
                note = (row.get("note") or "").strip()

                if not source_text or not target_text:
                    skipped_count += 1
                    error_rows.append(f"{row_number}. sor: hiányzó source_text vagy target_text")
                    continue

                if card_type not in valid_card_types:
                    card_type = Card.CARD_TYPE_WORD

                already_exists = Card.objects.filter(
                    deck=deck,
                    source_text=source_text,
                    target_text=target_text,
                ).exists()

                if already_exists:
                    skipped_count += 1
                    continue

                Card.objects.create(
                    deck=deck,
                    source_text=source_text,
                    target_text=target_text,
                    card_type=card_type,
                    example_sentence=example_sentence,
                    note=note,
                    active=True,
                )

                imported_count += 1

            result = {
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "error_rows": error_rows,
            }

    else:
        form = CardImportForm()

    return render(
        request,
        "vocabulary/card_import.html",
        {
            "form": form,
            "result": result,
        },
    )

@login_required
def practice_setup_view(request, deck_id):
    deck = get_object_or_404(Deck, id=deck_id, active=True)

    cards = Card.objects.filter(
        deck=deck,
        active=True,
    )

    if request.method != "POST":
        return render(
            request,
            "vocabulary/practice_start.html",
            {
                "deck": deck,
                "card_count": cards.count(),
                "can_practice": cards.count() >= 3,
            },
        )

    direction = request.POST.get("direction")
    question_count = request.POST.get("question_count")

    valid_directions = ["source-to-target", "target-to-source"]
    valid_question_counts = ["10", "20", "50"]

    if direction not in valid_directions:
        error_message = "Érvénytelen gyakorlási irány."
    elif question_count not in valid_question_counts:
        error_message = "Érvénytelen kérdésszám."
    elif cards.count() < 3:
        error_message = "A gyakorláshoz legalább 3 aktív kártya szükséges."
    else:
        error_message = None

    if error_message:
        return render(
            request,
            "vocabulary/practice_start.html",
            {
                "deck": deck,
                "card_count": cards.count(),
                "can_practice": cards.count() >= 3,
                "error_message": error_message,
            },
        )

    context = {
        "deck": deck,
        "direction": direction,
        "question_count": int(question_count),
        "card_count": cards.count(),
    }

    return render(request, "vocabulary/practice_setup.html", context)

@login_required
def practice_session_start_view(request, deck_id):
    deck = get_object_or_404(Deck, id=deck_id, active=True)

    if request.method != "POST":
        return redirect("vocabulary:practice_start", deck_id=deck.id)

    direction = request.POST.get("direction")
    question_count = request.POST.get("question_count")

    valid_directions = ["source-to-target", "target-to-source"]
    valid_question_counts = ["10", "20", "50"]

    cards = list(
        Card.objects.filter(
            deck=deck,
            active=True,
        ).values_list("id", flat=True)
    )

    if direction not in valid_directions:
        return redirect("vocabulary:practice_start", deck_id=deck.id)

    if question_count not in valid_question_counts:
        return redirect("vocabulary:practice_start", deck_id=deck.id)

    if len(cards) < 3:
        return redirect("vocabulary:practice_start", deck_id=deck.id)

    requested_question_count = int(question_count)
    actual_question_count = min(requested_question_count, len(cards))

    selected_card_ids = random.sample(cards, actual_question_count)

    request.session["practice_state"] = {
        "deck_id": deck.id,
        "direction": direction,
        "requested_question_count": requested_question_count,
        "remaining_card_ids": selected_card_ids,
        "wrong_card_ids": [],
        "repeat_card_ids": [],
        "phase": "first_round",
        "first_round_total": actual_question_count,
        "first_round_correct": 0,
        "first_round_wrong": 0,
    }

    request.session.modified = True

    return redirect("vocabulary:practice_session_question", deck_id=deck.id)

@login_required
def practice_session_question_view(request, deck_id):
    deck = get_object_or_404(Deck, id=deck_id, active=True)

    practice_state = request.session.get("practice_state")

    if not practice_state or practice_state.get("deck_id") != deck.id:
        return redirect("vocabulary:practice_start", deck_id=deck.id)

    direction = practice_state["direction"]
    phase = practice_state.get("phase", "first_round")

    remaining_card_ids = practice_state.get("remaining_card_ids", [])
    repeat_card_ids = practice_state.get("repeat_card_ids", [])

    # Első kör vége: ha volt hiba, indul az ismétlőkör
    if phase == "first_round" and not remaining_card_ids:
        wrong_card_ids = practice_state.get("wrong_card_ids", [])

        if wrong_card_ids:
            practice_state["phase"] = "repeat_round"
            practice_state["repeat_card_ids"] = wrong_card_ids.copy()
            request.session["practice_state"] = practice_state
            request.session.modified = True

            return redirect("vocabulary:practice_session_question", deck_id=deck.id)

        result = save_practice_session_result(request, deck, practice_state)

        return render(
            request,
            "vocabulary/practice_session_question.html",
            {
                "deck": deck,
                "session_finished": True,
                "first_round_total": result.first_round_question_count,
                "first_round_correct": result.first_round_correct_count,
                "first_round_wrong": result.first_round_wrong_count,
                "accuracy_percent": result.accuracy_percent,
                "result_saved": True,
            },
        )

    # Ismétlőkör vége
    if phase == "repeat_round" and not repeat_card_ids:
        result = save_practice_session_result(request, deck, practice_state)

        return render(
            request,
            "vocabulary/practice_session_question.html",
            {
                "deck": deck,
                "session_finished": True,
                "first_round_total": result.first_round_question_count,
                "first_round_correct": result.first_round_correct_count,
                "first_round_wrong": result.first_round_wrong_count,
                "accuracy_percent": result.accuracy_percent,
                "result_saved": True,
            },
        )

    result_checked = False
    selected_answer = None
    is_correct = False

    if request.method == "POST":
        question_card_id = int(request.POST.get("question_card_id"))
        selected_answer = request.POST.get("selected_answer")
        answer_options = request.POST.getlist("answer_options")

        question_card = get_object_or_404(
            Card,
            id=question_card_id,
            deck=deck,
            active=True,
        )

        if direction == "source-to-target":
            question_language = deck.source_language
            answer_language = deck.target_language
            question_text = question_card.source_text
            correct_answer = question_card.target_text
        else:
            question_language = deck.target_language
            answer_language = deck.source_language
            question_text = question_card.target_text
            correct_answer = question_card.source_text

        result_checked = True
        is_correct = selected_answer == correct_answer

        if phase == "first_round":
            if question_card_id in remaining_card_ids:
                remaining_card_ids.remove(question_card_id)

                if is_correct:
                    practice_state["first_round_correct"] += 1
                else:
                    practice_state["first_round_wrong"] += 1
                    practice_state["wrong_card_ids"].append(question_card_id)

                practice_state["remaining_card_ids"] = remaining_card_ids

        elif phase == "repeat_round":
            if question_card_id in repeat_card_ids:
                repeat_card_ids.remove(question_card_id)

                # Ha ismétlésben is rossz, visszarakjuk a sor végére.
                # Így addig jön vissza, amíg egyszer jól nem megy.
                if not is_correct:
                    repeat_card_ids.append(question_card_id)

                practice_state["repeat_card_ids"] = repeat_card_ids

        request.session["practice_state"] = practice_state
        request.session.modified = True

        if phase == "first_round":
            progress_current = (
                practice_state["first_round_total"]
                - len(practice_state.get("remaining_card_ids", []))
            )
            progress_total = practice_state["first_round_total"]
            repeat_remaining_count = None
        else:
            progress_current = None
            progress_total = None
            repeat_remaining_count = len(practice_state.get("repeat_card_ids", []))

    else:
        if phase == "first_round":
            current_card_id = remaining_card_ids[0]
        else:
            current_card_id = repeat_card_ids[0]

        question_card = get_object_or_404(
            Card,
            id=current_card_id,
            deck=deck,
            active=True,
        )

        wrong_cards = list(
            Card.objects.filter(
                deck=deck,
                active=True,
            ).exclude(id=question_card.id)
        )

        wrong_options = random.sample(wrong_cards, 2)

        if direction == "source-to-target":
            question_language = deck.source_language
            answer_language = deck.target_language
            question_text = question_card.source_text
            correct_answer = question_card.target_text
            answer_options = [
                correct_answer,
                wrong_options[0].target_text,
                wrong_options[1].target_text,
            ]
        else:
            question_language = deck.target_language
            answer_language = deck.source_language
            question_text = question_card.target_text
            correct_answer = question_card.source_text
            answer_options = [
                correct_answer,
                wrong_options[0].source_text,
                wrong_options[1].source_text,
            ]

        random.shuffle(answer_options)

        if phase == "first_round":
            progress_current = (
                practice_state["first_round_total"]
                - len(remaining_card_ids)
                + 1
            )
            progress_total = practice_state["first_round_total"]
            repeat_remaining_count = None
        else:
            progress_current = None
            progress_total = None
            repeat_remaining_count = len(repeat_card_ids)

    context = {
        "deck": deck,
        "direction": direction,
        "question_language": question_language,
        "answer_language": answer_language,
        "question_card": question_card,
        "question_text": question_text,
        "answer_options": answer_options,
        "correct_answer": correct_answer,
        "selected_answer": selected_answer,
        "is_correct": is_correct,
        "result_checked": result_checked,
        "progress_current": progress_current,
        "progress_total": progress_total,
        "repeat_remaining_count": repeat_remaining_count,
        "phase": phase,
        "session_finished": False,
    }

    return render(request, "vocabulary/practice_session_question.html", context)

def save_practice_session_result(request, deck, practice_state):
    first_round_total = practice_state["first_round_total"]
    first_round_correct = practice_state["first_round_correct"]
    first_round_wrong = practice_state["first_round_wrong"]

    if first_round_total > 0:
        accuracy_percent = round((first_round_correct / first_round_total) * 100)
    else:
        accuracy_percent = 0

    result = PracticeSessionResult.objects.create(
        user=request.user,
        deck=deck,
        direction=practice_state["direction"],
        requested_question_count=practice_state["requested_question_count"],
        first_round_question_count=first_round_total,
        first_round_correct_count=first_round_correct,
        first_round_wrong_count=first_round_wrong,
        accuracy_percent=accuracy_percent,
        repeated_wrong_count=first_round_wrong,
    )

    request.session.pop("practice_state", None)
    request.session.modified = True

    return result
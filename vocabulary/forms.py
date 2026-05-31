from django import forms

from .models import Deck


class CardImportForm(forms.Form):
    deck = forms.ModelChoiceField(
        queryset=Deck.objects.filter(active=True),
        label="Pakli",
    )

    csv_file = forms.FileField(
        label="CSV fájl",
        help_text="Elvárt oszlopok: source_text, target_text, card_type, example_sentence, note",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["deck"].widget.attrs.update({
            "class": "form-select",
        })

        self.fields["csv_file"].widget.attrs.update({
            "class": "form-control",
            "accept": ".csv,text/csv",
        })
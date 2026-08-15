from django import forms
from .models import QarzDaftar, SavdoChek


class QarzForm(forms.ModelForm):
    class Meta:
        model = QarzDaftar
        fields = ['mijoz_ism', 'mijoz_telefon', 'summa', 'izoh']
        widgets = {
            'mijoz_ism': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mijoz ismi',
            }),
            'mijoz_telefon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+998 90 000 00 00',
            }),
            'summa': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'min': '0',
            }),
            'izoh': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Izoh (ixtiyoriy)',
                'rows': 2,
            }),
        }
        labels = {
            'mijoz_ism': 'Mijoz ismi',
            'mijoz_telefon': 'Telefon raqami',
            'summa': 'Summa',
            'izoh': 'Izoh',
        }


class SavdoForm(forms.Form):
    TOLASH = [
        ('naqd', 'Naqd'),
        ('karta', 'Karta'),
        ('qarz', 'Qarz'),
    ]
    tolash_turi = forms.ChoiceField(
        choices=TOLASH,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="To'lov turi",
    )
    chegirma = forms.DecimalField(
        required=False,
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0',
        }),
        label='Chegirma',
    )
    berilgan = forms.DecimalField(
        required=False,
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0',
        }),
        label='Berilgan pul',
    )
    mijoz_ism = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mijoz ismi (qarz uchun)',
        }),
        label='Mijoz ismi',
    )
    mijoz_telefon = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+998 90 000 00 00',
        }),
        label='Telefon',
    )

    # Karta to'lov
    karta_raqami = forms.CharField(
        required=False,
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '9860 0000 0000 0000',
            'maxlength': '19',
            'inputmode': 'numeric',
        }),
        label='Karta raqami',
    )
    karta_kod = forms.CharField(
        required=False,
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tasdiqlash kodi',
            'inputmode': 'numeric',
        }),
        label='Tasdiqlash kodi',
    )
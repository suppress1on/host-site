# auth_app/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    country = forms.CharField(max_length=100, required=False, label="Страна проживания")

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + ('country', 'email',)
        widgets = {
            'email': forms.EmailInput(attrs={'required': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

class CustomAuthenticationForm(AuthenticationForm):
    pass

class TwoFACodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'placeholder': 'Введите 6-значный код'}),
        label="Код подтверждения"
    )
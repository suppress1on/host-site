from django import forms
from .models import DiskSpaceInstance

class RequestDiskSpaceForm(forms.ModelForm):
    # Выбор размера дискового пространства от 1 до 20 ГБ
    ALLOCATED_GB_CHOICES = [(i, f'{i} ГБ') for i in range(1, 21)]
    allocated_gb = forms.ChoiceField(
        choices=ALLOCATED_GB_CHOICES,
        label="Выделить дисковое пространство",
        initial=5, # Значение по умолчанию
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    name = forms.CharField(
        max_length=255,
        label="Имя для вашего хранилища",
        help_text="Уникальное имя для вашего экземпляра хранилища (например, 'МоиДокументы')",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = DiskSpaceInstance
        fields = ['name', 'allocated_gb']
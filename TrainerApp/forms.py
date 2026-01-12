# TrainerApp/forms.py
from django import forms
from .models import TrainerLeave

class TrainerLeaveForm(forms.ModelForm):
    class Meta:
        model = TrainerLeave
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for leave...'}),
        }
from django import forms
from .models import Movimiento

class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ['tipo', 'monto', 'descripcion', 'fecha', 'comprobante']
        widgets = {
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. 1250000.50',
                'step': '0.01',
                'min': '0',
            }),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

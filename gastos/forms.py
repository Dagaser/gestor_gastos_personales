from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Movimiento
import re
from decimal import Decimal, InvalidOperation
from .models import Presupuesto, Movimiento

class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ['tipo', 'monto', 'descripcion', 'categoria', 'fecha', 'comprobante', 'nota']
        widgets = {
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. 1250000.50',
                'step': '0.01',
                'min': '0.01',
                'max': '999999999.99',  # Validación HTML5
                'required': True,
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'maxlength': 50,
                'placeholder': 'Describe brevemente este movimiento...'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'fecha': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control',
                'required': True,
                'max': timezone.now().date().strftime('%Y-%m-%d'),
            }),
            'comprobante': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png,.pdf,.doc,.docx',  # Validación HTML5
            }),
            'nota': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'maxlength': 150,  # Validación HTML5
                'placeholder': 'Notas adicionales (opcional)...'
            }),
        }

    def clean_monto(self):
        """
        Validación personalizada para el campo monto
        """
        monto = self.cleaned_data.get('monto')
        
        if monto is None:
            raise ValidationError('El monto es obligatorio.')
        
        # Convertir a Decimal para validaciones precisas
        try:
            monto_decimal = Decimal(str(monto))
        except (InvalidOperation, TypeError):
            raise ValidationError('El monto debe ser un número válido.')
        
        # Validar que sea positivo
        if monto_decimal <= 0:
            raise ValidationError('El monto debe ser mayor a cero.')
        
        # Validar límite máximo
        if monto_decimal > Decimal('999999999.99'):
            raise ValidationError('El monto no puede exceder $999,999,999.99')
        
        # Validar que no tenga más de 2 decimales
        if monto_decimal.as_tuple().exponent < -2:
            raise ValidationError('El monto no puede tener más de 2 decimales.')
        
        return monto_decimal
    
    def clean_descripcion(self):
        """
        Validación personalizada para la descripción
        """
        descripcion = self.cleaned_data.get('descripcion', '')
        
        # Limpiar espacios extra
        descripcion = descripcion.strip()
        
        # Validar longitud mínima si no está vacía
        if descripcion and len(descripcion) < 3:
            raise ValidationError('La descripción debe tener al menos 3 caracteres.')
        
        # Validar que no contenga solo números o caracteres especiales
        if descripcion and not re.search(r'[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]', descripcion):
            raise ValidationError('La descripción debe contener al menos una letra.')
        
        # Filtrar contenido potencialmente malicioso (XSS básico)
        caracteres_peligrosos = ['<script', '</script', 'javascript:', 'onload=', 'onerror=']
        descripcion_lower = descripcion.lower()
        
        for caracter in caracteres_peligrosos:
            if caracter in descripcion_lower:
                raise ValidationError('La descripción contiene caracteres no permitidos.')
        
        return descripcion
    
    def clean_fecha(self):
        """
        Validación personalizada para la fecha
        """
        fecha = self.cleaned_data.get('fecha')
        
        if not fecha:
            raise ValidationError('La fecha es obligatoria.')
        
        # Validar que no sea muy antigua (más de 10 años)
        fecha_minima = timezone.now().date().replace(year=timezone.now().year - 10)
        if fecha < fecha_minima:
            raise ValidationError('La fecha no puede ser anterior a 10 años.')
        
        # Validar que no sea muy futura (más de 1 año)
        fecha_maxima = timezone.now().date().replace(year=timezone.now().year + 1)
        if fecha > fecha_maxima:
            raise ValidationError('La fecha no puede ser más de un año en el futuro.')
        
        return fecha
    
    def clean_nota(self):
        """
        Validación personalizada para la nota
        """
        nota = self.cleaned_data.get('nota', '')
        
        if not nota:
            return nota
        
        # Limpiar espacios extra
        nota = nota.strip()
        
        # Filtrar contenido potencialmente malicioso
        caracteres_peligrosos = ['<script', '</script', 'javascript:', 'onload=', 'onerror=']
        nota_lower = nota.lower()
        
        for caracter in caracteres_peligrosos:
            if caracter in nota_lower:
                raise ValidationError('La nota contiene caracteres no permitidos.')
        
        return nota
    
    def clean_comprobante(self):
        """
        Validación adicional para el comprobante
        (El modelo ya tiene validaciones, pero podemos agregar más aquí)
        """
        comprobante = self.cleaned_data.get('comprobante')
        
        if not comprobante:
            return comprobante
        
        # Validaciones adicionales si es necesario
        # (Las principales están en el modelo)
        
        return comprobante
    
    def clean(self):
        """
        Validación general del formulario
        """
        cleaned_data = super().clean()
        
        # Validaciones que involucran múltiples campos
        tipo = cleaned_data.get('tipo')
        monto = cleaned_data.get('monto')
        categoria = cleaned_data.get('categoria')
        
        # Validar coherencia entre tipo y categoría
        if tipo == 'ingreso':
            categorias_ingreso = ['salario', 'otros']
            if categoria and categoria not in categorias_ingreso:
                self.add_error('categoria', 
                    'Para ingresos, selecciona una categoría apropiada (Salario u Otros).')
        
        elif tipo == 'gasto':
            categorias_gasto = [
                'alimento', 'transporte', 'gasolina', 'arriendo', 
                'servicios', 'creditos', 'targeta_credito', 'otros'
            ]
            if categoria and categoria not in categorias_gasto:
                self.add_error('categoria', 
                    'Categoría no válida para gastos.')
        
        # Validar montos grandes para ciertos tipos
        if monto and monto > Decimal('10000000'):  # 10 millones
            if not cleaned_data.get('comprobante'):
                self.add_error('comprobante', 
                    'Para montos superiores a $10,000,000 es obligatorio adjuntar comprobante.')
        
        return cleaned_data

# Formulario adicional para filtros (seguro)
class FiltroMovimientosForm(forms.Form):
    """
    Formulario para filtros de búsqueda con validaciones de seguridad
    """
    tipo = forms.ChoiceField(
        choices=[('', '-- Todos --')] + Movimiento._meta.get_field('tipo').choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    categoria = forms.ChoiceField(
        choices=[('', '-- Todas --')] + Movimiento.CATEGORIAS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'max': timezone.now().date().strftime('%Y-%m-%d'),
        })
    )
    
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'max': timezone.now().date().strftime('%Y-%m-%d'),
        })
    )
    
    nota = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar en notas...',
            'maxlength': 100,
        })
    )
    
    def clean_fecha_inicio(self):
        fecha = self.cleaned_data.get('fecha_inicio')
        if fecha and fecha > timezone.now().date():
            raise ValidationError('La fecha de inicio no puede ser futura.')
        return fecha
    
    def clean_fecha_fin(self):
        fecha = self.cleaned_data.get('fecha_fin')
        if fecha and fecha > timezone.now().date():
            raise ValidationError('La fecha de fin no puede ser futura.')
        return fecha
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise ValidationError('La fecha de inicio debe ser anterior a la fecha de fin.')
        
        return cleaned_data

class PresupuestoForm(forms.ModelForm):
    """
    Formulario para crear y editar presupuestos
    """
    class Meta:
        model = Presupuesto
        fields = ['categoria', 'monto_presupuestado']
        widgets = {
            'categoria': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'monto_presupuestado': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'required': True,
                'placeholder': '0.00'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        self.año = kwargs.pop('año', None)
        self.mes = kwargs.pop('mes', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar categorías solo para gastos
        self.fields['categoria'].choices = [
            choice for choice in Movimiento.CATEGORIAS_CHOICES 
            if choice[0] not in ['salario', 'bonificacion', 'inversion', 'otro_ingreso']
        ]
    
    def clean_monto_presupuestado(self):
        monto = self.cleaned_data.get('monto_presupuestado')
        if monto is not None and monto <= 0:
            raise ValidationError('El monto presupuestado debe ser mayor a 0.')
        return monto
    
    def clean(self):
        cleaned_data = super().clean()
        categoria = cleaned_data.get('categoria')
        
        if self.usuario and self.año and self.mes and categoria:
            # Verificar si ya existe un presupuesto para esta categoría en este mes
            presupuesto_existente = Presupuesto.objects.filter(
                usuario=self.usuario,
                año=self.año,
                mes=self.mes,
                categoria=categoria
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if presupuesto_existente.exists():
                raise ValidationError(
                    f'Ya existe un presupuesto para la categoría "{dict(Movimiento.CATEGORIAS_CHOICES)[categoria]}" '
                    f'en {self.mes}/{self.año}.'
                )
        
        return cleaned_data

class FiltroPresupuestosForm(forms.Form):
    """
    Formulario para filtrar presupuestos
    """
    año = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Año (ej: 2025)',
            'min': '2020',
            'max': '2030'
        })
    )
    mes = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mes (1-12)',
            'min': '1',
            'max': '12'
        })
    )
    categoria = forms.ChoiceField(
        choices=[('', 'Todas las categorías')] + [
            choice for choice in Movimiento.CATEGORIAS_CHOICES 
            if choice[0] not in ['salario', 'bonificacion', 'inversion', 'otro_ingreso']
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    estado = forms.ChoiceField(
        choices=[
            ('', 'Todos los estados'),
            ('normal', 'Normal'),
            ('advertencia', 'Advertencia'),
            ('excedido', 'Excedido')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean_año(self):
        año = self.cleaned_data.get('año')
        if año is not None and (año < 2020 or año > 2030):
            raise ValidationError('El año debe estar entre 2020 y 2030.')
        return año
    
    def clean_mes(self):
        mes = self.cleaned_data.get('mes')
        if mes is not None and (mes < 1 or mes > 12):
            raise ValidationError('El mes debe estar entre 1 y 12.')
        return mes

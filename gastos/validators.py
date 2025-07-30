# gastos/validators.py
"""
Validadores personalizados para la aplicación de gastos
"""

import os
import re
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.conf import settings
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone


@deconstructible
class ValidadorArchivoSeguro:
    """
    Validador para archivos subidos que verifica:
    - Extensión permitida
    - Tamaño máximo
    - Tipo MIME
    - Nombres seguros
    """
    
    def __init__(self, 
                 extensiones_permitidas=None, 
                 tamaño_maximo=5*1024*1024,  # 5MB
                 tipos_mime_permitidos=None):
        self.extensiones_permitidas = extensiones_permitidas or [
            '.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx'
        ]
        self.tamaño_maximo = tamaño_maximo
        self.tipos_mime_permitidos = tipos_mime_permitidos or [
            'image/jpeg', 'image/png', 'application/pdf',
            'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
    
    def __call__(self, archivo):
        if not archivo:
            return
        
        # Validar extensión
        nombre_archivo = archivo.name.lower()
        extension = os.path.splitext(nombre_archivo)[1]
        
        if extension not in self.extensiones_permitidas:
            raise ValidationError(
                f'Tipo de archivo no permitido. Extensiones válidas: '
                f'{", ".join(self.extensiones_permitidas)}'
            )
        
        # Validar tamaño
        if archivo.size > self.tamaño_maximo:
            tamaño_mb = self.tamaño_maximo / (1024 * 1024)
            raise ValidationError(
                f'El archivo es muy grande. Tamaño máximo: {tamaño_mb}MB'
            )
        
        # Validar nombre de archivo (sin caracteres peligrosos)
        if not re.match(r'^[a-zA-Z0-9._\-\s]+$', archivo.name):
            raise ValidationError(
                'El nombre del archivo contiene caracteres no permitidos. '
                'Use solo letras, números, guiones, puntos y espacios.'
            )
        
        # Validar que no sea un archivo ejecutable disfrazado
        nombre_sin_extension = os.path.splitext(archivo.name)[0]
        extensiones_peligrosas = ['.exe', '.bat', '.cmd', '.scr', '.vbs', '.js']
        
        for ext_peligrosa in extensiones_peligrosas:
            if ext_peligrosa in nombre_sin_extension.lower():
                raise ValidationError(
                    'El nombre del archivo no puede contener extensiones ejecutables.'
                )


@deconstructible
class ValidadorMontoSeguro:
    """
    Validador para montos que verifica rangos lógicos
    """
    
    def __init__(self, monto_minimo=0.01, monto_maximo=999999999.99):
        self.monto_minimo = Decimal(str(monto_minimo))
        self.monto_maximo = Decimal(str(monto_maximo))
    
    def __call__(self, valor):
        if valor is None:
            return
        
        try:
            monto = Decimal(str(valor))
        except:
            raise ValidationError('El monto debe ser un número válido.')
        
        if monto < self.monto_minimo:
            raise ValidationError(f'El monto debe ser mayor a ${self.monto_minimo}')
        
        if monto > self.monto_maximo:
            raise ValidationError(f'El monto no puede exceder ${self.monto_maximo:,}')
        
        # Validar que no tenga más de 2 decimales
        if monto.as_tuple().exponent < -2:
            raise ValidationError('El monto no puede tener más de 2 decimales.')


@deconstructible
class ValidadorFechaLogica:
    """
    Validador para fechas que verifica rangos lógicos
    """
    
    def __init__(self, años_atras=10, años_adelante=1):
        self.años_atras = años_atras
        self.años_adelante = años_adelante
    
    def __call__(self, fecha):
        if not fecha:
            return
        
        hoy = timezone.now().date()
        
        # Fecha mínima (hace X años)
        fecha_minima = hoy.replace(year=hoy.year - self.años_atras)
        if fecha < fecha_minima:
            raise ValidationError(
                f'La fecha no puede ser anterior a {self.años_atras} años.'
            )
        
        # Fecha máxima (dentro de X años)
        fecha_maxima = hoy.replace(year=hoy.year + self.años_adelante)
        if fecha > fecha_maxima:
            raise ValidationError(
                f'La fecha no puede ser más de {self.años_adelante} año(s) en el futuro.'
            )


@deconstructible
class ValidadorTextoSeguro:
    """
    Validador para campos de texto que previene XSS y otros ataques
    """
    
    def __init__(self, longitud_minima=0, longitud_maxima=1000, 
                 permitir_html=False, requerir_letras=True):
        self.longitud_minima = longitud_minima
        self.longitud_maxima = longitud_maxima
        self.permitir_html = permitir_html
        self.requerir_letras = requerir_letras
    
    def __call__(self, valor):
        if not valor:
            return
        
        # Limpiar espacios extra
        texto = valor.strip()
        
        # Validar longitud
        if len(texto) < self.longitud_minima:
            raise ValidationError(
                f'El texto debe tener al menos {self.longitud_minima} caracteres.'
            )
        
        if len(texto) > self.longitud_maxima:
            raise ValidationError(
                f'El texto no puede exceder {self.longitud_maxima} caracteres.'
            )
        
        # Requerir al menos una letra si está configurado
        if self.requerir_letras and texto:
            if not re.search(r'[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]', texto):
                raise ValidationError(
                    'El texto debe contener al menos una letra.'
                )
        
        # Validar contenido potencialmente peligroso
        if not self.permitir_html:
            patrones_peligrosos = [
                r'<script.*?>.*?</script>',
                r'javascript:',
                r'onload\s*=',
                r'onerror\s*=',
                r'onclick\s*=',
                r'<iframe.*?>',
                r'<object.*?>',
                r'<embed.*?>',
            ]
            
            texto_lower = texto.lower()
            for patron in patrones_peligrosos:
                if re.search(patron, texto_lower, re.IGNORECASE | re.DOTALL):
                    raise ValidationError(
                        'El texto contiene contenido no permitido.'
                    )


def validar_categoria_coherente(tipo, categoria):
    """
    Validador para verificar que la categoría sea coherente con el tipo
    """
    categorias_ingresos = getattr(settings, 'CATEGORIAS_INGRESOS', ['salario', 'otros'])
    categorias_gastos = getattr(settings, 'CATEGORIAS_GASTOS', [
        'alimento', 'transporte', 'gasolina', 'arriendo', 
        'servicios', 'creditos', 'targeta_credito', 'otros'
    ])
    
    if tipo == 'ingreso' and categoria not in categorias_ingresos:
        raise ValidationError(
            f'Para ingresos, las categorías válidas son: {", ".join(categorias_ingresos)}'
        )
    
    if tipo == 'gasto' and categoria not in categorias_gastos:
        raise ValidationError(
            f'Para gastos, las categorías válidas son: {", ".join(categorias_gastos)}'
        )


class ValidadorLimitesUsuario:
    """
    Validadores para límites por usuario (prevenir abuso)
    """
    
    @staticmethod
    def validar_movimientos_por_dia(usuario, fecha, limite=None):
        """Valida que no exceda el límite de movimientos por día"""
        from .models import Movimiento
        
        limite = limite or getattr(settings, 'MAX_MOVIMIENTOS_POR_DIA', 50)
        
        movimientos_hoy = Movimiento.objects.filter(
            usuario=usuario,
            fecha=fecha
        ).count()
        
        if movimientos_hoy >= limite:
            raise ValidationError(
                f'Has alcanzado el límite de {limite} movimientos por día.'
            )
    
    @staticmethod
    def validar_uploads_por_hora(usuario, limite=None):
        """Valida que no exceda el límite de uploads por hora"""
        from .models import Movimiento
        
        limite = limite or getattr(settings, 'MAX_UPLOADS_POR_HORA', 10)
        
        una_hora_atras = timezone.now() - timedelta(hours=1)
        uploads_recientes = Movimiento.objects.filter(
            usuario=usuario,
            creado_en__gte=una_hora_atras,
            comprobante__isnull=False
        ).count()
        
        if uploads_recientes >= limite:
            raise ValidationError(
                f'Has alcanzado el límite de {limite} archivos por hora.'
            )
    
    @staticmethod
    def validar_tamaño_total_archivos(usuario, nuevo_archivo_size=0, limite_mb=100):
        """Valida que no exceda el límite total de almacenamiento"""
        from .models import Movimiento
        import os
        
        # Calcular tamaño total actual
        movimientos_con_archivos = Movimiento.objects.filter(
            usuario=usuario,
            comprobante__isnull=False
        )
        
        tamaño_total = 0
        for mov in movimientos_con_archivos:
            if mov.comprobante and os.path.exists(mov.comprobante.path):
                tamaño_total += mov.comprobante.size
        
        limite_bytes = limite_mb * 1024 * 1024
        
        if (tamaño_total + nuevo_archivo_size) > limite_bytes:
            raise ValidationError(
                f'Excederías el límite de {limite_mb}MB de almacenamiento. '
                f'Actualmente usas {tamaño_total/(1024*1024):.1f}MB.'
            )


# Instancias pre-configuradas de validadores comunes
validador_archivo_comprobante = ValidadorArchivoSeguro()
validador_monto_movimiento = ValidadorMontoSeguro()
validador_fecha_movimiento = ValidadorFechaLogica()
validador_descripcion = ValidadorTextoSeguro(longitud_minima=0, longitud_maxima=50)
validador_nota = ValidadorTextoSeguro(longitud_minima=0, longitud_maxima=150)
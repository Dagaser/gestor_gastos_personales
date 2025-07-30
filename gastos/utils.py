# gastos/utils.py
"""
Utilidades de seguridad y helpers para la aplicación
"""

import os
import hashlib
import logging
import re
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from PIL import Image
import magic

logger = logging.getLogger(__name__)


class SeguridadArchivos:
    """
    Utilidades para manejo seguro de archivos
    """
    
    @staticmethod
    def generar_nombre_seguro(archivo, usuario_id):
        """
        Genera un nombre de archivo seguro y único
        """
        # Obtener extensión original
        nombre_original = archivo.name
        extension = os.path.splitext(nombre_original)[1].lower()
        
        # Crear hash único basado en contenido + timestamp + usuario
        timestamp = str(int(timezone.now().timestamp()))
        contenido_hash = hashlib.md5(
            f"{usuario_id}_{timestamp}_{nombre_original}".encode()
        ).hexdigest()[:10]
        
        # Nombre final seguro
        nombre_seguro = f"comprobante_{usuario_id}_{contenido_hash}{extension}"
        
        return nombre_seguro
    
    @staticmethod
    def validar_tipo_archivo_real(archivo):
        """
        Valida el tipo real del archivo usando python-magic
        (no solo la extensión)
        """
        try:
            # Leer primeros bytes del archivo
            archivo.seek(0)
            primeros_bytes = archivo.read(1024)
            archivo.seek(0)
            
            # Detectar tipo MIME real
            tipo_real = magic.from_buffer(primeros_bytes, mime=True)
            
            # Tipos permitidos
            tipos_permitidos = [
                'image/jpeg', 'image/png', 'image/gif',
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ]
            
            if tipo_real not in tipos_permitidos:
                raise ValidationError(f"Tipo de archivo no permitido: {tipo_real}")
            
            return tipo_real
            
        except Exception as e:
            logger.warning(f"Error validando tipo de archivo: {e}")
            # Fallback a validación por extensión
            return None
    
    @staticmethod
    def comprimir_imagen_si_es_necesario(archivo, calidad=85, max_ancho=1920, max_alto=1080):
        """
        Comprime imagen si es muy grande para ahorrar espacio
        """
        try:
            # Solo procesar si es imagen
            if not archivo.content_type.startswith('image/'):
                return archivo
            
            # Abrir imagen
            imagen = Image.open(archivo)
            
            # Convertir a RGB si es necesario
            if imagen.mode in ('RGBA', 'P'):
                imagen = imagen.convert('RGB')
            
            # Redimensionar si es muy grande
            if imagen.width > max_ancho or imagen.height > max_alto:
                imagen.thumbnail((max_ancho, max_alto), Image.Resampling.LANCZOS)
            
            # Guardar con compresión
            from io import BytesIO
            output = BytesIO()
            imagen.save(output, format='JPEG', quality=calidad, optimize=True)
            output.seek(0)
            
            # Crear nuevo archivo comprimido
            from django.core.files.base import ContentFile
            archivo_comprimido = ContentFile(
                output.getvalue(),
                name=f"{os.path.splitext(archivo.name)[0]}.jpg"
            )
            
            return archivo_comprimido
            
        except Exception as e:
            logger.warning(f"Error comprimiendo imagen: {e}")
            return archivo  # Devolver original si hay error
    
    @staticmethod
    def limpiar_archivos_huerfanos():
        """
        Limpia archivos que no están referenciados en la BD
        """
        from .models import Movimiento
        
        try:
            # Obtener todos los archivos en el directorio
            media_root = settings.MEDIA_ROOT
            comprobantes_dir = os.path.join(media_root, 'comprobantes')
            
            if not os.path.exists(comprobantes_dir):
                return
            
            archivos_fisicos = set()
            for root, dirs, files in os.walk(comprobantes_dir):
                for file in files:
                    archivo_path = os.path.join(root, file)
                    archivos_fisicos.add(archivo_path)
            
            # Obtener archivos referenciados en BD
            movimientos = Movimiento.objects.filter(comprobante__isnull=False)
            archivos_bd = set()
            
            for mov in movimientos:
                if mov.comprobante:
                    archivo_path = mov.comprobante.path
                    if os.path.exists(archivo_path):
                        archivos_bd.add(archivo_path)
            
            # Eliminar archivos huérfanos
            archivos_huerfanos = archivos_fisicos - archivos_bd
            eliminados = 0
            
            for archivo_huerfano in archivos_huerfanos:
                try:
                    os.remove(archivo_huerfano)
                    eliminados += 1
                except OSError as e:
                    logger.error(f"Error eliminando archivo huérfano {archivo_huerfano}: {e}")
            
            logger.info(f"Limpieza completada: {eliminados} archivos huérfanos eliminados")
            return eliminados
            
        except Exception as e:
            logger.error(f"Error en limpieza de archivos huérfanos: {e}")
            return 0


class ValidacionesBusiness:
    """
    Validaciones específicas de la lógica de negocio
    """
    
    @staticmethod
    def validar_coherencia_movimiento(tipo, categoria, monto):
        """
        Valida que el movimiento tenga sentido desde el punto de vista de negocio
        """
        errores = []
        
        # Validar coherencia tipo-categoría
        if tipo == 'ingreso':
            categorias_validas = ['salario', 'otros']
            if categoria not in categorias_validas:
                errores.append(f"Para ingresos, usa categorías: {', '.join(categorias_validas)}")
        
        # Validar montos sospechosos
        if monto > 10000000:  # 10 millones
            errores.append("Monto muy alto. ¿Estás seguro de que es correcto?")
        
        # Validar salarios razonables (ejemplo para Colombia)
        if tipo == 'ingreso' and categoria == 'salario':
            if monto < 1000000 or monto > 50000000:  # 1M a 50M pesos
                errores.append("El salario parece fuera del rango típico")
        
        return errores
    
    @staticmethod
    def detectar_patrones_sospechosos(usuario, nuevo_movimiento):
        """
        Detecta patrones que podrían indicar uso anómalo
        """
        from .models import Movimiento
        
        alertas = []
        
        # Muchos movimientos en poco tiempo
        ultima_hora = timezone.now() - timedelta(hours=1)
        movimientos_recientes = Movimiento.objects.filter(
            usuario=usuario,
            creado_en__gte=ultima_hora
        ).count()
        
        if movimientos_recientes > 20:
            alertas.append("Actividad muy alta en la última hora")
        
        # Movimientos con montos idénticos
        movimientos_similares = Movimiento.objects.filter(
            usuario=usuario,
            monto=nuevo_movimiento['monto'],
            fecha=nuevo_movimiento['fecha']
        ).count()
        
        if movimientos_similares > 3:
            alertas.append("Múltiples movimientos con el mismo monto y fecha")
        
        # Cambios drásticos en patrones de gasto
        promedio_mensual = Movimiento.objects.filter(
            usuario=usuario,
            tipo='gasto',
            fecha__gte=timezone.now().date() - timedelta(days=30)
        ).aggregate(promedio=Sum('monto'))['promedio'] or 0
        
        if nuevo_movimiento['tipo'] == 'gasto' and nuevo_movimiento['monto'] > promedio_mensual * 0.5:
            alertas.append("Gasto significativamente mayor al promedio mensual")
        
        return alertas


class ReportesSeguridad:
    """
    Generación de reportes de seguridad y auditoría
    """
    
    @staticmethod
    def generar_reporte_actividad_usuario(usuario, dias=30):
        """
        Genera un reporte de actividad del usuario
        """
        from .models import Movimiento
        
        fecha_inicio = timezone.now().date() - timedelta(days=dias)
        
        movimientos = Movimiento.objects.filter(
            usuario=usuario,
            creado_en__gte=fecha_inicio
        )
        
        reporte = {
            'usuario': usuario.username,
            'periodo': f"Últimos {dias} días",
            'total_movimientos': movimientos.count(),
            'movimientos_por_dia': movimientos.count() / dias,
            'total_ingresos': movimientos.filter(tipo='ingreso').aggregate(
                total=Sum('monto'))['total'] or 0,
            'total_gastos': movimientos.filter(tipo='gasto').aggregate(
                total=Sum('monto'))['total'] or 0,
            'archivos_subidos': movimientos.filter(
                comprobante__isnull=False).count(),
            'movimientos_grandes': movimientos.filter(
                monto__gt=1000000).count(),
        }
        
        reporte['balance'] = reporte['total_ingresos'] - reporte['total_gastos']
        
        return reporte
    
    @staticmethod
    def detectar_usuarios_anomalos():
        """
        Detecta usuarios con patrones anómalos de uso
        """
        from .models import Movimiento
        
        usuarios_anomalos = []
        fecha_limite = timezone.now() - timedelta(days=7)
        
        # Usuarios con actividad muy alta
        usuarios_activos = Movimiento.objects.filter(
            creado_en__gte=fecha_limite
        ).values('usuario').annotate(
            total_movimientos=models.Count('id')
        ).filter(total_movimientos__gt=100)
        
        for usuario_data in usuarios_activos:
            try:
                usuario = User.objects.get(id=usuario_data['usuario'])
                usuarios_anomalos.append({
                    'usuario': usuario.username,
                    'motivo': 'Actividad muy alta',
                    'movimientos': usuario_data['total_movimientos']
                })
            except User.DoesNotExist:
                continue
        
        return usuarios_anomalos


class LimpiadorDatos:
    """
    Utilidades para limpiar y sanitizar datos
    """
    
    @staticmethod
    def sanitizar_texto(texto):
        """
        Sanitiza texto eliminando caracteres peligrosos
        """
        if not texto:
            return texto
        
        # Eliminar tags HTML básicos
        texto = re.sub(r'<[^>]+>', '', texto)
        
        # Eliminar caracteres de control
        texto = ''.join(char for char in texto if ord(char) >= 32 or char in '\n\r\t')
        
        # Normalizar espacios
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        return texto
    
    @staticmethod
    def limpiar_numero(valor):
        """
        Limpia y normaliza números de entrada
        """
        if not valor:
            return None
        
        # Convertir a string si no lo es
        valor_str = str(valor)
        
        # Eliminar caracteres no numéricos excepto punto y coma
        valor_limpio = re.sub(r'[^\d.,\-]', '', valor_str)
        
        # Reemplazar comas por puntos para decimales
        valor_limpio = valor_limpio.replace(',', '.')
        
        try:
            return Decimal(valor_limpio)
        except:
            return None
    
    @staticmethod
    def validar_entrada_sql_injection(texto):
        """
        Detecta posibles intentos de SQL injection
        """
        if not texto:
            return False
        
        patrones_sospechosos = [
            r'\b(union|select|insert|update|delete|drop|create)\b',
            r'[\'";]',
            r'--',
            r'/\*.*\*/',
            r'\bor\b.*=.*',
            r'\band\b.*=.*'
        ]
        
        texto_lower = texto.lower()
        
        for patron in patrones_sospechosos:
            if re.search(patron, texto_lower, re.IGNORECASE):
                logger.warning(f"Posible SQL injection detectado: {texto[:100]}")
                return True
        
        return False


class MonitoreoRendimiento:
    """
    Utilidades para monitorear el rendimiento de la aplicación
    """
    
    @staticmethod
    def medir_tiempo_consulta(func):
        """
        Decorador para medir tiempo de consultas
        """
        def wrapper(*args, **kwargs):
            inicio = timezone.now()
            resultado = func(*args, **kwargs)
            fin = timezone.now()
            
            tiempo_ms = (fin - inicio).total_seconds() * 1000
            
            if tiempo_ms > 1000:  # Más de 1 segundo
                logger.warning(f"Consulta lenta detectada en {func.__name__}: {tiempo_ms:.2f}ms")
            
            return resultado
        
        return wrapper
    
    @staticmethod
    def obtener_estadisticas_bd():
        """
        Obtiene estadísticas básicas de la base de datos
        """
        from .models import Movimiento
        from django.contrib.auth.models import User
        
        stats = {
            'total_usuarios': User.objects.count(),
            'total_movimientos': Movimiento.objects.count(),
            'movimientos_ultimo_mes': Movimiento.objects.filter(
                creado_en__gte=timezone.now() - timedelta(days=30)
            ).count(),
            'usuarios_activos_mes': Movimiento.objects.filter(
                creado_en__gte=timezone.now() - timedelta(days=30)
            ).values('usuario').distinct().count(),
            'tamaño_archivos_mb': 0,  # Se calcularía recorriendo archivos
        }
        
        return stats


class BackupSeguridad:
    """
    Utilidades para backup y recuperación
    """
    
    @staticmethod
    def crear_backup_usuario(usuario, incluir_archivos=True):
        """
        Crea un backup de los datos de un usuario específico
        """
        from .models import Movimiento
        import json
        
        try:
            movimientos = Movimiento.objects.filter(usuario=usuario)
            
            datos_backup = {
                'usuario': {
                    'username': usuario.username,
                    'email': usuario.email,
                    'fecha_creacion': usuario.date_joined.isoformat(),
                },
                'movimientos': [],
                'estadisticas': {
                    'total_movimientos': movimientos.count(),
                    'fecha_backup': timezone.now().isoformat(),
                }
            }
            
            for mov in movimientos:
                mov_data = {
                    'tipo': mov.tipo,
                    'monto': str(mov.monto),
                    'descripcion': mov.descripcion,
                    'categoria': mov.categoria,
                    'fecha': mov.fecha.isoformat(),
                    'nota': mov.nota,
                    'creado_en': mov.creado_en.isoformat(),
                }
                
                if incluir_archivos and mov.comprobante:
                    mov_data['comprobante_nombre'] = mov.comprobante.name
                    # En una implementación real, copiarías el archivo
                
                datos_backup['movimientos'].append(mov_data)
            
            return json.dumps(datos_backup, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Error creando backup para usuario {usuario.id}: {e}")
            return None
    
    @staticmethod
    def validar_integridad_datos():
        """
        Valida la integridad de los datos en la base de datos
        """
        from .models import Movimiento
        
        errores = []
        
        # Verificar movimientos sin usuario
        movimientos_huerfanos = Movimiento.objects.filter(usuario__isnull=True)
        if movimientos_huerfanos.exists():
            errores.append(f"{movimientos_huerfanos.count()} movimientos sin usuario")
        
        # Verificar archivos referenciados que no existen
        movimientos_con_archivo = Movimiento.objects.filter(comprobante__isnull=False)
        archivos_faltantes = 0
        
        for mov in movimientos_con_archivo:
            if not os.path.exists(mov.comprobante.path):
                archivos_faltantes += 1
        
        if archivos_faltantes > 0:
            errores.append(f"{archivos_faltantes} archivos referenciados no encontrados")
        
        # Verificar montos anómalos
        movimientos_anomalos = Movimiento.objects.filter(
            Q(monto__lt=0) | Q(monto__gt=999999999)
        )
        if movimientos_anomalos.exists():
            errores.append(f"{movimientos_anomalos.count()} movimientos con montos anómalos")
        
        return errores


# Funciones de utilidad general
def log_accion_seguridad(usuario, accion, detalles=""):
    """
    Registra acciones importantes de seguridad
    """
    mensaje = f"Usuario {usuario.username} (ID: {usuario.id}) - {accion}"
    if detalles:
        mensaje += f" - {detalles}"
    
    logger.info(mensaje)


def validar_permisos_archivo(usuario, archivo_path):
    """
    Valida que el usuario tenga permisos para acceder a un archivo
    """
    try:
        # Verificar que el archivo pertenece al usuario
        from .models import Movimiento
        
        movimiento = Movimiento.objects.get(
            usuario=usuario,
            comprobante=archivo_path
        )
        
        return True
        
    except Movimiento.DoesNotExist:
        log_accion_seguridad(
            usuario, 
            "INTENTO_ACCESO_ARCHIVO_NO_AUTORIZADO", 
            f"Archivo: {archivo_path}"
        )
        return False


def generar_token_csrf_personalizado():
    """
    Genera un token CSRF personalizado para operaciones críticas
    """
    import secrets
    return secrets.token_urlsafe(32)


def verificar_rate_limit(usuario, accion, limite_por_hora=10):
    """
    Verifica si el usuario ha excedido el rate limit para una acción
    """
    from django.core.cache import cache
    
    cache_key = f"rate_limit_{usuario.id}_{accion}"
    contador = cache.get(cache_key, 0)
    
    if contador >= limite_por_hora:
        log_accion_seguridad(
            usuario, 
            f"RATE_LIMIT_EXCEDIDO_{accion.upper()}", 
            f"Límite: {limite_por_hora}/hora"
        )
        return False
    
    # Incrementar contador
    cache.set(cache_key, contador + 1, timeout=3600)  # 1 hora
    return True


def limpiar_sesiones_expiradas():
    """
    Limpia sesiones expiradas de la base de datos
    """
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    
    sesiones_expiradas = Session.objects.filter(expire_date__lt=timezone.now())
    count = sesiones_expiradas.count()
    sesiones_expiradas.delete()
    
    logger.info(f"Limpiadas {count} sesiones expiradas")
    return count


# Configuraciones de seguridad por defecto
CONFIGURACION_SEGURIDAD = {
    'MAX_INTENTOS_LOGIN': 5,
    'TIEMPO_BLOQUEO_MINUTOS': 30,
    'MAX_ARCHIVOS_POR_USUARIO': 100,
    'TAMAÑO_MAX_ARCHIVO_MB': 5,
    'PATRON_PASSWORD_SEGURO': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,},
    'EXTENSION_ARCHIVOS_PERMITIDAS': ['.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx'],
    'DIRECTORIO_CUARENTENA': 'quarantine/',
}
#!/usr/bin/env python
"""
Script de verificación final para confirmar que la aplicación está funcionando correctamente.
"""

import os
import sys
import requests
import time

def verificar_servidor():
    """Verifica que el servidor esté funcionando"""
    print("🔍 Verificando que el servidor esté funcionando...")
    
    try:
        # Intentar conectar al servidor
        response = requests.get('http://127.0.0.1:8000/', timeout=5)
        if response.status_code == 200:
            print("✅ Servidor funcionando correctamente")
            return True
        else:
            print(f"⚠️ Servidor respondió con código: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al servidor. Asegúrate de que esté ejecutándose.")
        return False
    except Exception as e:
        print(f"❌ Error verificando servidor: {e}")
        return False

def verificar_archivos_importantes():
    """Verifica que los archivos importantes existan"""
    print("\n🔍 Verificando archivos importantes...")
    
    archivos_importantes = [
        'manage.py',
        'requirements.txt',
        'core/settings.py',
        'gastos/models.py',
        'gastos/views.py',
        'gastos/urls.py',
        'static/css/style.css',
        'gastos/templates/base.html',
        'gastos/templates/gastos/dashboard.html',
        'README.md',
        'env.example'
    ]
    
    todos_existen = True
    for archivo in archivos_importantes:
        if os.path.exists(archivo):
            print(f"✅ {archivo}")
        else:
            print(f"❌ {archivo} - NO EXISTE")
            todos_existen = False
    
    return todos_existen

def verificar_estructura_directorios():
    """Verifica la estructura de directorios"""
    print("\n🔍 Verificando estructura de directorios...")
    
    directorios_importantes = [
        'core',
        'gastos',
        'gastos/templates',
        'gastos/templates/gastos',
        'static',
        'static/css',
        'media',
        'logs'
    ]
    
    todos_existen = True
    for directorio in directorios_importantes:
        if os.path.exists(directorio):
            print(f"✅ {directorio}/")
        else:
            print(f"❌ {directorio}/ - NO EXISTE")
            todos_existen = False
    
    return todos_existen

def mostrar_instrucciones():
    """Muestra las instrucciones de uso"""
    print("\n" + "="*60)
    print("🎉 ¡VERIFICACIÓN COMPLETADA!")
    print("="*60)
    
    print("\n📋 RESUMEN DE LA APLICACIÓN:")
    print("   • Gestión completa de gastos e ingresos")
    print("   • Dashboard con estadísticas")
    print("   • Filtros avanzados")
    print("   • Exportación a PDF")
    print("   • Interfaz moderna y responsive")
    print("   • Seguridad robusta")
    
    print("\n🌐 ACCESO A LA APLICACIÓN:")
    print("   URL: http://127.0.0.1:8000/")
    print("   Usuario: admin")
    print("   Contraseña: admin123")
    
    print("\n🚀 COMANDOS ÚTILES:")
    print("   • Iniciar servidor: python manage.py runserver")
    print("   • Crear superusuario: python manage.py createsuperuser")
    print("   • Aplicar migraciones: python manage.py migrate")
    print("   • Ejecutar pruebas: python test_app.py")
    
    print("\n📁 ESTRUCTURA PRINCIPAL:")
    print("   • /dashboard/ - Dashboard principal")
    print("   • /balance/ - Balance general")
    print("   • /crear/ - Crear nuevo movimiento")
    print("   • /movimientos/ - Lista de movimientos")
    print("   • /resumen/ - Resumen mensual")
    
    print("\n🔧 PRÓXIMOS PASOS SUGERIDOS:")
    print("   1. Explorar todas las funcionalidades")
    print("   2. Crear algunos movimientos de prueba")
    print("   3. Probar los filtros y búsquedas")
    print("   4. Exportar reportes en PDF")
    print("   5. Personalizar categorías si es necesario")
    print("   6. Configurar para producción cuando esté listo")
    
    print("\n📞 SOPORTE:")
    print("   • Revisar el README.md para documentación completa")
    print("   • Ejecutar python test_app.py para verificar funcionamiento")
    print("   • Revisar logs en caso de problemas")
    
    print("\n" + "="*60)
    print("¡Disfruta usando tu Gestor de Gastos Personales! 🎊")
    print("="*60)

def main():
    """Función principal"""
    print("🚀 VERIFICACIÓN FINAL DE LA APLICACIÓN")
    print("="*60)
    
    # Verificaciones
    archivos_ok = verificar_archivos_importantes()
    directorios_ok = verificar_estructura_directorios()
    servidor_ok = verificar_servidor()
    
    # Resultado final
    print("\n" + "="*60)
    if archivos_ok and directorios_ok and servidor_ok:
        print("🎉 ¡TODAS LAS VERIFICACIONES PASARON!")
        print("✅ La aplicación está lista para usar")
        mostrar_instrucciones()
        return True
    else:
        print("⚠️ ALGUNAS VERIFICACIONES FALLARON")
        print("❌ Revisa los errores arriba antes de continuar")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 
from datetime import datetime


def guardar_historial(operacion, resultado):
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("historial.txt", "a") as archivo:
        archivo.write(f"[{fecha_hora}] {operacion} = {resultado}\n")


def ver_historial():
    try:
        with open("historial.txt", "r") as archivo:
            lineas = archivo.readlines()
            if not lineas:
                print("Historial vacío.")
                return

            print("\n Historial de operaciones:")
            for i, linea in enumerate(lineas, start=1):
                print(f"{i}. {linea.strip()}")
    except FileNotFoundError:
        print("No hay operaciones en el historial.")
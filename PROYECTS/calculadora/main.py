from entrada import leer_numero
from operaciones import realizar_operacion
from historial import guardar_historial, ver_historial

def mostrar_menu():
    print("1. Sumar")
    print("2. Restar")
    print("3. Multiplicar")
    print("4. Dividir")
    print("5. Ver historial")
    print("6. Salir")
    
def main():
    while True:
        mostrar_menu()
        opcion = input("Selecione una opción: ")

        if opcion == "6":
            print("Saliendo de la calculadora...")
            break

        else:
            print(f"Elegiste la opcion {opcion}")

            
            if opcion in ["1", "2", "3", "4"]:
                a = leer_numero("Ingrese el primer número: ")
                b = leer_numero("Ingrese el segundo número: ")

                try:
                    if opcion == "1":
                        resultado = a + b
                        print(f"El resultado de la suma es: {resultado}")
                        guardar_historial(f"{a} + {b}", resultado)
                    elif opcion == "2":
                        resultado = a - b
                        print(f"El resultado de la resta es: {resultado}")
                        guardar_historial(f"{a} - {b}", resultado)
                    elif opcion == "3":
                        resultado = a * b
                        print(f"El resultado de la multiplicación es: {resultado}")
                        guardar_historial(f"{a} * {b}", resultado)
                    elif opcion == "4":
                        if b == 0:
                            raise ZeroDivisionError("No se puede dividir por cero.")
                        resultado = a / b
                        print(f"El resultado de la división es: {resultado}")
                        guardar_historial(f"{a} / {b}", resultado)
                except ZeroDivisionError as error:
                    print(f"Error: {error}")

            elif opcion == "5":
                ver_historial()

        

if __name__ == "__main__":
    main()
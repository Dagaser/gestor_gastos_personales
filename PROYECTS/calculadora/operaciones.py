def realizar_operacion(opcion, a, b):
    if opcion == "1":
        return a + b, f"{a} + {b}"
    elif opcion == "2":
        return a - b, f"{a} - {b}"
    elif opcion == "3":
        return a * b, f"{a} * {b}"
    elif opcion == "4":
        if b == 0:
            raise ZeroDivisionError("No se puede dividir entre cero.")
        return a / b, f"{a} / {b}"

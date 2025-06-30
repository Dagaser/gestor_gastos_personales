def leer_numero(mensaje):
    while True:
        try:
            numero = float(input(mensaje))
            return numero
        except ValueError:
            print("Entrada inválida. Por favor, ingrese un número válido.")
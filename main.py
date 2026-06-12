from ejercicio_p1 import (
    ft_ejecutar_practica_p1,
    ft_inicializar_api,
    ft_pedir_parametros_usuario,
)
from ejercicio_p2 import ft_main_p2


def ft_main():
    while True:
        print("\nMENU PRINCIPAL")
        print("=" * 14)
        print("1. P1 - Sentinel-2 L2A, NDVI y composiciones RGB")
        print("2. P2 - Deteccion de cambios post-incendio con dNBR")
        print("0. Salir")

        opcion = input("Selecciona una opcion [1]: ").strip() or "1"

        if opcion == "1":
            try:
                sesion_api = ft_inicializar_api()
                coordenadas_bbox, fechas_consulta, tamano_salida = ft_pedir_parametros_usuario()
                ft_ejecutar_practica_p1(
                    sesion_api,
                    coordenadas_bbox,
                    fechas_consulta,
                    tamano_salida=tamano_salida,
                )
            except Exception as error_programa:
                print(f"\n[ERROR CRITICO] {error_programa}")
            return

        if opcion == "2":
            ft_main_p2()
            return

        if opcion == "0":
            print("Saliendo.")
            return

        print("[AVISO] Opcion no valida. Elige 1, 2 o 0.")


if __name__ == "__main__":
    ft_main()

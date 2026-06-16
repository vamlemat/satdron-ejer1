from ejercicio_p1 import (
    ft_ejecutar_practica_p1,
    ft_inicializar_api,
    ft_pedir_parametros_usuario,
)
from ejercicio_p2 import ft_main_p2
from ejercicio_p3 import procesar_lidar
import os


def ft_main():
    while True:
        print("\nMENU PRINCIPAL")
        print("=" * 14)
        print("1. P1 - Sentinel-2 L2A, NDVI y composiciones RGB")
        print("2. P2 - Deteccion de cambios post-incendio con dNBR")
        print("3. P3 - Procesamiento de nube de puntos LiDAR")
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

        if opcion == "3":
            ruta_archivo = input("Introduce la ruta del archivo LiDAR (.las/.laz) [muestra_lidar.las]: ").strip() or "muestra_lidar.las"
            if not os.path.exists(ruta_archivo):
                print(f"\n[ERROR] No se encuentra el archivo: {ruta_archivo}")
            else:
                epsg = input("Introduce el código EPSG de tu archivo (ej. 25830 para España peninsular) [25830]: ").strip() or "25830"
                procesar_lidar(ruta_archivo, epsg=epsg)
            return

        if opcion == "0":
            print("Saliendo.")
            return

        print("[AVISO] Opcion no valida. Elige 1, 2, 3 o 0.")


if __name__ == "__main__":
    ft_main()

import os
from datetime import datetime

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from dotenv import load_dotenv
from rasterio.transform import from_bounds
from sentinelhub import (
    BBox,
    CRS,
    DataCollection,
    MimeType,
    MosaickingOrder,
    SHConfig,
    SentinelHubRequest,
)
import contextily as cx
import folium
from io import BytesIO
import base64
import webbrowser


COORDENADAS_BBOX_DEFECTO = [-4.56, 37.02, -4.54, 37.04]
RANGO_FECHAS_DEFECTO = ("2026-05-01", "2026-06-01")
TAMANO_SALIDA_DEFECTO = (512, 512)


def ft_formatear_porcentaje(valor):
    return f"{valor:.2f}%"


def ft_inicializar_api():
    """
    Carga las credenciales desde el archivo .env y configura la conexion
    contra Copernicus Data Space Ecosystem.
    """
    load_dotenv()

    id_cliente = os.getenv("SH_CLIENT_ID")
    secreto_cliente = os.getenv("SH_CLIENT_SECRET")

    if not id_cliente or not secreto_cliente:
        raise ValueError(
            "No se encontraron SH_CLIENT_ID o SH_CLIENT_SECRET en el archivo .env"
        )

    configuracion = SHConfig(use_defaults=True)
    configuracion.sh_client_id = id_cliente
    configuracion.sh_client_secret = secreto_cliente
    configuracion.sh_base_url = "https://sh.dataspace.copernicus.eu"
    configuracion.sh_token_url = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/"
        "protocol/openid-connect/token"
    )

    return configuracion


def ft_pedir_float(mensaje, valor_defecto):
    """
    Solicita un numero decimal por consola y permite usar un valor por defecto.
    """
    while True:
        valor_usuario = input(f"{mensaje} [{valor_defecto}]: ").strip()
        if not valor_usuario:
            return float(valor_defecto)

        try:
            return float(valor_usuario.replace(",", "."))
        except ValueError:
            print("[AVISO] Introduce un numero valido. Ejemplo: -4.56")


def ft_pedir_entero(mensaje, valor_defecto, minimo=1):
    """
    Solicita un numero entero por consola y permite usar un valor por defecto.
    """
    while True:
        valor_usuario = input(f"{mensaje} [{valor_defecto}]: ").strip()
        if not valor_usuario:
            return int(valor_defecto)

        try:
            valor = int(valor_usuario)
            if valor >= minimo:
                return valor
            print(f"[AVISO] El valor minimo permitido es {minimo}.")
        except ValueError:
            print("[AVISO] Introduce un numero entero valido. Ejemplo: 512")


def ft_pedir_texto(mensaje, valor_defecto):
    """
    Solicita texto por consola y permite usar un valor por defecto.
    """
    valor_usuario = input(f"{mensaje} [{valor_defecto}]: ").strip()
    return valor_usuario or valor_defecto


def ft_pedir_fecha(mensaje, valor_defecto):
    """
    Solicita una fecha en formato YYYY-MM-DD.
    """
    while True:
        valor = ft_pedir_texto(mensaje, valor_defecto)
        try:
            datetime.strptime(valor, "%Y-%m-%d")
            return valor
        except ValueError:
            print("[AVISO] Introduce una fecha valida en formato YYYY-MM-DD.")


def ft_validar_rango_fechas(fecha_inicio, fecha_fin):
    """
    Valida que el rango temporal tenga inicio anterior al fin.
    """
    inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    fin = datetime.strptime(fecha_fin, "%Y-%m-%d")

    if inicio >= fin:
        raise ValueError(
            "La fecha de inicio debe ser anterior a la fecha de fin. "
            "Usa un rango de varios dias, por ejemplo 2026-05-01 a 2026-06-01."
        )


def ft_pedir_parametros_usuario():
    """
    Solicita los parametros principales para generar la imagen satelital.
    """
    print("\nIntroduce las coordenadas del area en grados decimales (WGS84).")
    print("Orden esperado: oeste, sur, este, norte.")

    oeste = ft_pedir_float("Oeste / longitud minima", COORDENADAS_BBOX_DEFECTO[0])
    sur = ft_pedir_float("Sur / latitud minima", COORDENADAS_BBOX_DEFECTO[1])
    este = ft_pedir_float("Este / longitud maxima", COORDENADAS_BBOX_DEFECTO[2])
    norte = ft_pedir_float("Norte / latitud maxima", COORDENADAS_BBOX_DEFECTO[3])

    if oeste >= este:
        raise ValueError("La coordenada oeste debe ser menor que la coordenada este.")
    if sur >= norte:
        raise ValueError("La coordenada sur debe ser menor que la coordenada norte.")
    if not -180 <= oeste <= 180 or not -180 <= este <= 180:
        raise ValueError("Las longitudes deben estar entre -180 y 180.")
    if not -90 <= sur <= 90 or not -90 <= norte <= 90:
        raise ValueError("Las latitudes deben estar entre -90 y 90.")

    fecha_inicio = ft_pedir_fecha("Fecha inicio YYYY-MM-DD", RANGO_FECHAS_DEFECTO[0])
    fecha_fin = ft_pedir_fecha("Fecha fin YYYY-MM-DD", RANGO_FECHAS_DEFECTO[1])
    ft_validar_rango_fechas(fecha_inicio, fecha_fin)

    ancho = ft_pedir_entero("Ancho de salida en pixeles", TAMANO_SALIDA_DEFECTO[0])
    alto = ft_pedir_entero("Alto de salida en pixeles", TAMANO_SALIDA_DEFECTO[1])

    limites_bbox = BBox(bbox=[oeste, sur, este, norte], crs=CRS.WGS84)
    return limites_bbox, (fecha_inicio, fecha_fin), (ancho, alto)


def ft_calcular_estadisticas_ndvi(matriz_ndvi):
    """
    Calcula estadisticas descriptivas y rangos interpretables del NDVI.
    """
    valores_validos = matriz_ndvi[np.isfinite(matriz_ndvi)]

    if valores_validos.size == 0:
        raise ValueError("No hay valores NDVI validos para calcular estadisticas.")

    total_pixeles = valores_validos.size
    rangos = [
        ("NDVI < 0", valores_validos < 0, "agua, sombras, nubes o superficies sin vegetacion"),
        (
            "0 <= NDVI < 0.2",
            (valores_validos >= 0) & (valores_validos < 0.2),
            "suelo desnudo, urbano o vegetacion muy escasa",
        ),
        (
            "0.2 <= NDVI < 0.4",
            (valores_validos >= 0.2) & (valores_validos < 0.4),
            "vegetacion moderada o posiblemente estresada",
        ),
        ("NDVI >= 0.4", valores_validos >= 0.4, "vegetacion densa o sana"),
    ]

    distribucion = []
    for etiqueta, mascara, interpretacion in rangos:
        cantidad = int(mascara.sum())
        porcentaje = cantidad * 100 / total_pixeles
        distribucion.append(
            {
                "rango": etiqueta,
                "pixeles": cantidad,
                "porcentaje": porcentaje,
                "interpretacion": interpretacion,
            }
        )

    return {
        "pixeles_validos": int(total_pixeles),
        "minimo": float(valores_validos.min()),
        "maximo": float(valores_validos.max()),
        "media": float(valores_validos.mean()),
        "mediana": float(np.median(valores_validos)),
        "percentil_10": float(np.percentile(valores_validos, 10)),
        "percentil_25": float(np.percentile(valores_validos, 25)),
        "percentil_75": float(np.percentile(valores_validos, 75)),
        "percentil_90": float(np.percentile(valores_validos, 90)),
        "distribucion": distribucion,
    }


def ft_calcular_estadisticas_banda(matriz_banda):
    """
    Calcula estadisticas basicas para una banda raster.
    """
    valores_validos = matriz_banda[np.isfinite(matriz_banda)]

    if valores_validos.size == 0:
        raise ValueError("No hay valores validos para calcular estadisticas de banda.")

    return {
        "pixeles_validos": int(valores_validos.size),
        "minimo": float(valores_validos.min()),
        "maximo": float(valores_validos.max()),
        "media": float(valores_validos.mean()),
        "mediana": float(np.median(valores_validos)),
        "percentil_10": float(np.percentile(valores_validos, 10)),
        "percentil_90": float(np.percentile(valores_validos, 90)),
    }


def ft_normalizar_para_visualizar(matriz, percentil_minimo=2, percentil_maximo=98):
    """
    Normaliza una matriz a rango 0-1 usando percentiles para mejorar contraste.
    """
    valores_validos = matriz[np.isfinite(matriz)]
    if valores_validos.size == 0:
        return np.zeros_like(matriz, dtype="float32")

    minimo = np.percentile(valores_validos, percentil_minimo)
    maximo = np.percentile(valores_validos, percentil_maximo)

    if maximo <= minimo:
        return np.zeros_like(matriz, dtype="float32")

    matriz_normalizada = (matriz - minimo) / (maximo - minimo)
    return np.clip(matriz_normalizada, 0, 1).astype("float32")


def ft_crear_rgb_visual(*bandas):
    """
    Crea una imagen RGB normalizada a partir de tres bandas.
    """
    return np.dstack([ft_normalizar_para_visualizar(banda) for banda in bandas])


def ft_calcular_estadisticas_composiciones(
    banda_azul,
    banda_verde,
    banda_rojo,
    banda_nir,
):
    """
    Calcula estadisticas de las bandas usadas en color verdadero y falso color.
    """
    return {
        "color_verdadero": [
            {
                "canal": "Rojo",
                "banda": "B04",
                "descripcion": "reflectancia en rojo visible",
                "estadisticas": ft_calcular_estadisticas_banda(banda_rojo),
            },
            {
                "canal": "Verde",
                "banda": "B03",
                "descripcion": "reflectancia en verde visible",
                "estadisticas": ft_calcular_estadisticas_banda(banda_verde),
            },
            {
                "canal": "Azul",
                "banda": "B02",
                "descripcion": "reflectancia en azul visible",
                "estadisticas": ft_calcular_estadisticas_banda(banda_azul),
            },
        ],
        "falso_color": [
            {
                "canal": "Rojo",
                "banda": "B08",
                "descripcion": "infrarrojo cercano asignado al canal rojo",
                "estadisticas": ft_calcular_estadisticas_banda(banda_nir),
            },
            {
                "canal": "Verde",
                "banda": "B04",
                "descripcion": "rojo visible asignado al canal verde",
                "estadisticas": ft_calcular_estadisticas_banda(banda_rojo),
            },
            {
                "canal": "Azul",
                "banda": "B03",
                "descripcion": "verde visible asignado al canal azul",
                "estadisticas": ft_calcular_estadisticas_banda(banda_verde),
            },
        ],
        "bandas_originales": {
            "B02": ft_calcular_estadisticas_banda(banda_azul),
            "B03": ft_calcular_estadisticas_banda(banda_verde),
            "B04": ft_calcular_estadisticas_banda(banda_rojo),
            "B08": ft_calcular_estadisticas_banda(banda_nir),
        },
    }


def ft_interpretar_ndvi_medio(valor_medio):
    """
    Devuelve una interpretacion breve a partir del NDVI medio.
    """
    if valor_medio < 0:
        return "predominan agua, sombras, nubes o superficies sin vegetacion."
    if valor_medio < 0.2:
        return "predominan suelo desnudo, zonas urbanas o vegetacion muy escasa."
    if valor_medio < 0.4:
        return "predomina vegetacion moderada o posiblemente estresada."
    return "predomina vegetacion densa o sana."


def ft_todas_las_bandas_son_cero(estadisticas_composiciones):
    """
    Detecta si todas las bandas descargadas tienen valor maximo cero.
    """
    return all(
        estadisticas["maximo"] == 0
        for estadisticas in estadisticas_composiciones["bandas_originales"].values()
    )


def ft_generar_texto_resumen_ndvi(
    estadisticas,
    estadisticas_composiciones,
    limites_bbox,
    rango_fechas,
    tamano_salida,
):
    """
    Genera un informe de texto con los parametros usados y resultados NDVI.
    """
    oeste, sur, este, norte = tuple(limites_bbox)
    ancho, alto = tamano_salida

    lineas = [
        "RESUMEN FINAL DE RESULTADOS - PRACTICA P1",
        "=" * 48,
        "",
        "PARAMETROS DE ENTRADA",
        "-" * 22,
        f"Nivel de procesamiento: Sentinel-2 L2A",
        f"Coleccion: s2l2a_cdse",
        f"Bounding box WGS84: oeste={oeste}, sur={sur}, este={este}, norte={norte}",
        f"Rango de fechas: {rango_fechas[0]} a {rango_fechas[1]}",
        f"Tamano de salida: {ancho} x {alto} pixeles",
        "",
        "ARCHIVOS GENERADOS",
        "-" * 18,
        "p1_resultado_ndvi.tif",
        "p1_color_verdadero.tif",
        "p1_falso_color.tif",
        "p1_resumen_resultados.txt",
        "",
        "VALORES DE COLOR VERDADERO",
        "-" * 27,
    ]

    for elemento in estadisticas_composiciones["color_verdadero"]:
        stats = elemento["estadisticas"]
        lineas.extend(
            [
                f"Canal {elemento['canal']} = {elemento['banda']} ({elemento['descripcion']})",
                f"  Minimo: {stats['minimo']:.6f}",
                f"  Maximo: {stats['maximo']:.6f}",
                f"  Media: {stats['media']:.6f}",
                f"  Mediana: {stats['mediana']:.6f}",
                f"  Percentil 10: {stats['percentil_10']:.6f}",
                f"  Percentil 90: {stats['percentil_90']:.6f}",
            ]
        )

    lineas.extend(
        [
            "",
            "LECTURA DEL COLOR VERDADERO",
            "-" * 29,
            "Esta composicion usa bandas visibles: B04, B03 y B02.",
            "Se parece a una fotografia normal y ayuda a reconocer visualmente suelo, caminos, nubes, agua y zonas urbanas.",
            "Valores mas altos en un canal significan mayor reflectancia en esa banda visible.",
            "",
            "VALORES DE FALSO COLOR",
            "-" * 22,
        ]
    )

    for elemento in estadisticas_composiciones["falso_color"]:
        stats = elemento["estadisticas"]
        lineas.extend(
            [
                f"Canal {elemento['canal']} = {elemento['banda']} ({elemento['descripcion']})",
                f"  Minimo: {stats['minimo']:.6f}",
                f"  Maximo: {stats['maximo']:.6f}",
                f"  Media: {stats['media']:.6f}",
                f"  Mediana: {stats['mediana']:.6f}",
                f"  Percentil 10: {stats['percentil_10']:.6f}",
                f"  Percentil 90: {stats['percentil_90']:.6f}",
            ]
        )

    lineas.extend(
        [
            "",
            "LECTURA DEL FALSO COLOR",
            "-" * 23,
            "Esta composicion coloca el infrarrojo cercano B08 en el canal rojo.",
            "La vegetacion sana suele destacar porque refleja mas en B08 que en B04.",
            "Si la media de B08 es claramente superior a la de B04, suele haber mas respuesta vegetal.",
            "Si B08 y B04 son parecidos o bajos, la vegetacion suele ser escasa o estar poco activa.",
            "",
            "ESTADISTICAS NDVI",
            "-" * 18,
            f"Pixeles validos: {estadisticas['pixeles_validos']}",
            f"NDVI minimo: {estadisticas['minimo']:.6f}",
            f"NDVI maximo: {estadisticas['maximo']:.6f}",
            f"NDVI medio: {estadisticas['media']:.6f}",
            f"NDVI mediana: {estadisticas['mediana']:.6f}",
            f"Percentil 10: {estadisticas['percentil_10']:.6f}",
            f"Percentil 25: {estadisticas['percentil_25']:.6f}",
            f"Percentil 75: {estadisticas['percentil_75']:.6f}",
            f"Percentil 90: {estadisticas['percentil_90']:.6f}",
            "",
            "DISTRIBUCION POR RANGOS",
            "-" * 24,
        ]
    )

    for elemento in estadisticas["distribucion"]:
        lineas.append(
            f"{elemento['rango']}: {elemento['pixeles']} pixeles "
            f"({ft_formatear_porcentaje(elemento['porcentaje'])})"
        )
        lineas.append(f"  Interpretacion: {elemento['interpretacion']}")

    lineas.extend(
        [
            "",
            "ADVERTENCIAS",
            "-" * 12,
        ]
    )

    if ft_todas_las_bandas_son_cero(estadisticas_composiciones):
        lineas.extend(
            [
                "Todas las bandas descargadas tienen valor maximo 0.",
                "Esto suele indicar que la zona o el rango temporal no devolvio reflectancias utiles.",
                "Recomendacion: probar otro rango de fechas, reducir/cambiar el bounding box o revisar nubosidad/disponibilidad.",
            ]
        )
    else:
        lineas.append("No se detectan bandas completamente vacias en el resumen estadistico.")

    lineas.extend(
        [
            "",
            "INTERPRETACION GLOBAL",
            "-" * 21,
            f"Segun el NDVI medio, {ft_interpretar_ndvi_medio(estadisticas['media'])}",
            "",
            "LECTURA RAPIDA",
            "-" * 14,
            "Valores altos indican mayor presencia o vigor de vegetacion.",
            "Valores bajos indican suelo desnudo, urbano, vegetacion escasa o superficies no vegetales.",
            "Valores negativos suelen asociarse a agua, sombras o nubes.",
        ]
    )

    return "\n".join(lineas)


def ft_guardar_y_mostrar_resumen(
    estadisticas,
    estadisticas_composiciones,
    limites_bbox,
    rango_fechas,
    tamano_salida,
    ruta_salida="p1_resumen_resultados.txt",
):
    """
    Muestra el resumen por pantalla y lo guarda en un archivo de texto.
    """
    resumen = ft_generar_texto_resumen_ndvi(
        estadisticas,
        estadisticas_composiciones,
        limites_bbox,
        rango_fechas,
        tamano_salida,
    )

    print("\n" + resumen)

    with open(ruta_salida, "w", encoding="utf-8") as archivo:
        archivo.write(resumen)
        archivo.write("\n")

    print(f"\n[OK] Resumen numerico exportado: {ruta_salida}")


def ft_generar_panel_visual(
    banda_azul,
    banda_verde,
    banda_rojo,
    banda_nir,
    matriz_ndvi,
    estadisticas_ndvi,
    limites_bbox,
    ruta_salida="p1_panel_visual.png",
):
    """
    Genera una figura PNG con color verdadero, falso color, NDVI e histograma.
    """
    color_verdadero = ft_crear_rgb_visual(banda_rojo, banda_verde, banda_azul)
    falso_color = ft_crear_rgb_visual(banda_nir, banda_rojo, banda_verde)
    valores_ndvi = matriz_ndvi[np.isfinite(matriz_ndvi)]

    fig, ejes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    fig.suptitle("Practica P1 - Sentinel-2 L2A y NDVI", fontsize=16, fontweight="bold")

    ejes[0, 0].imshow(color_verdadero)
    ejes[0, 0].set_title("Color verdadero (B04, B03, B02)")
    ejes[0, 0].axis("off")

    ejes[0, 1].imshow(falso_color)
    ejes[0, 1].set_title("Falso color (B08, B04, B03)")
    ejes[0, 1].axis("off")

    imagen_ndvi = ejes[1, 0].imshow(matriz_ndvi, cmap="RdYlGn", vmin=-1, vmax=1)
    ejes[1, 0].set_title("NDVI")
    ejes[1, 0].axis("off")
    fig.colorbar(imagen_ndvi, ax=ejes[1, 0], fraction=0.046, pad=0.04)

    ejes[1, 1].hist(valores_ndvi, bins=40, color="#4C78A8", edgecolor="white")
    ejes[1, 1].axvline(0.2, color="#F58518", linestyle="--", linewidth=1.5, label="0.2")
    ejes[1, 1].axvline(0.4, color="#54A24B", linestyle="--", linewidth=1.5, label="0.4")
    ejes[1, 1].axvline(
        estadisticas_ndvi["media"],
        color="#B279A2",
        linestyle="-",
        linewidth=2,
        label=f"Media {estadisticas_ndvi['media']:.3f}",
    )
    ejes[1, 1].set_title("Distribucion de valores NDVI")
    ejes[1, 1].set_xlabel("NDVI")
    ejes[1, 1].set_ylabel("Numero de pixeles")
    ejes[1, 1].legend()
    ejes[1, 1].grid(alpha=0.25)

    fig.text(
        0.5,
        0.01,
        (
            f"NDVI min={estadisticas_ndvi['minimo']:.3f} | "
            f"media={estadisticas_ndvi['media']:.3f} | "
            f"max={estadisticas_ndvi['maximo']:.3f}"
        ),
        ha="center",
        fontsize=11,
    )

    fig.savefig(ruta_salida, dpi=180)
    plt.close(fig)

    print(f"[OK] Panel visual exportado: {ruta_salida}")

def ft_generar_mapa_interactivo_p1(
    banda_azul,
    banda_verde,
    banda_rojo,
    banda_nir,
    matriz_ndvi,
    limites_bbox,
    ruta_salida="p1_mapa_interactivo.html"
):
    """
    Genera un mapa HTML interactivo con Color Verdadero, Falso Color y NDVI, mas leyendas.
    """
    oeste, sur, este, norte = tuple(limites_bbox)
    centro_lat = (sur + norte) / 2.0
    centro_lon = (oeste + este) / 2.0
    
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=13, control_scale=True)
    
    # Capa de satélite estilo Google Earth (Esri World Imagery)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Esri Satellite',
        overlay=False,
        control=True
    ).add_to(m)

    # Convertir bandas RGB a matriz visual
    color_verdadero = ft_crear_rgb_visual(banda_rojo, banda_verde, banda_azul)
    falso_color = ft_crear_rgb_visual(banda_nir, banda_rojo, banda_verde)
    
    def rgb_a_url(matriz_rgb):
        fig, ax = plt.subplots(figsize=(matriz_rgb.shape[1]/100, matriz_rgb.shape[0]/100), dpi=100)
        fig.patch.set_alpha(0)
        ax.axis('off')
        ax.imshow(matriz_rgb)
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close(fig)
        buf.seek(0)
        return f"data:image/png;base64,{base64.b64encode(buf.read()).decode('utf-8')}"

    def ndvi_a_url(matriz, alpha=0.85):
        fig, ax = plt.subplots(figsize=(matriz.shape[1]/100, matriz.shape[0]/100), dpi=100)
        fig.patch.set_alpha(0)
        ax.axis('off')
        cmap = plt.get_cmap("RdYlGn")
        norm = plt.Normalize(vmin=-1, vmax=1)
        rgba = cmap(norm(matriz))
        rgba[matriz < 0, 3] = 0.2
        rgba[matriz >= 0, 3] = alpha
        ax.imshow(rgba)
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close(fig)
        buf.seek(0)
        return f"data:image/png;base64,{base64.b64encode(buf.read()).decode('utf-8')}"

    bounds = [[sur, oeste], [norte, este]]

    folium.raster_layers.ImageOverlay(
        image=rgb_a_url(color_verdadero),
        bounds=bounds,
        name="Color Verdadero (B04, B03, B02)",
        show=False,
    ).add_to(m)

    folium.raster_layers.ImageOverlay(
        image=rgb_a_url(falso_color),
        bounds=bounds,
        name="Falso Color (B08, B04, B03)",
        show=False,
    ).add_to(m)

    folium.raster_layers.ImageOverlay(
        image=ndvi_a_url(matriz_ndvi),
        bounds=bounds,
        name="NDVI (Indice de Vegetacion)",
        show=True,
    ).add_to(m)
    
    folium.Rectangle(
        bounds=bounds,
        color="#ff0000",
        fill=False,
        weight=2,
        name="Area de estudio"
    ).add_to(m)
    
    # Leyendas dinamicas HTML
    leyenda_html = """
    <div id="leyenda_verdadero" style="position: fixed; bottom: 50px; right: 50px; width: 280px; height: auto; 
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px; border-radius: 5px; display: none;">
         <b>Color Verdadero (RGB)</b><br>
         <span style="font-size:12px;">Refleja la visión humana.</span><br>
         <ul style="margin-bottom:0; padding-left:20px; font-size:12px;">
            <li><b>Vegetación:</b> Tonos verdes</li>
            <li><b>Suelo desnudo:</b> Marrón / claro</li>
            <li><b>Agua:</b> Azul oscuro / negro</li>
         </ul>
    </div>

    <div id="leyenda_falso" style="position: fixed; bottom: 50px; right: 50px; width: 280px; height: auto; 
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px; border-radius: 5px; display: none;">
         <b>Falso Color (NIR)</b><br>
         <span style="font-size:12px;">Resalta el vigor vegetal.</span><br>
         <ul style="margin-bottom:0; padding-left:20px; font-size:12px;">
            <li><b>Vegetación densa:</b> Rojo intenso</li>
            <li><b>Suelo desnudo:</b> Tonos cian/grises</li>
            <li><b>Agua:</b> Negro profundo</li>
         </ul>
    </div>

    <div id="leyenda_ndvi" style="position: fixed; bottom: 50px; right: 50px; width: 280px; height: auto; 
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px; border-radius: 5px; display: block;">
         <b>NDVI (Normalized Difference Veg. Index)</b><br>
         <div style="background: linear-gradient(to right, #a50026, #f46d43, #ffffbf, #66bd63, #006837); 
                     width: 100%; height: 20px; margin-top: 5px; margin-bottom: 5px;"></div>
         <span style="float:left;">-1.0</span>
         <span style="float:right;">1.0</span>
         <div style="clear:both;"></div>
         <span style="font-size:11px;">Rojo: Agua/Nubes | Verde: Vegetación Densa</span>
    </div>

    <script>
        setTimeout(function() {
            var map_keys = Object.keys(window).filter(k => k.startsWith('map_'));
            if(map_keys.length > 0) {
                var myMap = window[map_keys[0]];
                
                myMap.on('overlayadd', function(eventLayer) {
                    if (eventLayer.name === 'Color Verdadero (B04, B03, B02)') {
                        document.getElementById('leyenda_verdadero').style.display = 'block';
                    } else if (eventLayer.name === 'Falso Color (B08, B04, B03)') {
                        document.getElementById('leyenda_falso').style.display = 'block';
                    } else if (eventLayer.name === 'NDVI (Indice de Vegetacion)') {
                        document.getElementById('leyenda_ndvi').style.display = 'block';
                    }
                });
                
                myMap.on('overlayremove', function(eventLayer) {
                    if (eventLayer.name === 'Color Verdadero (B04, B03, B02)') {
                        document.getElementById('leyenda_verdadero').style.display = 'none';
                    } else if (eventLayer.name === 'Falso Color (B08, B04, B03)') {
                        document.getElementById('leyenda_falso').style.display = 'none';
                    } else if (eventLayer.name === 'NDVI (Indice de Vegetacion)') {
                        document.getElementById('leyenda_ndvi').style.display = 'none';
                    }
                });
            }
        }, 1000);
    </script>
    """
    m.get_root().html.add_child(folium.Element(leyenda_html))
    
    folium.LayerControl().add_to(m)
    m.save(ruta_salida)
    print(f"[OK] Mapa interactivo satelital exportado: {ruta_salida}")
    
    # Abrir automaticamente en el navegador
    import os
    ruta_absoluta = os.path.abspath(ruta_salida)
    webbrowser.open('file://' + ruta_absoluta)


def ft_ejecutar_practica_p1(
    configuracion_api,
    limites_bbox,
    rango_fechas,
    tamano_salida=(512, 512),
):
    """
    Descarga bandas Sentinel-2 L2A, calcula el NDVI y exporta composiciones
    georreferenciadas en formato GeoTIFF.
    """
    evalscript_p1 = """
//VERSION=3
function setup() {
  return {
    input: ["B02", "B03", "B04", "B08"],
    output: { bands: 4, sampleType: "FLOAT32" }
  };
}

function evaluatePixel(samples) {
  return [samples.B02, samples.B03, samples.B04, samples.B08];
}
"""

    print("[INFO] Descargando bandas B02, B03, B04 y B08 de Sentinel-2...")

    peticion = SentinelHubRequest(
        evalscript=evalscript_p1,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A.define_from(
                    "s2l2a_cdse",
                    service_url=configuracion_api.sh_base_url,
                ),
                time_interval=rango_fechas,
                maxcc=0.3,
                mosaicking_order=MosaickingOrder.LEAST_CC,
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=limites_bbox,
        size=tamano_salida,
        config=configuracion_api,
    )

    lista_datos = peticion.get_data()
    if not lista_datos:
        print("[ERROR] La API no devolvio datos para los parametros indicados.")
        return

    matriz_p1 = lista_datos[0].astype("float32")

    banda_azul = matriz_p1[:, :, 0]
    banda_verde = matriz_p1[:, :, 1]
    banda_rojo = matriz_p1[:, :, 2]
    banda_nir = matriz_p1[:, :, 3]

    denominador_ndvi = banda_nir + banda_rojo
    matriz_ndvi = np.divide(
        banda_nir - banda_rojo,
        denominador_ndvi,
        out=np.zeros_like(banda_nir, dtype="float32"),
        where=denominador_ndvi != 0,
    )
    estadisticas_ndvi = ft_calcular_estadisticas_ndvi(matriz_ndvi)
    estadisticas_composiciones = ft_calcular_estadisticas_composiciones(
        banda_azul,
        banda_verde,
        banda_rojo,
        banda_nir,
    )

    alto, ancho = matriz_ndvi.shape
    oeste, sur, este, norte = tuple(limites_bbox)

    metadatos_base = {
        "driver": "GTiff",
        "dtype": "float32",
        "nodata": None,
        "width": ancho,
        "height": alto,
        "count": 1,
        "crs": CRS.WGS84.pyproj_crs(),
        "transform": from_bounds(oeste, sur, este, norte, ancho, alto),
    }

    ruta_salida_ndvi = "p1_resultado_ndvi.tif"
    with rasterio.open(ruta_salida_ndvi, "w", **metadatos_base) as destino_ndvi:
        destino_ndvi.write(matriz_ndvi, 1)
    print(f"[OK] NDVI exportado: {ruta_salida_ndvi}")

    metadatos_multicanal = metadatos_base.copy()
    metadatos_multicanal.update(count=3)

    ruta_salida_verdadero = "p1_color_verdadero.tif"
    with rasterio.open(ruta_salida_verdadero, "w", **metadatos_multicanal) as destino_rgb:
        destino_rgb.write(banda_rojo, 1)
        destino_rgb.write(banda_verde, 2)
        destino_rgb.write(banda_azul, 3)
    print(f"[OK] Color verdadero exportado: {ruta_salida_verdadero}")

    ruta_salida_falso = "p1_falso_color.tif"
    with rasterio.open(ruta_salida_falso, "w", **metadatos_multicanal) as destino_falso:
        destino_falso.write(banda_nir, 1)
        destino_falso.write(banda_rojo, 2)
        destino_falso.write(banda_verde, 3)
    print(f"[OK] Falso color exportado: {ruta_salida_falso}")

    ft_guardar_y_mostrar_resumen(
        estadisticas_ndvi,
        estadisticas_composiciones,
        limites_bbox,
        rango_fechas,
        tamano_salida,
    )
    ft_generar_panel_visual(
        banda_azul,
        banda_verde,
        banda_rojo,
        banda_nir,
        matriz_ndvi,
        estadisticas_ndvi,
        limites_bbox,
    )
    ft_generar_mapa_interactivo_p1(
        banda_azul,
        banda_verde,
        banda_rojo,
        banda_nir,
        matriz_ndvi,
        limites_bbox
    )


if __name__ == "__main__":
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

import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from sentinelhub import BBox, CRS, DataCollection, MimeType, MosaickingOrder, SentinelHubRequest
import contextily as cx
import folium
from io import BytesIO
import base64
import webbrowser

from ejercicio_p1 import (
    TAMANO_SALIDA_DEFECTO,
    ft_formatear_porcentaje,
    ft_inicializar_api,
    ft_pedir_entero,
    ft_pedir_fecha,
    ft_pedir_float,
    ft_validar_rango_fechas,
    ft_calcular_bbox_desde_centro,
)

def fmt_num(valor, decimales=6):
    return f"{valor:.{decimales}f}".replace('.', ',')


BANDA_NIR_DEFECTO = 1
BANDA_SWIR2_DEFECTO = 2
COORDENADAS_BBOX_P2_DEFECTO = [16.56, 43.46, 16.76, 43.56]
RANGO_PRE_INCENDIO_DEFECTO = ("2018-07-05", "2018-07-10")
RANGO_POST_INCENDIO_DEFECTO = ("2018-07-20", "2018-07-25")
MAX_NUBOSIDAD_P2 = 1.0

CLASES_SEVERIDAD = [
    {
        "valor": 1,
        "nombre": "Sin cambio o no quemado",
        "minimo": -np.inf,
        "maximo": 0.10,
        "color": "#2ca25f",
    },
    {
        "valor": 2,
        "nombre": "Severidad baja",
        "minimo": 0.10,
        "maximo": 0.27,
        "color": "#ffeda0",
    },
    {
        "valor": 3,
        "nombre": "Severidad moderada",
        "minimo": 0.27,
        "maximo": 0.66,
        "color": "#feb24c",
    },
    {
        "valor": 4,
        "nombre": "Severidad alta",
        "minimo": 0.66,
        "maximo": np.inf,
        "color": "#de2d26",
    },
]


def ft_pedir_ruta_imagen(mensaje):
    """
    Solicita una ruta de imagen raster existente.
    """
    while True:
        ruta = input(f"{mensaje}: ").strip().strip('"').strip("'")
        if os.path.isfile(ruta):
            return ruta
        print("[AVISO] No se encontro el archivo. Revisa la ruta e intentalo de nuevo.")


def ft_pedir_parametros_usuario_p2_api():
    """
    Solicita coordenadas y rangos temporales para descargar imagenes por API.
    """
    print("\nP2 - Deteccion de cambios post-incendio con dNBR")
    print("Se descargaran dos imagenes Sentinel-2 L2A por API:")
    print("- imagen PRE-incendio")
    print("- imagen POST-incendio")
    
    print("\n¿Como desea definir el area de estudio?")
    print("1. Bounding Box manual (Oeste, Sur, Este, Norte) [Por defecto]")
    print("2. Coordenada central (Latitud, Longitud) y tamaño en pixeles")
    
    modo = input("Elige una opcion (1 o 2) [1]: ").strip()
    
    if modo == "2":
        latitud = ft_pedir_float("Latitud central (ej. 43.51)", 43.51)
        longitud = ft_pedir_float("Longitud central (ej. 16.66)", 16.66)
        ancho = ft_pedir_entero("Ancho de salida en pixeles (1px=10m)", TAMANO_SALIDA_DEFECTO[0])
        alto = ft_pedir_entero("Alto de salida en pixeles (1px=10m)", TAMANO_SALIDA_DEFECTO[1])
        
        oeste, sur, este, norte = ft_calcular_bbox_desde_centro(latitud, longitud, ancho, alto)
        print(f"\n[INFO] Bounding Box calculado automáticamente: Oeste={oeste:.5f}, Sur={sur:.5f}, Este={este:.5f}, Norte={norte:.5f}")
    else:
        print("\nIntroduce las coordenadas del area en grados decimales (WGS84).")
        print("Orden esperado: oeste, sur, este, norte.")

        oeste = ft_pedir_float("Oeste / longitud minima", COORDENADAS_BBOX_P2_DEFECTO[0])
        sur = ft_pedir_float("Sur / latitud minima", COORDENADAS_BBOX_P2_DEFECTO[1])
        este = ft_pedir_float("Este / longitud maxima", COORDENADAS_BBOX_P2_DEFECTO[2])
        norte = ft_pedir_float("Norte / latitud maxima", COORDENADAS_BBOX_P2_DEFECTO[3])

        ancho = ft_pedir_entero("Ancho de salida en pixeles", TAMANO_SALIDA_DEFECTO[0])
        alto = ft_pedir_entero("Alto de salida en pixeles", TAMANO_SALIDA_DEFECTO[1])

    if oeste >= este:
        raise ValueError("La coordenada oeste debe ser menor que la coordenada este.")
    if sur >= norte:
        raise ValueError("La coordenada sur debe ser menor que la coordenada norte.")
    if not -180 <= oeste <= 180 or not -180 <= este <= 180:
        raise ValueError("Las longitudes deben estar entre -180 y 180.")
    if not -90 <= sur <= 90 or not -90 <= norte <= 90:
        raise ValueError("Las latitudes deben estar entre -90 y 90.")

    print("\nRango temporal PRE-incendio")
    pre_inicio = ft_pedir_fecha("Fecha inicio PRE YYYY-MM-DD", RANGO_PRE_INCENDIO_DEFECTO[0])
    pre_fin = ft_pedir_fecha("Fecha fin PRE YYYY-MM-DD", RANGO_PRE_INCENDIO_DEFECTO[1])
    ft_validar_rango_fechas(pre_inicio, pre_fin)

    print("\nRango temporal POST-incendio")
    post_inicio = ft_pedir_fecha("Fecha inicio POST YYYY-MM-DD", RANGO_POST_INCENDIO_DEFECTO[0])
    post_fin = ft_pedir_fecha("Fecha fin POST YYYY-MM-DD", RANGO_POST_INCENDIO_DEFECTO[1])
    ft_validar_rango_fechas(post_inicio, post_fin)

    limites_bbox = BBox(bbox=[oeste, sur, este, norte], crs=CRS.WGS84)
    return limites_bbox, (pre_inicio, pre_fin), (post_inicio, post_fin), (ancho, alto)


def ft_descargar_bandas_nbr(configuracion_api, limites_bbox, rango_fechas, tamano_salida):
    """
    Descarga B08 y B12 de Sentinel-2 L2A para calcular NBR.
    """
    evalscript = """
//VERSION=3
function setup() {
  return {
    input: ["B08", "B12", "dataMask"],
    output: { bands: 3, sampleType: "FLOAT32" }
  };
}

function evaluatePixel(samples) {
  return [samples.B08, samples.B12, samples.dataMask];
}
"""

    peticion = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A.define_from(
                    "s2l2a_cdse",
                    service_url=configuracion_api.sh_base_url,
                ),
                time_interval=rango_fechas,
                maxcc=MAX_NUBOSIDAD_P2,
                mosaicking_order=MosaickingOrder.LEAST_CC,
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=limites_bbox,
        size=tamano_salida,
        config=configuracion_api,
    )

    datos = peticion.get_data()
    if not datos:
        raise ValueError("La API no devolvio datos para el rango indicado.")

    matriz = datos[0].astype("float32")
    data_mask = matriz[:, :, 2]
    if np.nansum(data_mask) == 0:
        raise ValueError(
            "La descarga no contiene pixeles validos segun dataMask. "
            "Prueba a ampliar fechas o revisar el area de estudio."
        )

    return matriz[:, :, 0], matriz[:, :, 1]


def ft_leer_bandas_nbr_desde_imagen(
    ruta_imagen,
    banda_nir=BANDA_NIR_DEFECTO,
    banda_swir2=BANDA_SWIR2_DEFECTO,
):
    """
    Lee B08 y B12 desde una imagen multibanda local.
    """
    dataset = rasterio.open(ruta_imagen)

    if dataset.count < max(banda_nir, banda_swir2):
        dataset.close()
        raise ValueError(
            f"La imagen {ruta_imagen} tiene {dataset.count} banda(s), "
            f"pero se necesitan al menos {max(banda_nir, banda_swir2)}."
        )

    banda_nir_matriz = dataset.read(banda_nir).astype("float32")
    banda_swir2_matriz = dataset.read(banda_swir2).astype("float32")
    perfil = dataset.profile.copy()
    forma = (dataset.height, dataset.width)
    crs = dataset.crs
    transform = dataset.transform
    bounds = dataset.bounds
    dataset.close()

    return {
        "nir": banda_nir_matriz,
        "swir2": banda_swir2_matriz,
        "perfil": perfil,
        "forma": forma,
        "crs": crs,
        "transform": transform,
        "bounds": bounds,
    }


def ft_validar_compatibilidad_imagenes(datos_pre, datos_post):
    """
    Comprueba que ambas imagenes se puedan comparar pixel a pixel.
    """
    if datos_pre["forma"] != datos_post["forma"]:
        raise ValueError(
            "Las imagenes PRE y POST no tienen el mismo tamano. "
            "Deben estar recortadas y remuestreadas a la misma malla."
        )

    if datos_pre["crs"] != datos_post["crs"]:
        raise ValueError("Las imagenes PRE y POST no tienen el mismo CRS.")

    if datos_pre["transform"] != datos_post["transform"]:
        raise ValueError(
            "Las imagenes PRE y POST no tienen la misma georreferenciacion. "
            "Deben coincidir para poder comparar pixel a pixel."
        )


def ft_calcular_indice_normalizado(banda_a, banda_b):
    """
    Calcula (A - B) / (A + B) evitando divisiones por cero.
    """
    denominador = banda_a + banda_b
    return np.divide(
        banda_a - banda_b,
        denominador,
        out=np.zeros_like(banda_a, dtype="float32"),
        where=denominador != 0,
    )


def ft_calcular_estadisticas_genericas(matriz):
    valores_validos = matriz[np.isfinite(matriz)]
    if valores_validos.size == 0:
        raise ValueError("No hay valores validos para calcular estadisticas.")

    return {
        "pixeles_validos": int(valores_validos.size),
        "minimo": float(valores_validos.min()),
        "maximo": float(valores_validos.max()),
        "media": float(valores_validos.mean()),
        "mediana": float(np.median(valores_validos)),
        "percentil_10": float(np.percentile(valores_validos, 10)),
        "percentil_25": float(np.percentile(valores_validos, 25)),
        "percentil_75": float(np.percentile(valores_validos, 75)),
        "percentil_90": float(np.percentile(valores_validos, 90)),
    }


def ft_clasificar_severidad_dnbr(matriz_dnbr):
    """
    Clasifica dNBR en cuatro clases de severidad.
    """
    clases = np.zeros_like(matriz_dnbr, dtype="uint8")
    for clase in CLASES_SEVERIDAD:
        mascara = (matriz_dnbr >= clase["minimo"]) & (matriz_dnbr < clase["maximo"])
        clases[mascara] = clase["valor"]
    return clases


def ft_resumir_clases_severidad(matriz_clases):
    total = matriz_clases.size
    resumen = []
    for clase in CLASES_SEVERIDAD:
        pixeles = int((matriz_clases == clase["valor"]).sum())
        porcentaje = pixeles * 100 / total
        resumen.append(
            {
                "valor": clase["valor"],
                "nombre": clase["nombre"],
                "pixeles": pixeles,
                "porcentaje": porcentaje,
            }
        )
    return resumen


def ft_exportar_geotiff_monobanda(ruta_salida, matriz, perfil_base, dtype="float32"):
    perfil = perfil_base.copy()
    perfil.update(
        driver="GTiff",
        dtype=dtype,
        count=1,
        nodata=None,
    )
    with rasterio.open(ruta_salida, "w", **perfil) as destino:
        destino.write(matriz.astype(dtype), 1)
    print(f"[OK] GeoTIFF exportado: {ruta_salida}")


def ft_crear_perfil_desde_bbox(matriz, limites_bbox, dtype="float32"):
    alto, ancho = matriz.shape
    oeste, sur, este, norte = tuple(limites_bbox)
    return {
        "driver": "GTiff",
        "dtype": dtype,
        "nodata": None,
        "width": ancho,
        "height": alto,
        "count": 1,
        "crs": CRS.WGS84.pyproj_crs(),
        "transform": from_bounds(oeste, sur, este, norte, ancho, alto),
    }


def ft_generar_resumen_p2(
    estadisticas_pre,
    estadisticas_post,
    estadisticas_dnbr,
    resumen_clases,
    limites_bbox,
    rango_pre,
    rango_post,
    tamano_salida,
    ruta_salida="p2_resumen_resultados.txt",
):
    oeste, sur, este, norte = tuple(limites_bbox)
    ancho, alto = tamano_salida

    lineas = [
        "RESUMEN FINAL DE RESULTADOS - PRACTICA P2",
        "=" * 48,
        "",
        "PARAMETROS DE ENTRADA",
        "-" * 22,
        "Metodo: descarga por API de dos imagenes Sentinel-2 L2A PRE y POST incendio",
        "Coleccion: s2l2a_cdse",
        "Bandas usadas: B08 (NIR) y B12 (SWIR2)",
        f"Filtro de nubosidad maxcc: {fmt_num(MAX_NUBOSIDAD_P2, 2)}",
        f"Bounding box WGS84: oeste={fmt_num(oeste,2)}, sur={fmt_num(sur,2)}, este={fmt_num(este,2)}, norte={fmt_num(norte,2)}",
        f"Rango PRE-incendio: {rango_pre[0]} a {rango_pre[1]}",
        f"Rango POST-incendio: {rango_post[0]} a {rango_post[1]}",
        f"Tamano: {ancho} x {alto} pixeles",
        "",
        "FORMULAS",
        "-" * 8,
        "NBR = (B08 - B12) / (B08 + B12)",
        "dNBR = NBR_pre - NBR_post",
        "",
        "ARCHIVOS GENERADOS",
        "-" * 18,
        "p2_nbr_pre.tif",
        "p2_nbr_post.tif",
        "p2_dnbr.tif",
        "p2_severidad_incendio.tif",
        "p2_resumen_resultados.txt",
        "p2_panel_visual.png",
        "",
        "ESTADISTICAS NBR PRE-INCENDIO",
        "-" * 31,
        f"Minimo: {fmt_num(estadisticas_pre['minimo'])}",
        f"Maximo: {fmt_num(estadisticas_pre['maximo'])}",
        f"Media: {fmt_num(estadisticas_pre['media'])}",
        f"Mediana: {fmt_num(estadisticas_pre['mediana'])}",
        "",
        "ESTADISTICAS NBR POST-INCENDIO",
        "-" * 32,
        f"Minimo: {fmt_num(estadisticas_post['minimo'])}",
        f"Maximo: {fmt_num(estadisticas_post['maximo'])}",
        f"Media: {fmt_num(estadisticas_post['media'])}",
        f"Mediana: {fmt_num(estadisticas_post['mediana'])}",
        "",
        "ESTADISTICAS dNBR",
        "-" * 18,
        f"Minimo: {fmt_num(estadisticas_dnbr['minimo'])}",
        f"Maximo: {fmt_num(estadisticas_dnbr['maximo'])}",
        f"Media: {fmt_num(estadisticas_dnbr['media'])}",
        f"Mediana: {fmt_num(estadisticas_dnbr['mediana'])}",
        f"Percentil 10: {fmt_num(estadisticas_dnbr['percentil_10'])}",
        f"Percentil 25: {fmt_num(estadisticas_dnbr['percentil_25'])}",
        f"Percentil 75: {fmt_num(estadisticas_dnbr['percentil_75'])}",
        f"Percentil 90: {fmt_num(estadisticas_dnbr['percentil_90'])}",
        "",
        "CLASIFICACION DE SEVERIDAD",
        "-" * 28,
    ]

    for clase in resumen_clases:
        lineas.append(
            f"Clase {clase['valor']} - {clase['nombre']}: "
            f"{clase['pixeles']} pixeles ({ft_formatear_porcentaje(clase['porcentaje'])})"
        )

    lineas.extend(
        [
            "",
            "INTERPRETACION",
            "-" * 14,
            "Valores dNBR mas altos indican mayor perdida relativa de vegetacion y mayor severidad potencial.",
            "La clase 1 representa ausencia de cambio fuerte o zonas no quemadas.",
            "La clase 4 representa las zonas con mayor severidad potencial del incendio.",
        ]
    )

    texto = "\n".join(lineas)
    print("\n" + texto)

    with open(ruta_salida, "w", encoding="utf-8") as archivo:
        archivo.write(texto)
        archivo.write("\n")

    print(f"\n[OK] Resumen P2 exportado: {ruta_salida}")


def ft_generar_panel_visual_p2(
    nbr_pre,
    nbr_post,
    dnbr,
    severidad,
    estadisticas_dnbr,
    limites_bbox,
    ruta_salida="p2_panel_visual.png",
):
    colores = [clase["color"] for clase in CLASES_SEVERIDAD]
    nombres = [f"{clase['valor']} - {clase['nombre']}" for clase in CLASES_SEVERIDAD]
    cmap_clases = mcolors.ListedColormap(colores)
    norm_clases = mcolors.BoundaryNorm([0.5, 1.5, 2.5, 3.5, 4.5], cmap_clases.N)

    fig, ejes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    fig.suptitle("Practica P2 - dNBR y severidad post-incendio", fontsize=16, fontweight="bold")

    img_pre = ejes[0, 0].imshow(nbr_pre, cmap="BrBG", vmin=-1, vmax=1)
    ejes[0, 0].set_title("NBR pre-incendio")
    ejes[0, 0].axis("off")
    fig.colorbar(img_pre, ax=ejes[0, 0], fraction=0.046, pad=0.04)

    img_post = ejes[0, 1].imshow(nbr_post, cmap="BrBG", vmin=-1, vmax=1)
    ejes[0, 1].set_title("NBR post-incendio")
    ejes[0, 1].axis("off")
    fig.colorbar(img_post, ax=ejes[0, 1], fraction=0.046, pad=0.04)

    img_dnbr = ejes[1, 0].imshow(dnbr, cmap="YlOrRd", vmin=-0.2, vmax=1)
    ejes[1, 0].set_title("dNBR = NBR pre - NBR post")
    ejes[1, 0].axis("off")
    fig.colorbar(img_dnbr, ax=ejes[1, 0], fraction=0.046, pad=0.04)

    img_sev = ejes[1, 1].imshow(severidad, cmap=cmap_clases, norm=norm_clases)
    ejes[1, 1].set_title("Clasificacion de severidad")
    ejes[1, 1].axis("off")
    cbar = fig.colorbar(img_sev, ax=ejes[1, 1], ticks=[1, 2, 3, 4], fraction=0.046, pad=0.04)
    cbar.ax.set_yticklabels(nombres)

    fig.text(
        0.5,
        0.01,
        (
            f"dNBR min={estadisticas_dnbr['minimo']:.3f} | "
            f"media={estadisticas_dnbr['media']:.3f} | "
            f"max={estadisticas_dnbr['maximo']:.3f}"
        ),
        ha="center",
        fontsize=11,
    )

    fig.savefig(ruta_salida, dpi=180)
    plt.close(fig)
    print(f"[OK] Panel visual P2 exportado: {ruta_salida}")


def ft_generar_mapa_interactivo_p2(nbr_pre, nbr_post, dnbr, severidad, limites_bbox, ruta_salida="p2_mapa_interactivo.html"):
    """
    Genera un mapa HTML interactivo con multiples capas (NBR pre/post, dNBR, severidad) y leyendas.
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
    
    # Funcion auxiliar para convertir matriz a imagen para folium
    def numpy_a_url(matriz, cmap_nombre, vmin, vmax, alpha=0.7):
        fig, ax = plt.subplots(figsize=(matriz.shape[1]/100, matriz.shape[0]/100), dpi=100)
        fig.patch.set_alpha(0)
        ax.axis('off')
        
        cmap = plt.get_cmap(cmap_nombre)
        norm = plt.Normalize(vmin=vmin, vmax=vmax)
        rgba = cmap(norm(matriz))
        rgba[..., 3] = alpha
        
        ax.imshow(rgba)
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
        plt.close(fig)
        buf.seek(0)
        return f"data:image/png;base64,{base64.b64encode(buf.read()).decode('utf-8')}"

    bounds = [[sur, oeste], [norte, este]]

    # Capa NBR PRE
    folium.raster_layers.ImageOverlay(
        image=numpy_a_url(nbr_pre, "BrBG", -1, 1),
        bounds=bounds,
        name="NBR PRE-incendio",
        show=False,
    ).add_to(m)

    # Capa NBR POST
    folium.raster_layers.ImageOverlay(
        image=numpy_a_url(nbr_post, "BrBG", -1, 1),
        bounds=bounds,
        name="NBR POST-incendio",
        show=False,
    ).add_to(m)

    # Capa dNBR
    folium.raster_layers.ImageOverlay(
        image=numpy_a_url(dnbr, "YlOrRd", -0.2, 1),
        bounds=bounds,
        name="dNBR (Diferencia)",
        show=False,
    ).add_to(m)

    # Capa Severidad (usamos el colormap personalizado)
    colores = [clase["color"] for clase in CLASES_SEVERIDAD]
    cmap_clases = mcolors.ListedColormap(colores)
    norm_clases = mcolors.BoundaryNorm([0.5, 1.5, 2.5, 3.5, 4.5], cmap_clases.N)
    
    rgba_sev = cmap_clases(norm_clases(severidad))
    rgba_sev[severidad == 1, 3] = 0.2  # Clase 1 mas transparente
    rgba_sev[severidad != 1, 3] = 0.8
    
    fig_sev, ax_sev = plt.subplots(figsize=(severidad.shape[1]/100, severidad.shape[0]/100), dpi=100)
    fig_sev.patch.set_alpha(0)
    ax_sev.axis('off')
    ax_sev.imshow(rgba_sev)
    buf_sev = BytesIO()
    fig_sev.savefig(buf_sev, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close(fig_sev)
    buf_sev.seek(0)
    url_sev = f"data:image/png;base64,{base64.b64encode(buf_sev.read()).decode('utf-8')}"

    folium.raster_layers.ImageOverlay(
        image=url_sev,
        bounds=bounds,
        name="Clasificacion de Severidad",
        show=True, # Por defecto mostramos la severidad
    ).add_to(m)
    
    folium.Rectangle(
        bounds=bounds,
        color="#ff0000",
        fill=False,
        weight=2,
        name="Area de estudio"
    ).add_to(m)
    
    # Agregar Leyendas mediante HTML y script para hacerlas dinamicas
    leyenda_html = """
    <div id="leyenda_sev" style="position: fixed; bottom: 50px; right: 50px; width: 280px; height: auto; 
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px; border-radius: 5px; display: block;">
         <b>Severidad del Incendio</b><br>
         <i style="background:#2ca25f; width: 18px; height: 18px; float: left; margin-right: 8px;"></i> Sin cambio / no quemado<br>
         <i style="background:#ffeda0; width: 18px; height: 18px; float: left; margin-right: 8px;"></i> Severidad baja<br>
         <i style="background:#feb24c; width: 18px; height: 18px; float: left; margin-right: 8px;"></i> Severidad moderada<br>
         <i style="background:#de2d26; width: 18px; height: 18px; float: left; margin-right: 8px;"></i> Severidad alta<br>
    </div>

    <div id="leyenda_nbr" style="position: fixed; bottom: 50px; right: 50px; width: 280px; height: auto; 
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px; border-radius: 5px; display: none;">
         <b>NBR (Normalized Burn Ratio)</b><br>
         <div style="background: linear-gradient(to right, #543005, #bf812d, #f5f5f5, #35978f, #003c30); 
                     width: 100%; height: 20px; margin-top: 5px; margin-bottom: 5px;"></div>
         <span style="float:left;">-1.0</span>
         <span style="float:right;">1.0</span>
         <div style="clear:both;"></div>
    </div>

    <div id="leyenda_dnbr" style="position: fixed; bottom: 50px; right: 50px; width: 280px; height: auto; 
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px; border-radius: 5px; display: none;">
         <b>dNBR (Diferencia NBR)</b><br>
         <div style="background: linear-gradient(to right, #ffffb2, #fecc5c, #fd8d3c, #f03b20, #bd0026); 
                     width: 100%; height: 20px; margin-top: 5px; margin-bottom: 5px;"></div>
         <span style="float:left;">-0.2</span>
         <span style="float:right;">1.0</span>
         <div style="clear:both;"></div>
    </div>

    <script>
        // Leaflet no esta garantizado que este cargado en el scope raiz de inmediato,
        // esperamos al evento onload o usamos un intervalo corto
        setTimeout(function() {
            var map_keys = Object.keys(window).filter(k => k.startsWith('map_'));
            if(map_keys.length > 0) {
                var myMap = window[map_keys[0]];
                
                myMap.on('overlayadd', function(eventLayer) {
                    if (eventLayer.name === 'Clasificacion de Severidad') {
                        document.getElementById('leyenda_sev').style.display = 'block';
                    } else if (eventLayer.name === 'NBR PRE-incendio' || eventLayer.name === 'NBR POST-incendio') {
                        document.getElementById('leyenda_nbr').style.display = 'block';
                    } else if (eventLayer.name === 'dNBR (Diferencia)') {
                        document.getElementById('leyenda_dnbr').style.display = 'block';
                    }
                });
                
                myMap.on('overlayremove', function(eventLayer) {
                    if (eventLayer.name === 'Clasificacion de Severidad') {
                        document.getElementById('leyenda_sev').style.display = 'none';
                    } else if (eventLayer.name === 'NBR PRE-incendio' || eventLayer.name === 'NBR POST-incendio') {
                        // Ocultar solo si la otra capa tampoco esta visible
                        // Como es dificil de saber sin iterar, para la Demo simplemente lo ocultamos
                        document.getElementById('leyenda_nbr').style.display = 'none';
                    } else if (eventLayer.name === 'dNBR (Diferencia)') {
                        document.getElementById('leyenda_dnbr').style.display = 'none';
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


def ft_ejecutar_practica_p2_api(
    configuracion_api,
    limites_bbox,
    rango_pre,
    rango_post,
    tamano_salida,
):
    import os
    
    # Crear carpeta de prueba
    base_dir = "prueba_ejer2"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        
    num = 1
    while os.path.exists(os.path.join(base_dir, f"prueba{num}")):
        num += 1
        
    out_dir = os.path.join(base_dir, f"prueba{num}")
    os.makedirs(out_dir)

    ruta_pre = os.path.join(out_dir, "p2_nbr_pre.tif")
    ruta_post = os.path.join(out_dir, "p2_nbr_post.tif")
    ruta_dnbr = os.path.join(out_dir, "p2_dnbr.tif")
    ruta_sev = os.path.join(out_dir, "p2_severidad_incendio.tif")
    ruta_resumen = os.path.join(out_dir, "p2_resumen_resultados.txt")
    ruta_salida_panel = os.path.join(out_dir, "p2_panel_visual.png")
    ruta_mapa_interactivo = os.path.join(out_dir, "p2_mapa_interactivo.html")

    """
    Ejecuta la deteccion de cambios post-incendio descargando PRE y POST por API.
    """
    print("[INFO] Descargando bandas PRE-incendio B08 y B12...")
    pre_nir, pre_swir2 = ft_descargar_bandas_nbr(
        configuracion_api,
        limites_bbox,
        rango_pre,
        tamano_salida,
    )

    print("[INFO] Descargando bandas POST-incendio B08 y B12...")
    post_nir, post_swir2 = ft_descargar_bandas_nbr(
        configuracion_api,
        limites_bbox,
        rango_post,
        tamano_salida,
    )

    nbr_pre = ft_calcular_indice_normalizado(pre_nir, pre_swir2)
    nbr_post = ft_calcular_indice_normalizado(post_nir, post_swir2)
    dnbr = nbr_pre - nbr_post
    severidad = ft_clasificar_severidad_dnbr(dnbr)

    estadisticas_pre = ft_calcular_estadisticas_genericas(nbr_pre)
    estadisticas_post = ft_calcular_estadisticas_genericas(nbr_post)
    estadisticas_dnbr = ft_calcular_estadisticas_genericas(dnbr)
    resumen_clases = ft_resumir_clases_severidad(severidad)

    perfil_base = ft_crear_perfil_desde_bbox(nbr_pre, limites_bbox)
    ft_exportar_geotiff_monobanda(ruta_pre, nbr_pre, perfil_base)
    ft_exportar_geotiff_monobanda(ruta_post, nbr_post, perfil_base)
    ft_exportar_geotiff_monobanda(ruta_dnbr, dnbr, perfil_base)
    ft_exportar_geotiff_monobanda(
        ruta_sev,
        severidad,
        perfil_base,
        dtype="uint8",
    )

    ft_generar_resumen_p2(
        estadisticas_pre,
        estadisticas_post,
        estadisticas_dnbr,
        resumen_clases,
        limites_bbox,
        rango_pre,
        rango_post,
        tamano_salida,
        ruta_salida=ruta_resumen
    )
    ft_generar_panel_visual_p2(
        nbr_pre,
        nbr_post,
        dnbr,
        severidad,
        estadisticas_dnbr,
        limites_bbox,
        ruta_salida=ruta_salida_panel
    )
    ft_generar_mapa_interactivo_p2(nbr_pre, nbr_post, dnbr, severidad, limites_bbox, ruta_salida=ruta_mapa_interactivo)


def ft_main_p2():
    try:
        sesion_api = ft_inicializar_api()
        limites_bbox, rango_pre, rango_post, tamano_salida = ft_pedir_parametros_usuario_p2_api()
        ft_ejecutar_practica_p2_api(
            sesion_api,
            limites_bbox,
            rango_pre,
            rango_post,
            tamano_salida,
        )
    except Exception as error_programa:
        print(f"\n[ERROR CRITICO] {error_programa}")


if __name__ == "__main__":
    ft_main_p2()

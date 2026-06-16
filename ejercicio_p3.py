import numpy as np
import laspy
from scipy.interpolate import griddata
import rasterio
from rasterio.transform import from_origin
import matplotlib.pyplot as plt
import os
import sys
import folium
from pyproj import Transformer
import matplotlib.cm as cm
from matplotlib.colors import Normalize
from PIL import Image
import webbrowser
import base64

def procesar_lidar(ruta_archivo, resolucion=1.0, epsg="25830"):
    """
    Procesa un archivo LiDAR (.las o .laz) para generar MDT, MDS y CHM,
    e incluye un mapa web interactivo usando el EPSG proporcionado.
    """
    print(f"Cargando archivo: {ruta_archivo}")
    las = laspy.read(ruta_archivo)
    
    print(f"Total de puntos: {len(las.points)}")
    
    # 1. Filtrar Suelo (Clase 2) y Vegetación (Clases 3, 4, 5)
    clases_vegetacion = [3, 4, 5]
    
    puntos_suelo = las.points[las.classification == 2]
    puntos_veg = las.points[np.isin(las.classification, clases_vegetacion)]
    
    print(f"Puntos de suelo (Clase 2): {len(puntos_suelo)}")
    print(f"Puntos de vegetación (Clases 3, 4, 5): {len(puntos_veg)}")
    
    if len(puntos_suelo) == 0:
        print("Advertencia: No se encontraron puntos clasificados como suelo. Usando todos los puntos como aproximación para que el script no falle.")
        puntos_suelo = las.points
        
    # 2. Definir los límites de la cuadrícula
    min_x, max_x = np.min(las.x), np.max(las.x)
    min_y, max_y = np.min(las.y), np.max(las.y)
    
    ancho = max_x - min_x
    alto = max_y - min_y
    
    # Auto-ajuste de resolución para evitar bloqueos
    limite_pixels = 2000 * 2000  # Máximo de 4 millones de píxeles
    while (ancho / resolucion) * (alto / resolucion) > limite_pixels:
        resolucion *= 2
        print(f"Advertencia: El área es muy extensa para la resolución actual.")
        print(f"Ajustando resolución automáticamente a {resolucion}m para evitar sobrecarga de memoria.")

    cols = int(np.ceil(ancho / resolucion))
    rows = int(np.ceil(alto / resolucion))
    print(f"Dimensiones de la cuadrícula: {cols} columnas x {rows} filas (Resolución: {resolucion}m)")
    
    # Coordenadas de los centros de los píxeles (Y de arriba a abajo)
    x_coords = np.linspace(min_x + resolucion/2, max_x - resolucion/2, cols)
    y_coords = np.linspace(max_y - resolucion/2, min_y + resolucion/2, rows)
    grid_x, grid_y = np.meshgrid(x_coords, y_coords)
    
    # 3. Generar MDT (Modelo Digital de Terreno) - Interpolación
    print("Generando MDT (Modelo Digital de Terreno)...")
    dtm = griddata((puntos_suelo.x, puntos_suelo.y), puntos_suelo.z, (grid_x, grid_y), method='linear')
    dtm_nearest = griddata((puntos_suelo.x, puntos_suelo.y), puntos_suelo.z, (grid_x, grid_y), method='nearest')
    dtm = np.where(np.isnan(dtm), dtm_nearest, dtm)
    
    # 4. Generar MDS (Modelo Digital de Superficie)
    print("Generando MDS (Modelo Digital de Superficie)...")
    dsm = griddata((las.x, las.y), las.z, (grid_x, grid_y), method='linear')
    dsm_nearest = griddata((las.x, las.y), las.z, (grid_x, grid_y), method='nearest')
    dsm = np.where(np.isnan(dsm), dsm_nearest, dsm)
    
    # Asegurar lógicamente que el MDS siempre es mayor o igual al MDT
    dsm = np.maximum(dsm, dtm)
    
    # 5. Calcular CHM (Canopy Height Model)
    print("Calculando CHM (Altura de la vegetación)...")
    chm = dsm - dtm
    chm[chm < 0] = 0  # Evitar valores negativos por artefactos de interpolación
    
    # 6. Guardar los resultados en TIF
    transform = from_origin(min_x, max_y, resolucion, resolucion)
    carpeta_salida = 'prueba_ejer3'
    os.makedirs(carpeta_salida, exist_ok=True)
    
    crs_salida = f'EPSG:{epsg}'

    def guardar_tif(ruta, matriz):
        with rasterio.open(
            ruta, 'w', driver='GTiff',
            height=matriz.shape[0], width=matriz.shape[1],
            count=1, dtype=str(matriz.dtype),
            crs=crs_salida,
            transform=transform
        ) as dst:
            dst.write(matriz, 1)
            
    guardar_tif(f'{carpeta_salida}/p3_mdt.tif', dtm)
    guardar_tif(f'{carpeta_salida}/p3_mds.tif', dsm)
    guardar_tif(f'{carpeta_salida}/p3_chm.tif', chm)
    print(f"Archivos TIF generados en la carpeta '{carpeta_salida}'.")
    
    # 7. Visualización rápida estática
    print("Generando panel estático...")
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    im1 = axes[0].imshow(dtm, cmap='terrain', extent=(min_x, max_x, min_y, max_y))
    axes[0].set_title('MDT (Terreno)')
    plt.colorbar(im1, ax=axes[0], fraction=0.046, pad=0.04, label='Elevación (m)')
    
    im2 = axes[1].imshow(dsm, cmap='terrain', extent=(min_x, max_x, min_y, max_y))
    axes[1].set_title('MDS (Superficie)')
    plt.colorbar(im2, ax=axes[1], fraction=0.046, pad=0.04, label='Elevación (m)')
    
    im3 = axes[2].imshow(chm, cmap='Greens', extent=(min_x, max_x, min_y, max_y))
    axes[2].set_title('CHM (Vegetación / Estructuras)')
    plt.colorbar(im3, ax=axes[2], fraction=0.046, pad=0.04, label='Altura (m)')
    
    plt.tight_layout()
    ruta_img = f'{carpeta_salida}/p3_panel_lidar.png'
    plt.savefig(ruta_img, dpi=150)
    plt.close()
    
    # 8. Generar Mapa Interactivo HTML con Folium
    print("\nGenerando mapa interactivo HTML con Folium...")
    try:
        # Convertir coordenadas del EPSG dado a Latitud/Longitud (EPSG:4326)
        transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        
        # Ojo: folium espera (lat, lon)
        lon_min, lat_min = transformer.transform(min_x, min_y)
        lon_max, lat_max = transformer.transform(max_x, max_y)
        
        bounds = [[lat_min, lon_min], [lat_max, lon_max]]
        centro_mapa = [(lat_min + lat_max) / 2, (lon_min + lon_max) / 2]
        
        # Crear mapa
        mapa = folium.Map(location=centro_mapa, zoom_start=16, control_scale=True)
        
        # Añadir satélite
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satélite (Esri)',
            overlay=False,
            control=True
        ).add_to(mapa)
        
        # Función para convertir matriz a PNG base64 con colores
        def matriz_a_png_b64(matriz, cmap_name):
            min_val = np.nanmin(matriz)
            max_val = np.nanmax(matriz)
            if min_val == max_val: max_val += 0.1
            norm = Normalize(vmin=min_val, vmax=max_val)
            m = cm.ScalarMappable(norm=norm, cmap=cmap_name)
            
            # Convertir a RGBA y hacer transparente donde no hay datos
            rgba = m.to_rgba(matriz, bytes=True)
            rgba[np.isnan(matriz), 3] = 0
            
            # Guardar a archivo temporal
            temp_path = "temp_overlay.png"
            Image.fromarray(rgba).save(temp_path)
            
            # Leer como base64
            with open(temp_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            
            os.remove(temp_path)
            return f"data:image/png;base64,{encoded}"

        # Añadir MDT
        folium.raster_layers.ImageOverlay(
            image=matriz_a_png_b64(dtm, 'terrain'),
            bounds=bounds,
            opacity=0.7,
            name='MDT (Terreno)',
            show=True
        ).add_to(mapa)
        
        # Añadir CHM
        folium.raster_layers.ImageOverlay(
            image=matriz_a_png_b64(chm, 'Greens'),
            bounds=bounds,
            opacity=0.8,
            name='CHM (Altura Vegetación)',
            show=False
        ).add_to(mapa)
        
        # --- AÑADIR LEYENDAS DINÁMICAS ---
        min_mdt, max_mdt = np.nanmin(dtm), np.nanmax(dtm)
        min_chm, max_chm = np.nanmin(chm), np.nanmax(chm)
        
        # Colores aproximados a terrain: azul, verde, amarillo, marron, blanco
        # Colores aproximados a Greens: blanco a verde oscuro
        
        leyenda_html = f"""
        <div id="leyenda_mdt" style="position: fixed; bottom: 50px; right: 50px; width: 280px; height: auto; 
             background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
             padding: 10px; border-radius: 5px; display: block;">
             <b>Elevación del Terreno (MDT)</b><br>
             <div style="background: linear-gradient(to right, #3366cc, #009933, #ffff99, #cc9900, #993300, #ffffff); 
                         width: 100%; height: 20px; margin-top: 5px; margin-bottom: 5px;"></div>
             <span style="float:left;">{min_mdt:.1f} m</span>
             <span style="float:right;">{max_mdt:.1f} m</span>
             <div style="clear:both;"></div>
             <span style="font-size:11px;">Altitud absoluta (Nivel del mar)</span>
        </div>

        <div id="leyenda_chm" style="position: fixed; bottom: 50px; right: 50px; width: 280px; height: auto; 
             background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
             padding: 10px; border-radius: 5px; display: none;">
             <b>Altura de Vegetación (CHM)</b><br>
             <div style="background: linear-gradient(to right, #f7fcf5, #c7e9c0, #74c476, #238b45, #00441b); 
                         width: 100%; height: 20px; margin-top: 5px; margin-bottom: 5px;"></div>
             <span style="float:left;">{min_chm:.1f} m</span>
             <span style="float:right;">{max_chm:.1f} m</span>
             <div style="clear:both;"></div>
             <span style="font-size:11px;">Altura neta sobre el suelo</span>
        </div>

        <script>
            setTimeout(function() {{
                var map_keys = Object.keys(window).filter(k => k.startsWith('map_'));
                if(map_keys.length > 0) {{
                    var myMap = window[map_keys[0]];
                    
                    myMap.on('overlayadd', function(eventLayer) {{
                        if (eventLayer.name === 'MDT (Terreno)') {{
                            document.getElementById('leyenda_mdt').style.display = 'block';
                        }} else if (eventLayer.name === 'CHM (Altura Vegetación)') {{
                            document.getElementById('leyenda_chm').style.display = 'block';
                        }}
                    }});
                    
                    myMap.on('overlayremove', function(eventLayer) {{
                        if (eventLayer.name === 'MDT (Terreno)') {{
                            document.getElementById('leyenda_mdt').style.display = 'none';
                        }} else if (eventLayer.name === 'CHM (Altura Vegetación)') {{
                            document.getElementById('leyenda_chm').style.display = 'none';
                        }}
                    }});
                }}
            }}, 1000);
        </script>
        """
        mapa.get_root().html.add_child(folium.Element(leyenda_html))
        
        folium.LayerControl().add_to(mapa)
        
        ruta_html = f'{carpeta_salida}/p3_mapa_interactivo.html'
        mapa.save(ruta_html)
        
        ruta_absoluta = os.path.abspath(ruta_html)
        print(f"¡Mapa interactivo guardado con éxito!")
        print(f"Abriendo: {ruta_absoluta}")
        webbrowser.open('file://' + ruta_absoluta)
        
    except Exception as e:
        print(f"\n[AVISO] No se pudo generar el mapa interactivo. ¿El código EPSG ({epsg}) es válido para tus coordenadas?")
        print(f"Error técnico: {e}")

if __name__ == "__main__":
    ruta_defecto = "muestra_lidar.las"
    epsg_defecto = "25830"
    
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        ruta = ruta_defecto
        
    if not os.path.exists(ruta):
        print(f"Error: No se encuentra el archivo '{ruta}'.")
    else:
        epsg = input(f"Introduce el código EPSG de tu archivo (ej. 25830 para España) [{epsg_defecto}]: ").strip() or epsg_defecto
        procesar_lidar(ruta, epsg=epsg)

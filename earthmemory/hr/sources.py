"""Catálogo de fuentes externas: cita, DOI/URL, licencia, versión, resolución nativa y QUÉ AÑADE cada capa.

Verificado el 2026-11-14 (atributos de los archivos, páginas oficiales y CMR de NASA). Lo que dice cada
archivo descargado (versión, fecha de creación) se copia además en MANIFEST.json.
"""

from __future__ import annotations

SOURCES = {
    "CHIRPS_M": {
        "nombre": "CHIRPS v2.0 mensual (subconjunto Centroamérica-Caribe, camer-carib)",
        "cita": "Funk, C., Peterson, P., Landsfeld, M., Pedreros, D., Verdin, J., Shukla, S., Husak, G., Rowland, J., "
                "Harrison, L., Hoell, A., Michaelsen, J. (2015). The climate hazards infrared precipitation with "
                "stations — a new environmental record for monitoring extremes. Scientific Data 2, 150066.",
        "doi": "10.1038/sdata.2015.66",
        "url": "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/camer-carib_monthly/tifs/",
        "licencia": "Dominio público (CC0: 'Pete Peterson has waived all copyright…', chc.ucsb.edu/data/chirps)",
        "version": "2.0 (producto final)",
        "resolucion": "0.05° (~5.3 km en RD), mensual",
        "nasa": False,
        "que_es": "Infrarrojo térmico de satélites geoestacionarios (duración de nubes frías) calibrado con la "
                  "climatología CHPclim y mezclado con estaciones (GTS/GHCN y redes nacionales que comparten datos).",
        "aporta": "Lluvia a 0.05°: 4 celdas por cada celda IMERG (0.1°) y 25 por cada GLDAS (0.25°). Comprobación "
                  "independiente de IMERG (NASA), no sustituto.",
    },
    "CHIRPS_D": {
        "nombre": "CHIRPS v2.0 diario (hemisferio occidental, whem p05)",
        "cita": "Funk et al. (2015), Scientific Data 2, 150066.",
        "doi": "10.1038/sdata.2015.66",
        "url": "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/whem_daily/tifs/p05/2023/",
        "licencia": "Dominio público (CC0)",
        "version": "2.0 (producto final)",
        "resolucion": "0.05°, diario (etiqueta de día UTC; README-CHIRPS2-Daily)",
        "nasa": False,
        "que_es": "NO es un producto diario independiente: el total de la PÉNTADA (mezcla satélite + estaciones) "
                  "se reparte entre sus 5 días con las proporciones diarias del pronóstico CFSv2 (README-CHIRPS2-Daily). "
                  "Solo el total de 5 días está anclado a estaciones; el valor de un día es una redistribución.",
        "aporta": "Mirada a 0.05° del evento del 18-nov-2023 en Santo Domingo frente al dato de estación.",
    },
    "TERRACLIMATE": {
        "nombre": "TerraClimate v1.1 (THREDDS de Northwest Knowledge Network, subconjunto NCSS)",
        "cita": "Abatzoglou, J.T., Dobrowski, S.Z., Parks, S.A., Hegewisch, K.C. (2018). TerraClimate, a "
                "high-resolution global dataset of monthly climate and climatic water balance from 1958–2015. "
                "Scientific Data 5, 170191. Versión servida: Abatzoglou, J.T., Hegewisch, K.C., Yin, C., "
                "Kalashinkov, D.A. (2026). TerraClimate v1.1 (referencia del propio archivo).",
        "doi": "10.1038/sdata.2017.191",
        "url": "http://thredds.northwestknowledge.net:8080/thredds/catalog/TERRACLIMATE_ALL/data/catalog.html",
        "licencia": "CC0 1.0 (atributo 'license' del archivo)",
        "version": "V1.1 (atributo 'version'; date_created 2026-06-02)",
        "resolucion": "1/24° (~4.6 km en RD), mensual; PERO las anomalías mes a mes vienen de ERA5 (~0.25°) y la "
                      "capacidad de agua del suelo del modelo de balance es de 0.5° (Wang-Erlandsson et al. 2016)",
        "nasa": False,
        "que_es": "Interpolación climáticamente asistida: climatología de alta resolución (WorldClim v2.1 según el "
                  "atributo 'source') + anomalías mensuales de ERA5, y un balance hídrico Thornthwaite-Mather "
                  "modificado (humedad del suelo, ET real, déficit hídrico, PDSI). OJO: la v1.0 usaba CRU TS4/JRA-55; "
                  "la v1.1 que sirve hoy el THREDDS usa ERA5.",
        "aporta": "Respuesta del suelo (balance hídrico) a ~4 km, independiente de NASA. Es un MODELO, no una "
                  "medición: su detalle fino viene de la climatología, no de la variabilidad mensual.",
    },
    "SOILGRIDS": {
        "nombre": "SoilGrids 2.0 (ISRIC), arcilla y arena 0-5, 5-15, 15-30 cm (media), por WCS",
        "cita": "Poggio, L., de Sousa, L.M., Batjes, N.H., Heuvelink, G.B.M., Kempen, B., Ribeiro, E., Rossiter, D. "
                "(2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial "
                "uncertainty. SOIL 7, 217–240.",
        "doi": "10.5194/soil-7-217-2021",
        "url": "https://maps.isric.org/mapserv?map=/map/{prop}.map (WCS 2.0.1)",
        "licencia": "CC BY 4.0",
        "version": "SoilGrids 2.0 (2020)",
        "resolucion": "250 m nativo (Homolosine); pedido en EPSG:4326 a 0.0025° (el servidor reproyecta)",
        "nasa": False,
        "que_es": "Predicción por aprendizaje automático a partir de perfiles de suelo (WoSIS) y covariables; "
                  "incluye incertidumbre (no usada aquí).",
        "aporta": "Textura del suelo (factor explicativo estático) a ~250 m.",
    },
    "COPDEM": {
        "nombre": "Copernicus DEM GLO-90 (COG públicos en AWS)",
        "cita": "European Space Agency (2021). Copernicus DEM — Global and European Digital Elevation Model "
                "(COP-DEM), GLO-90. Teselas COG del registro AWS Open Data.",
        "doi": "10.5270/ESA-c5d3d65",
        "url": "https://copernicus-dem-90m.s3.amazonaws.com/",
        "licencia": "Licencia Copernicus DEM GLO-90: uso libre mundial con atribución '© DLR e.V. 2010-2014 and © "
                    "Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA'",
        "version": "GLO-90 (teselas COG 1°×1° del bucket público)",
        "resolucion": "3″ (~90 m)",
        "nasa": False,
        "que_es": "Modelo digital de superficie (TanDEM-X, radar interferométrico).",
        "aporta": "Elevación y pendiente (Horn, a 90 m) agregadas a 0.05°.",
    },
    "WORLDCOVER": {
        "nombre": "ESA WorldCover 10 m 2021 v200",
        "cita": "Zanaga, D., Van De Kerchove, R., Daems, D., De Keersmaecker, W., Brockmann, C., Kirches, G., "
                "Wevers, J., Cartus, O., Santoro, M., Fritz, S., Lesiv, M., Herold, M., Tsendbazar, N.E., Xu, P., "
                "Ramoino, F., Arino, O. (2022). ESA WorldCover 10 m 2021 v200.",
        "doi": "10.5281/zenodo.7254221",
        "url": "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/",
        "licencia": "CC BY 4.0",
        "version": "v200 (algorithm_version V2.0.0)",
        "resolucion": "10 m; aquí leído de la vista general 1/8 del COG (~80 m) y llevado a fracciones por celda 0.05°",
        "nasa": False,
        "que_es": "Clasificación de Sentinel-1 y Sentinel-2 (11 clases).",
        "aporta": "Fracción de bosque, cultivo, pasto, urbano, etc. por celda (factor explicativo estático).",
    },
    "GEOBOUNDARIES": {
        "nombre": "geoBoundaries gbOpen DOM ADM0 (simplificado, en appeears/) y ADM1",
        "cita": "Runfola, D. et al. (2020). geoBoundaries: A global database of political administrative "
                "boundaries. PLoS ONE 15(4): e0231866.",
        "doi": "10.1371/journal.pone.0231866",
        "url": "https://www.geoboundaries.org/api/current/gbOpen/DOM/",
        "licencia": "ADM0: CC BY 4.0 (fuente Caribbean GeoPortal); ADM1: dominio público (fuente Natural Earth)",
        "version": "DOM-ADM0-20870125 (2020); DOM-ADM1 según metadatos de la API",
        "resolucion": "vectorial",
        "nasa": False,
        "que_es": "Límites administrativos.",
        "aporta": "Máscara de tierra dominicana y bordes de provincia en los mapas.",
    },
    "SMAP_L4": {
        "nombre": "SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical Data V008 "
                  "(SPL4SMGP)",
        "cita": "Reichle, R., De Lannoy, G., Koster, R.D., Crow, W.T., Kimball, J.S., Liu, Q., Bechtold, M. SMAP L4 "
                "Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical Data, Version 8. "
                "NASA NSIDC DAAC.",
        "doi": "10.5067/T5RUATAQREF8",
        "url": "https://opendap.earthdata.nasa.gov/collections/C3480440870-NSIDC_CPRD/ (OPeNDAP en la nube, token)",
        "licencia": "Datos NASA EOSDIS: uso libre y sin restricciones con cita (NSIDC use & copyright)",
        "version": "V008",
        "resolucion": "9 km (EASE-Grid 2.0), cada 3 h; aquí 1 ventana de 3 h por día (12-15 UTC) promediada por mes",
        "nasa": True,
        "que_es": "Modelo Catchment del GEOS con asimilación de temperaturas de brillo de SMAP (banda L, 36 km).",
        "aporta": "Humedad superficial y de zona de raíces NASA a 9 km (2015-04 en adelante): la respuesta del suelo "
                  "con la observación de NASA más directa del agua del suelo.",
    },
    "IMERG_M": {
        "nombre": "GPM IMERG Final V07 mensual (descargado por el motor nacional, solo lectura aquí)",
        "cita": "Huffman, G.J., Stocker, E.F., Bolvin, D.T., Nelkin, E.J., Tan, J. (2023). GPM IMERG Final "
                "Precipitation L3 1 month 0.1 degree x 0.1 degree V07. GES DISC.",
        "doi": "10.5067/GPM/IMERG/3B-MONTH/07",
        "url": "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGM.07/",
        "licencia": "Datos NASA EOSDIS: uso libre con cita",
        "version": "V07",
        "resolucion": "0.1°, mensual",
        "nasa": True,
        "que_es": "Precipitación multisatélite (microondas pasivas + IR) calibrada con GPCC.",
        "aporta": "La lluvia NASA de referencia; se compara con CHIRPS celda a celda (sin pretender 0.05°).",
    },
}

# Clases de WorldCover v200
WORLDCOVER_CLASSES = {10: "bosque", 20: "matorral", 30: "pastizal", 40: "cultivo", 50: "urbano",
                      60: "suelo_desnudo", 70: "nieve", 80: "agua", 90: "humedal", 95: "manglar", 100: "musgo"}

TERRACLIMATE_VARS = {
    "soil": ("Humedad del suelo a fin de mes (balance hídrico)", "mm"),
    "PDSI": ("Índice de severidad de sequía de Palmer", "adimensional"),
    "aet": ("Evapotranspiración real", "mm/mes"),
    "def": ("Déficit hídrico climático (PET − AET)", "mm/mes"),
    "ppt": ("Precipitación TerraClimate", "mm/mes"),
    "pet": ("Evapotranspiración de referencia", "mm/mes"),
}

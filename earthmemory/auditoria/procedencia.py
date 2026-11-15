"""Matriz de procedencia e independencia de cada producto (verificada contra documentación oficial el 2026-11-14).

Cada afirmación lleva su URL. "V" = verificada en el documento citado; "I" = inferida (plausible, no escrita
así en la documentación); "NV" = no verificada. No se escribió nada de memoria sin marcarlo.
Regla del equipo: que dos o tres productos coincidan NO es una validación robusta si comparten insumos.
"""

from __future__ import annotations

U = {
    "imerg_td": "https://gpm.nasa.gov/sites/default/files/2023-07/IMERG_TechnicalDocumentation_final_230713.pdf",
    "imerg_rn": "https://gpm.nasa.gov/sites/default/files/2024-12/IMERG_V07_ReleaseNotes_241126.pdf",
    "chirps_d": "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/README-CHIRPS2-Daily.txt",
    "chirps_r": "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/README-CHIRPS.txt",
    "chirps_p": "https://doi.org/10.1038/sdata.2015.66",
    "chirps_st": "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/diagnostics/monthly_station_data/",
    "gldas": "https://hydro1.gesdisc.eosdis.nasa.gov/data/GLDAS/GLDAS_NOAH025_M.2.1/doc/README_GLDAS2.pdf",
    "gldas_p": "https://doi.org/10.1175/BAMS-85-3-381",
    "gpcp1dd": "https://www.ncei.noaa.gov/pub/data/sds/cdr/CDRs/Precipitation_GPCP-Daily/AlgorithmDescription_01B-35.pdf",
    "l4": "https://nsidc.org/sites/default/files/documents/user-guide/multi_spl4smau-v008-userguide.pdf",
    "l4v": "https://nsidc.org/data/spl4smgp/versions/8",
    "l3": "https://nsidc.org/sites/default/files/documents/user-guide/spl3smp_e-v006-userguide.pdf",
    "tc": "https://www.climatologylab.org/terraclimate.html",
    "tc_p": "https://doi.org/10.1038/sdata.2017.191",
    "m2p": "https://gmao.gsfc.nasa.gov/pubs/docs/Reichle734.pdf",
    "m2p17": "https://ntrs.nasa.gov/api/citations/20170011571/downloads/20170011571.pdf",
    "power": "https://power.larc.nasa.gov/api/system/manager/parameters/PRECTOTCORR?community=AG",
    "power_m": "https://power.larc.nasa.gov/docs/methodology/",
    "cpcu": "https://ftp.cpc.ncep.noaa.gov/precip/CPC_UNI_PRCP/GAUGE_GLB/DOCU/Chen_et_al_2008_JGR_Gauge_Algo.pdf",
    "grace": "https://grace.jpl.nasa.gov/data/get-data/jpl_global_mascons/",
    "mod13": "https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13a3-061",
    "mod17": "https://lpdaac.usgs.gov/documents/972/MOD17_User_Guide_V61.pdf",
    "geoglows": "https://geoglows.ecmwf.int/about",
    "gpcc": "https://opendata.dwd.de/climate_environment/GPCC/PDF/GPCC_intro_products_v2022.pdf",
    "ghcnd": "https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt",
    "gsod": "https://www.ncei.noaa.gov/data/global-summary-of-the-day/doc/readme.txt",
}

CLASES = ["observación in situ", "recuperación satelital", "recuperación satelital ajustada con pluviómetros",
          "modelo con asimilación", "modelo forzado", "simulación hidrológica"]

PRODUCTOS = [
    {"id": "IMERG", "producto": "GPM IMERG V07 Final (3IMERGHH/DF/M)", "clase": CLASES[2],
     "mide_o_modela": "Lluvia estimada por satélite (microondas pasivas + IR) con ajuste mensual a pluviómetros",
     "insumos": "PMW GPROF2021 (GMI, AMSR2, SSMIS, ATMS, MHS…) intercalibrados a CORRA (calibración climatológica a GPCP); "
                "IR CPC 4 km (GOES, Meteosat, Himawari) vía PDIR; vectores de morphing de MERRA-2 (Final); ERA5 en GPROF; "
                "pluviómetros GPCC Full Data V2022 (hasta 2020) y Monitoring (desde dic-2020), ajuste SOLO mensual "
                "(sesgo a gran escala, cociente limitado a [0.2, 3])",
     "pluviometros": "GPCC (GTS SYNOP/CLIMAT + servicios nacionales + GHCN en Full Data)",
     "resolucion": "0.1°, 30 min; diario = día UTC", "latencia": "~3.5 meses (Final)", "version": "V07B",
     "citas": "Huffman et al., IMERG V07 Technical Documentation (2023); Release Notes V07 (2024)",
     "urls": [U["imerg_td"], U["imerg_rn"]], "verificado": "V (ajuste mensual GPCC, insumos); diario = suma del día UTC: V (catálogo)"},
    {"id": "CHIRPS", "producto": "CHIRPS v2.0 (mensual, péntada, diario)", "clase": CLASES[2],
     "mide_o_modela": "Lluvia por duración de nubes frías IR calibrada con climatología CHPclim y mezclada con estaciones",
     "insumos": "IR geoestacionario (GriSat 1981-2008, CPC 2000-presente); CCD calibrada con TRMM 3B42 v7; huecos de CHIRP con CFSv2; "
                "estaciones GHCN mensual/diaria, GSOD, GTS, SASSCAL y servicios nacionales. DIARIO: el total de la péntada se "
                "reparte entre días con la lluvia diaria del CFSv2 (README-CHIRPS2-Daily): el día no es independiente",
     "pluviometros": "GTS + GSOD + GHCN (en RD: Puerto Plata, Santiago, Sabana de la Mar, Punta Cana, Barahona, Las Américas, Santo Domingo; lista oficial por mes)",
     "resolucion": "0.05°; péntada/mes (anclado a estaciones); diario redistribuido", "latencia": "final ~3.ª semana del mes siguiente",
     "version": "2.0 (final)", "citas": "Funk et al. 2015, Sci. Data 2:150066; README-CHIRPS2-Daily",
     "urls": [U["chirps_p"], U["chirps_r"], U["chirps_d"], U["chirps_st"]],
     "verificado": "V; CHIRPS v3 'sat' usa IMERG Late para el reparto diario (v3, no v2)"},
    {"id": "GLDAS_forzamiento", "producto": "GLDAS-2.1 Noah 0.25° (incl. Rainf_f_tavg)", "clase": CLASES[4],
     "mide_o_modela": "Modelo de superficie Noah-3.6 en bucle abierto; Rainf_f = lluvia de ENTRADA",
     "insumos": "Atmósfera GDAS (NOAA/NCEP); lluvia GPCP 1DD V1.3 desagregada; radiación AGRMET; SIN asimilación (open-loop; "
                "la asimilación de GRACE es de GLDAS-2.2). GPCP 1DD se escala a GPCP mensual V2.3, que mezcla GPCC con satélite",
     "pluviometros": "Indirecto: GPCC (vía GPCP mensual)", "resolucion": "0.25°, 3 h / mensual",
     "latencia": "3-4 meses (corriente principal con GPCP)", "version": "2.1",
     "citas": "Rodell et al. 2004 BAMS 85:381; README GLDAS-2 (GES DISC); GPCP 1DD ATBD",
     "urls": [U["gldas"], U["gldas_p"], U["gpcp1dd"]], "verificado": "V"},
    {"id": "SMAP_L4", "producto": "SMAP L4 SPL4SMGP V008", "clase": CLASES[3],
     "mide_o_modela": "Humedad superficial y de zona de raíces del modelo Catchment (GEOS) con asimilación de Tb SMAP",
     "insumos": "EnKF con Tb banda L de SMAP (36 km); lluvia GEOS FP corregida con CPC Unified (Norteamérica) e IMERG V07 Final "
                "(fuera de Norteamérica; climatología reescalada a IMERG V06B o GPCP v2.3); la nota de versión V8 indica que el "
                "procesamiento más reciente deja de usar las correcciones diarias de IMERG-Final",
     "pluviometros": "Indirecto: GPCC vía IMERG Final; CPCU en Norteamérica (si el Caribe entra: NV)",
     "resolucion": "9 km EASE-2, 3 h", "latencia": "NV", "version": "V008",
     "citas": "Reichle et al., SMAP L4_SM user guide V008; NSIDC versión 8",
     "urls": [U["l4"], U["l4v"]], "verificado": "V; NO es confirmación independiente de GLDAS ni de IMERG"},
    {"id": "SMAP_L3", "producto": "SMAP L3 SPL3SMP_E V6 (9 km mejorado)", "clase": CLASES[1],
     "mide_o_modela": "Humedad superficial (~0-5 cm) recuperada de Tb banda L (radiómetro)",
     "insumos": "Tb SMAP (Backus-Gilbert a 9 km); algoritmo DCA; temperatura efectiva de GMAO (GEOS); VWC de climatología NDVI MODIS; "
                "MOD44W; SoilGrids250m. No usa lluvia",
     "pluviometros": "ninguno", "resolucion": "9 km, diario (06 h y 18 h)", "latencia": "NV", "version": "V6",
     "citas": "O'Neill et al., SPL3SMP_E V6 user guide (NSIDC)", "urls": [U["l3"]],
     "verificado": "V; el testigo más observacional del suelo (solo superficie)"},
    {"id": "TerraClimate", "producto": "TerraClimate v1.1 (servido hoy)", "clase": CLASES[4],
     "mide_o_modela": "Interpolación climática + balance hídrico Thornthwaite-Mather modificado",
     "insumos": "v1.1: anomalías solo de ERA5 + normales CHELSA v2.1 (CRU TS solo para presión de vapor); v1.0: WorldClim + CRU TS4 + JRA-55",
     "pluviometros": "solo en la climatología de fondo (CHELSA/WorldClim) y en ERA5 indirectamente", "resolucion": "~4 km, mensual",
     "latencia": "anual", "version": "v1.1", "citas": "Abatzoglou et al. 2018, Sci. Data 5:170191; climatologylab.org",
     "urls": [U["tc_p"], U["tc"]], "verificado": "V (fuente de v1.1 según la página del laboratorio y metadatos del archivo)"},
    {"id": "MERRA2", "producto": "MERRA-2 PRECTOTCORR vía NASA POWER", "clase": CLASES[3],
     "mide_o_modela": "Reanálisis (GEOS) cuya lluvia en superficie se corrige con observaciones",
     "insumos": "Corrección con CPC Unified (CPCU, pluviómetros diarios 0.5°) en tierra de bajas latitudes (RD recibe la corrección "
                "completa); CMAP solo en África; transición 42.5-62.5°; POWER: 0.5° × 0.625°; tramo reciente de POWER desde GEOS FP-IT (NV su corrección)",
     "pluviometros": "CPCU (~30 000 estaciones: GTS, COOP, redes nacionales)", "resolucion": "0.5° × 0.625°, horario/diario",
     "latencia": "MERRA-2 ~semanas; POWER usa FP-IT para lo más reciente", "version": "MERRA-2 / POWER v2",
     "citas": "Gelaro et al. 2017 J. Climate; Reichle et al. 2017 J. Climate (doi:10.1175/JCLI-D-16-0570.1); Chen et al. 2008",
     "urls": [U["m2p"], U["m2p17"], U["power"], U["power_m"], U["cpcu"]], "verificado": "V"},
    {"id": "GRACE", "producto": "GRACE/GRACE-FO JPL mascons RL06.3 v04 CRI", "clase": CLASES[1],
     "mide_o_modela": "Almacenamiento total de agua por gravimetría",
     "insumos": "Gravedad variable en el tiempo; mascons de 3°; filtro CRI en costas (modelos de fondo GIA/AOD: NV aquí)",
     "pluviometros": "ninguno", "resolucion": "rejilla 0.5°, resolución efectiva ~3° (> área de RD)", "latencia": "NV",
     "version": "RL06.3 v04", "citas": "Watkins et al. 2015 JGR, doi:10.1002/2014JB011547", "urls": [U["grace"]],
     "verificado": "V; el más independiente en lluvia, pero inútil a escala de provincia"},
    {"id": "MOD13A3", "producto": "MODIS MOD13A3 v061 (NDVI/EVI mensual)", "clase": CLASES[1],
     "mide_o_modela": "Índices de vegetación de reflectancia MODIS Terra", "insumos": "MOD13A2 16 días ponderados",
     "pluviometros": "ninguno", "resolucion": "1 km, mensual", "latencia": "días", "version": "v061",
     "citas": "LP DAAC MOD13A3 v061", "urls": [U["mod13"]], "verificado": "V"},
    {"id": "MOD17", "producto": "MODIS MOD17A3HGF v061 (NPP anual)", "clase": CLASES[4],
     "mide_o_modela": "Modelo de eficiencia de uso de la luz", "insumos": "FPAR/LAI MOD15A2H + meteorología GMAO GEOS-5 (0.5° × 0.67°)",
     "pluviometros": "ninguno", "resolucion": "500 m, anual", "latencia": "fin de año", "version": "v061",
     "citas": "MOD17 User Guide V61 (Running & Zhao)", "urls": [U["mod17"]],
     "verificado": "V (500 m, no 1 km; meteorología GEOS-5, no 'MERRA-2' explícito)"},
    {"id": "GEOGLOWS", "producto": "GEOGLOWS v2 caudal", "clase": CLASES[5],
     "mide_o_modela": "Caudal SIMULADO", "insumos": "Escorrentía ERA5 enrutada con RAPID (TDX-Hydro); pronóstico HTESSEL; sin caudales observados",
     "pluviometros": "ninguno directo", "resolucion": "tramos de río, diario", "latencia": "diario (pronóstico)", "version": "v2",
     "citas": "geoglows.ecmwf.int/about", "urls": [U["geoglows"]], "verificado": "V"},
    {"id": "Estaciones", "producto": "Estaciones GHCN-Daily / GSOD de RD (SYNOP)", "clase": CLASES[0],
     "mide_o_modela": "Pluviómetro puntual; en RD los datos GHCN-D vienen de informes SYNOP (fuente 'S' = GSOD)",
     "insumos": "Informes sinópticos del GTS (pueden no ser el 'verdadero' día climatológico: readme GHCN-D)",
     "pluviometros": "es el pluviómetro", "resolucion": "punto, diario", "latencia": "días", "version": "GHCN-D v3",
     "citas": "Menne et al. 2012 JTECH 29:897; doi:10.7289/V5D21VHZ", "urls": [U["ghcnd"], U["gsod"]],
     "verificado": "V; las mismas estaciones están en la mezcla de CHIRPS (lista oficial) y probablemente en GPCC y CPCU (vía GTS)"},
]

# Familias de insumos que pueden compartir errores. V = verificado, I = inferido.
INSUMOS = {
    "Pluviómetros GTS/SYNOP": {"IMERG": "V", "CHIRPS": "V", "GLDAS_forzamiento": "V", "SMAP_L4": "V", "MERRA2": "V", "Estaciones": "V"},
    "GPCC": {"IMERG": "V", "GLDAS_forzamiento": "V", "SMAP_L4": "V", "CHIRPS": "I"},
    "GHCN/GSOD": {"CHIRPS": "V", "Estaciones": "V", "IMERG": "I", "TerraClimate": "I"},
    "CPC Unified": {"MERRA2": "V", "SMAP_L4": "I"},
    "IR geoestacionario": {"IMERG": "V", "CHIRPS": "V", "GLDAS_forzamiento": "V"},
    "Microondas pasivas": {"IMERG": "V", "GLDAS_forzamiento": "V", "CHIRPS": "I"},
    "Sistema GEOS / MERRA-2": {"MERRA2": "V", "IMERG": "V", "SMAP_L4": "V", "SMAP_L3": "V", "MOD17": "V"},
    "ERA5": {"IMERG": "V", "TerraClimate": "V", "GEOGLOWS": "V"},
    "NCEP (CFSv2 / GDAS)": {"CHIRPS": "V", "GLDAS_forzamiento": "V"},
    "Tb SMAP banda L": {"SMAP_L4": "V", "SMAP_L3": "V"},
    "Reflectancia MODIS": {"MOD13A3": "V", "MOD17": "V", "SMAP_L3": "V", "GLDAS_forzamiento": "V"},
    "Gravimetría GRACE": {"GRACE": "V"},
}

ARISTAS = [  # producto ↔ producto por insumo compartido (lo que permite errores comunes)
    ("IMERG", "GLDAS_forzamiento", "GPCC (vía GPCP mensual)", "V"),
    ("IMERG", "SMAP_L4", "IMERG Final corrige la lluvia de L4", "V"),
    ("IMERG", "CHIRPS", "IR CPC + calibración CCD con TMPA (predecesor ajustado a GPCC)", "V"),
    ("CHIRPS", "Estaciones", "mismas estaciones GTS/GSOD en la mezcla (lista oficial)", "V"),
    ("IMERG", "Estaciones", "GPCC usa SYNOP del GTS", "I"),
    ("MERRA2", "Estaciones", "CPCU usa SYNOP del GTS", "I"),
    ("IMERG", "MERRA2", "morphing con campos de MERRA-2", "V"),
    ("SMAP_L4", "SMAP_L3", "mismas Tb SMAP", "V"),
    ("SMAP_L4", "MERRA2", "sistema GEOS", "V"),
    ("CHIRPS", "GLDAS_forzamiento", "familia NCEP (CFSv2 / GDAS)", "I"),
    ("TerraClimate", "GEOGLOWS", "ERA5", "V"),
    ("IMERG", "TerraClimate", "ERA5", "V"),
    ("MOD13A3", "MOD17", "reflectancia MODIS", "I"),
]


def veredicto() -> list[str]:
    return [
        "Ningún par de productos de LLUVIA de esta lista es independiente: IMERG Final, la lluvia de GLDAS-2.1 (GPCP) y "
        "SMAP L4 cuelgan de GPCC; CHIRPS mezcla las mismas estaciones SYNOP/GSOD dominicanas; MERRA-2 corregido cuelga "
        "de CPC Unified, que también usa el GTS. Su acuerdo no es una confirmación independiente.",
        "SMAP L4 (zona de raíces) es un modelo con asimilación cuya lluvia se corrige con IMERG: no confirma a GLDAS "
        "ni a IMERG. SMAP L3 (0-5 cm) es el testigo más observacional del suelo, pero solo de la superficie.",
        "CHIRPS diario no es un dato diario independiente: reparte la péntada con el CFSv2. Para disparadores diarios "
        "solo la suma de 5 días está anclada a estaciones.",
        "GRACE-FO es el único independiente en lluvia, pero su resolución (~3°) es mayor que el país.",
        "Las estaciones GHCN-D/GSOD de RD sirven de verdad de terreno solo con la circularidad marcada: entran en CHIRPS "
        "(verificado mes a mes) y muy probablemente en GPCC/CPCU (vía GTS).",
    ]

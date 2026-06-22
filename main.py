from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import ee
import os
import json


service_account_info = os.getenv("GOOGLE_SERVICE_ACCOUNT")
project_id = os.getenv("GEE_PROJECT", "ee-bmarjanov1102")

if service_account_info:
    service_account_dict = json.loads(service_account_info)
    credentials = ee.ServiceAccountCredentials(
        service_account_dict["client_email"],
        key_data=service_account_info
    )
    ee.Initialize(credentials, project=project_id)
else:
    ee.Initialize(project=project_id)


app = FastAPI()

GRANICA = ee.FeatureCollection("projects/ee-bmarjanov1102/assets/tara_sume")


def get_sentinel_period(year: int, start_md: str, end_md: str):
    return (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(GRANICA)
        .filterDate(f"{year}-{start_md}", f"{year}-{end_md}")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .select(["B2", "B4", "B8", "B12"])
        .median()
        .clip(GRANICA)
        .divide(10000)
        .toFloat()
    )


def get_dynamic_world(year: int):
    return (
        ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
        .filterBounds(GRANICA)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .select("label")
        .mode()
        .clip(GRANICA)
    )


def get_forest_mask(year: int):
    return get_dynamic_world(year).eq(1).rename("Forest")
def get_sentinel_image(year: int):
    return (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(GRANICA)
        .filterDate(f"{year}-06-01", f"{year}-09-30")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .select(["B2", "B4", "B8", "B12"])
        .median()
        .clip(GRANICA)
        .divide(10000)
        .toFloat()
    )


def get_ndvi_image(year: int):
    image = get_sentinel_image(year)
    return image.normalizedDifference(["B8", "B4"]).rename("NDVI")


def get_evi_image(year: int):
    image = get_sentinel_image(year)
    return image.expression(
        "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
        {
            "NIR": image.select("B8"),
            "RED": image.select("B4"),
            "BLUE": image.select("B2")
        }
    ).rename("EVI")


def get_nbr_image(year: int):
    image = get_sentinel_image(year)
    return image.normalizedDifference(["B8", "B12"]).rename("NBR")


@app.get("/")
def home():
    return FileResponse("templates/index.html")


@app.get("/api/test")
def test():
    return {"message": "Backend radi i povezan je sa Earth Engine-om"}


@app.get("/api/ndvi/{year}")
def get_ndvi(year: int):
    start_date = f"{year}-06-01"
    end_date = f"{year}-09-30"

    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(GRANICA)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .select(["B4", "B8"])
        .median()
        .clip(GRANICA)
        .divide(10000)
        .toFloat()
    )

    ndvi = s2.normalizedDifference(["B8", "B4"]).rename("NDVI")

    map_id = ndvi.getMapId({
        "min": -1,
        "max": 1,
        "palette": ["red", "yellow", "white", "green"]
    })

    return {
        "year": year,
        "layer": "NDVI",
        "tile_url": map_id["tile_fetcher"].url_format
    }

@app.get("/api/srtm/{year}")
def get_srtm(year: int):
    srtm = ee.Image("USGS/SRTMGL1_003").clip(GRANICA)

    map_id = srtm.getMapId({
        "min": 238,
        "max": 1584,
        "palette": ["green", "yellow", "brown", "white"]
    })

    return {
        "year": year,
        "layer": "SRTM",
        "tile_url": map_id["tile_fetcher"].url_format
    }
@app.get("/api/chirps/{year}")
def get_chirps(year: int):
    chirps = (
        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        .filterBounds(GRANICA)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .select("precipitation")
        .sum()
        .clip(GRANICA)
    )

    map_id = chirps.getMapId({
        "min": 700,
        "max": 1500,
        "palette": ["#ffffcc", "#a1dab4", "#41b6c4", "#225ea8"]
    })

    return {
        "year": year,
        "layer": "CHIRPS",
        "tile_url": map_id["tile_fetcher"].url_format
    }
@app.get("/api/era5/{year}")
def get_era5(year: int):
    temp_k = (
        ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR")
        .filterBounds(GRANICA)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .select("temperature_2m")
        .mean()
        .clip(GRANICA)
    )

    temp_c = temp_k.subtract(273.15).rename("temperature_C")

    map_id = temp_c.getMapId({
        "min": 5,
        "max": 15,
        "palette": ["blue", "cyan", "yellow", "orange", "red"]
    })

    return {
        "year": year,
        "layer": "ERA5",
        "tile_url": map_id["tile_fetcher"].url_format
    }
@app.get("/api/gedi/{year}")
def get_gedi(year: int):
    if year < 2020:
        return {
            "year": year,
            "layer": "GEDI",
            "error": "GEDI podaci nisu dostupni za izabranu godinu. Izaberi godinu od 2020 do 2024."
        }

    gedi = (
        ee.ImageCollection("LARSE/GEDI/GEDI02_A_002_MONTHLY")
        .filterBounds(GRANICA)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .select("rh98")
        .median()
        .clip(GRANICA)
    )

    map_id = gedi.getMapId({
        "min": 0,
        "max": 40,
        "palette": ["#ffffcc", "#a1dab4", "#41ab5d", "#005a32"]
    })

    return {
        "year": year,
        "layer": "GEDI",
        "tile_url": map_id["tile_fetcher"].url_format
    }
@app.get("/api/boundary")
def get_boundary():
    geojson = GRANICA.geometry().getInfo()

    return geojson
@app.get("/api/stats/{layer}/{year}")
def get_stats(layer: str, year: int):

    if layer == "ndvi":
        image = get_ndvi_image(year)
        scale = 10
        unit = ""

    elif layer == "evi":
        image = get_evi_image(year)
        scale = 10
        unit = ""

    elif layer == "nbr":
        image = get_nbr_image(year)
        scale = 10
        unit = ""

    elif layer == "srtm":
        image = ee.Image("USGS/SRTMGL1_003").clip(GRANICA)
        scale = 30
        unit = "m"

    elif layer == "chirps":
        image = (
            ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filterBounds(GRANICA)
            .filterDate(f"{year}-01-01", f"{year}-12-31")
            .select("precipitation")
            .sum()
            .clip(GRANICA)
        )
        scale = 5000
        unit = "mm"

    elif layer == "era5":
        temp_k = (
            ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR")
            .filterBounds(GRANICA)
            .filterDate(f"{year}-01-01", f"{year}-12-31")
            .select("temperature_2m")
            .mean()
            .clip(GRANICA)
        )
        image = temp_k.subtract(273.15).rename("temperature_C")
        scale = 9000
        unit = "°C"

    elif layer == "gedi":
        if year < 2020:
            return {
                "error": "GEDI podaci nisu dostupni za izabranu godinu."
            }

        image = (
            ee.ImageCollection("LARSE/GEDI/GEDI02_A_002_MONTHLY")
            .filterBounds(GRANICA)
            .filterDate(f"{year}-01-01", f"{year}-12-31")
            .select("rh98")
            .median()
            .clip(GRANICA)
        )
        scale = 25
        unit = "m"
    elif layer == "forest-types":

        spring = get_sentinel_period(year, "03-01", "04-30")
        summer = get_sentinel_period(year, "06-01", "09-30")

        ndvi_spring = spring.normalizedDifference(["B8", "B4"])
        ndvi_summer = summer.normalizedDifference(["B8", "B4"])
        nbr_summer = summer.normalizedDifference(["B8", "B12"])

        ndvi_diff = ndvi_summer.subtract(ndvi_spring)
        forest = get_forest_mask(year)
        srtm = ee.Image("USGS/SRTMGL1_003").clip(GRANICA)

        coniferous = (
            forest
            .And(ndvi_diff.lt(0.14))
            .And(srtm.gt(850))
            .And(nbr_summer.gt(0.35))
        )

        deciduous = forest.And(coniferous.Not())

        def area_ha(mask):
            area = (
                mask.selfMask()
                .multiply(ee.Image.pixelArea())
                .divide(10000)
                .reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=GRANICA.geometry(),
                    scale=10,
                    maxPixels=1e13
                )
                .getInfo()
            )

            return round(list(area.values())[0], 2)

        return {
            "layer": "Tipovi šuma",
            "year": year,
            "coniferous": area_ha(coniferous),
            "deciduous": area_ha(deciduous)
        }
    else:
        return {"error": "Nepoznat sloj."}

    stats = image.reduceRegion(
        reducer=ee.Reducer.minMax().combine(
            reducer2=ee.Reducer.mean(),
            sharedInputs=True
        ),
        geometry=GRANICA.geometry(),
        scale=scale,
        maxPixels=1e13
    ).getInfo()

    values = list(stats.values())

    return {
        "layer": layer,
        "year": year,
        "min": round(min(values), 2),
        "mean": round(sum(values) / len(values), 2),
        "max": round(max(values), 2),
        "unit": unit
    }
@app.get("/api/loss/{year_from}/{year_to}")
def get_forest_loss(year_from: int, year_to: int):
    forest_from = get_forest_mask(year_from)
    forest_to = get_forest_mask(year_to)

    loss = forest_from.And(forest_to.Not())

    map_id = loss.selfMask().getMapId({
        "palette": ["red"]
    })

    return {
        "layer": "Forest Loss",
        "year_from": year_from,
        "year_to": year_to,
        "tile_url": map_id["tile_fetcher"].url_format
    }
@app.get("/api/gain/{year_from}/{year_to}")
def get_forest_gain(year_from: int, year_to: int):
    forest_from = get_forest_mask(year_from)
    forest_to = get_forest_mask(year_to)

    gain = forest_to.And(forest_from.Not())

    map_id = gain.selfMask().getMapId({
        "palette": ["lime"]
    })

    return {
        "layer": "Forest Gain",
        "year_from": year_from,
        "year_to": year_to,
        "tile_url": map_id["tile_fetcher"].url_format
    }
@app.get("/api/change/{year_from}/{year_to}")
def get_forest_change(year_from: int, year_to: int):
    forest_from = get_forest_mask(year_from)
    forest_to = get_forest_mask(year_to)

    stable = forest_from.And(forest_to)
    loss = forest_from.And(forest_to.Not())
    gain = forest_to.And(forest_from.Not())

    change = (
        stable.multiply(1)
        .where(loss, 2)
        .where(gain, 3)
        .selfMask()
    )

    map_id = change.getMapId({
        "min": 1,
        "max": 3,
        "palette": ["darkgreen", "red", "lime"]
    })

    return {
        "layer": "Forest Change",
        "year_from": year_from,
        "year_to": year_to,
        "tile_url": map_id["tile_fetcher"].url_format
    }
@app.get("/api/builtup/{year_from}/{year_to}")
def get_loss_to_builtup(year_from: int, year_to: int):
    forest_from = get_forest_mask(year_from)
    forest_to = get_forest_mask(year_to)

    forest_loss = forest_from.And(forest_to.Not())

    dw_to = get_dynamic_world(year_to)
    builtup_to = dw_to.eq(6)

    loss_to_builtup = forest_loss.And(builtup_to)

    map_id = loss_to_builtup.selfMask().getMapId({
        "palette": ["purple"]
    })

    return {
        "layer": "Forest Loss to Built-up",
        "year_from": year_from,
        "year_to": year_to,
        "tile_url": map_id["tile_fetcher"].url_format
    }
@app.get("/api/change-stats/{layer}/{year_from}/{year_to}")
def get_change_stats(layer: str, year_from: int, year_to: int):
    forest_from = get_forest_mask(year_from)
    forest_to = get_forest_mask(year_to)

    if layer == "loss":
        mask = forest_from.And(forest_to.Not())
        title = "Gubitak šuma"

    elif layer == "gain":
        mask = forest_to.And(forest_from.Not())
        title = "Dobitak šuma"

    elif layer == "builtup":
        forest_loss = forest_from.And(forest_to.Not())
        builtup_to = get_dynamic_world(year_to).eq(6)
        mask = forest_loss.And(builtup_to)
        title = "Gubitak šuma zbog izgradnje"
    elif layer == "change":

        stable = forest_from.And(forest_to)
        loss = forest_from.And(forest_to.Not())
        gain = forest_to.And(forest_from.Not())

        def area_ha(mask):
            area = (
                mask.selfMask()
                .multiply(ee.Image.pixelArea())
                .divide(10000)
                .reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=GRANICA.geometry(),
                    scale=10,
                    maxPixels=1e13
                )
                .getInfo()
            )

            return round(list(area.values())[0], 2)

        return {
            "title": "Promena šuma",
            "year_from": year_from,
            "year_to": year_to,
            "stable": area_ha(stable),
            "loss": area_ha(loss),
            "gain": area_ha(gain)
        }
    else:
        return {"error": "Statistika za ovaj sloj još nije dostupna."}

    area_image = mask.selfMask().multiply(ee.Image.pixelArea()).divide(10000)

    area = area_image.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=GRANICA.geometry(),
        scale=10,
        maxPixels=1e13
    ).getInfo()

    value = list(area.values())[0]

    return {
        "title": title,
        "year_from": year_from,
        "year_to": year_to,
        "area_ha": round(value, 2)
    }
@app.get("/api/forest-types/{year}")
def get_forest_types(year: int):
    spring = get_sentinel_period(year, "03-01", "04-30")
    summer = get_sentinel_period(year, "06-01", "09-30")

    ndvi_spring = spring.normalizedDifference(["B8", "B4"])
    ndvi_summer = summer.normalizedDifference(["B8", "B4"])
    nbr_summer = summer.normalizedDifference(["B8", "B12"])

    ndvi_diff = ndvi_summer.subtract(ndvi_spring)
    forest = get_forest_mask(year)
    srtm = ee.Image("USGS/SRTMGL1_003").clip(GRANICA)

    coniferous = (
        forest
        .And(ndvi_diff.lt(0.14))
        .And(srtm.gt(850))
        .And(nbr_summer.gt(0.35))
    )

    deciduous = forest.And(coniferous.Not())

    forest_types = (
        coniferous.multiply(1)
        .where(deciduous, 2)
        .selfMask()
    )

    map_id = forest_types.getMapId({
        "min": 1,
        "max": 2,
        "palette": ["darkgreen", "lightgreen"]
    })

    return {
        "year": year,
        "layer": "Forest Types",
        "tile_url": map_id["tile_fetcher"].url_format
    }
@app.get("/api/forest-area-chart")
def get_forest_area_chart():
    years = list(range(2017, 2025))
    results = []

    for year in years:
        forest = get_forest_mask(year)

        area_image = (
            forest.selfMask()
            .multiply(ee.Image.pixelArea())
            .divide(10000)
        )

        area = area_image.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=GRANICA.geometry(),
            scale=10,
            maxPixels=1e13
        ).getInfo()

        value = list(area.values())[0]

        results.append({
            "year": year,
            "area_ha": round(value, 2)
        })

    return results


@app.get("/api/evi/{year}")
def get_evi(year: int):
    start_date = f"{year}-06-01"
    end_date = f"{year}-09-30"

    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(GRANICA)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .select(["B2", "B4", "B8"])
        .median()
        .clip(GRANICA)
        .divide(10000)
        .toFloat()
    )

    evi = s2.expression(
        "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
        {
            "NIR": s2.select("B8"),
            "RED": s2.select("B4"),
            "BLUE": s2.select("B2")
        }
    ).rename("EVI")

    map_id = evi.getMapId({
        "min": 0,
        "max": 1,
        "palette": ["white", "yellow", "green", "darkgreen"]
    })

    return {
        "year": year,
        "layer": "EVI",
        "tile_url": map_id["tile_fetcher"].url_format
    }


@app.get("/api/nbr/{year}")
def get_nbr(year: int):
    start_date = f"{year}-06-01"
    end_date = f"{year}-09-30"

    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(GRANICA)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .select(["B8", "B12"])
        .median()
        .clip(GRANICA)
        .divide(10000)
        .toFloat()
    )

    nbr = s2.normalizedDifference(["B8", "B12"]).rename("NBR")

    map_id = nbr.getMapId({
        "min": -1,
        "max": 1,
        "palette": ["red", "yellow", "white", "green"]
    })

    return {
        "year": year,
        "layer": "NBR",
        "tile_url": map_id["tile_fetcher"].url_format
    }
app.mount("/static", StaticFiles(directory="static"), name="static")

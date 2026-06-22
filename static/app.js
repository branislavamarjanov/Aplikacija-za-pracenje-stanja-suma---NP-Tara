const map = L.map("map").setView([43.9, 19.45], 13);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);

let activeLayer = null;
let forestChart = null;

// --------------------------------------------------
// GLAVNA FUNKCIJA ZA PRIKAZ SLOJEVA
// --------------------------------------------------

async function loadLayer() {
    const mode = document.getElementById("mode").value;
    const layer = document.getElementById("layer").value;

    const statsBox = document.getElementById("stats");
    const legendBox = document.getElementById("legend");

    statsBox.innerHTML = "Učitavanje sloja i računanje statistike...";
    legendBox.innerHTML = "Učitavanje legende...";

    try {
        let response;

        if (mode === "change") {
            const yearFrom = document.getElementById("yearFrom").value;
            const yearTo = document.getElementById("yearTo").value;

            response = await fetch(`/api/${layer}/${yearFrom}/${yearTo}`);
        } else {
            const year = document.getElementById("year").value;

            response = await fetch(`/api/${layer}/${year}`);
        }

        const data = await response.json();

        if (data.error) {
            statsBox.innerHTML = data.error;
            legendBox.innerHTML = "Legenda nije dostupna.";
            return;
        }

        if (activeLayer) {
            map.removeLayer(activeLayer);
        }

        activeLayer = L.tileLayer(data.tile_url, {
            opacity: 0.8
        });

        activeLayer.addTo(map);

        updateLegend(layer);

        if (mode === "change") {
            const yearFrom = document.getElementById("yearFrom").value;
            const yearTo = document.getElementById("yearTo").value;

            await loadChangeStats(layer, yearFrom, yearTo);
        } else {
            const year = document.getElementById("year").value;

            await loadStats(layer, year);
        }

    } catch (error) {
        console.error(error);

        statsBox.innerHTML = "Greška pri učitavanju. Pogledaj Console u browseru.";
        legendBox.innerHTML = "Legenda nije učitana zbog greške.";
    }
}

// --------------------------------------------------
// DUGME ZA PRIKAZ
// --------------------------------------------------

document
    .getElementById("showBtn")
    .addEventListener("click", loadLayer);

// --------------------------------------------------
// PROMENA TIPA PRIKAZA
// --------------------------------------------------

document.getElementById("mode").addEventListener("change", function () {
    const mode = this.value;

    const singleYear = document.getElementById("singleYear");
    const changeYears = document.getElementById("changeYears");
    const layerSelect = document.getElementById("layer");

    if (mode === "change") {
        singleYear.style.display = "none";
        changeYears.style.display = "block";
    } else {
        singleYear.style.display = "block";
        changeYears.style.display = "none";
    }

    layerSelect.innerHTML = "";

    document.getElementById("stats").innerHTML =
        "Statistika će biti prikazana ovde.";

    document.getElementById("legend").innerHTML =
        "Legenda će biti prikazana ovde.";

    if (activeLayer) {
        map.removeLayer(activeLayer);
        activeLayer = null;
    }

    if (mode === "state") {
        layerSelect.innerHTML = `
            <option value="ndvi">NDVI</option>
            <option value="evi">EVI</option>
            <option value="nbr">NBR</option>
            <option value="forest-types">Četinarske i listopadne šume</option>
        `;
    }

    else if (mode === "additional") {
        layerSelect.innerHTML = `
            <option value="srtm">SRTM nadmorska visina</option>
            <option value="chirps">CHIRPS padavine</option>
            <option value="gedi">GEDI visina šume</option>
            <option value="era5">ERA5 temperatura</option>
        `;
    }

    else if (mode === "change") {
        layerSelect.innerHTML = `
            <option value="loss">Gubitak šuma</option>
            <option value="gain">Dobitak šuma</option>
            <option value="change">Promena šuma</option>
            <option value="builtup">Gubitak zbog izgradnje</option>
        `;
    }
});

// --------------------------------------------------
// PROMENA SLOJA
// --------------------------------------------------

document.getElementById("layer").addEventListener("change", function () {
    document.getElementById("stats").innerHTML =
        "Statistika će biti prikazana ovde.";

    document.getElementById("legend").innerHTML =
        "Legenda će biti prikazana ovde.";
});

// --------------------------------------------------
// GRANICA NP TARA
// --------------------------------------------------

async function loadBoundary() {
    const response = await fetch("/api/boundary");
    const data = await response.json();

    L.geoJSON(data, {
        style: {
            color: "green",
            weight: 3,
            fillOpacity: 0
        }
    }).addTo(map);
}

// --------------------------------------------------
// STATISTIKA ZA POJEDINAČNE SLOJEVE
// --------------------------------------------------

async function loadStats(layer, year) {
    const statsBox = document.getElementById("stats");

    statsBox.innerHTML = "Računanje statistike, sačekajte...";

    const response = await fetch(`/api/stats/${layer}/${year}`);
    const data = await response.json();

    if (data.error) {
        statsBox.innerHTML = data.error;
        return;
    }

    if (layer === "forest-types") {
        statsBox.innerHTML = `
            <strong>Tipovi šuma ${year}</strong><br>
            Četinarske šume: ${data.coniferous} ha<br>
            Listopadne šume: ${data.deciduous} ha
        `;
        return;
    }

    statsBox.innerHTML = `
        <strong>${data.layer.toUpperCase()} ${data.year}</strong><br>
        Minimum: ${data.min} ${data.unit}<br>
        Srednja vrednost: ${data.mean} ${data.unit}<br>
        Maksimum: ${data.max} ${data.unit}
    `;
}

// --------------------------------------------------
// STATISTIKA ZA ANALIZU PROMENA
// --------------------------------------------------

async function loadChangeStats(layer, yearFrom, yearTo) {
    const statsBox = document.getElementById("stats");

    statsBox.innerHTML = "Računanje površine, sačekajte...";

    const response = await fetch(`/api/change-stats/${layer}/${yearFrom}/${yearTo}`);
    const data = await response.json();

    if (data.error) {
        statsBox.innerHTML = data.error;
        return;
    }

    if (layer === "change") {
        statsBox.innerHTML = `
            <strong>Promena šuma ${yearFrom}-${yearTo}</strong><br>
            Stabilne šume: ${data.stable} ha<br>
            Gubitak šuma: ${data.loss} ha<br>
            Dobitak šuma: ${data.gain} ha
        `;
        return;
    }

    statsBox.innerHTML = `
        <strong>${data.title} ${data.year_from}–${data.year_to}</strong><br>
        Površina: ${data.area_ha} ha
    `;
}

// --------------------------------------------------
// LEGENDA
// --------------------------------------------------

function updateLegend(layer) {
    const legend = document.getElementById("legend");

    let items = [];

    if (layer === "ndvi") {
        items = [
            ["red", "Slaba vegetacija"],
            ["yellow", "Umerena vegetacija"],
            ["green", "Gusta vegetacija"]
        ];
    }

    else if (layer === "evi") {
        items = [
            ["white", "Niža vegetaciona aktivnost"],
            ["yellow", "Srednja vegetaciona aktivnost"],
            ["darkgreen", "Visoka vegetaciona aktivnost"]
        ];
    }

    else if (layer === "nbr") {
        items = [
            ["red", "Degradirane / gole površine"],
            ["yellow", "Ređa vegetacija"],
            ["green", "Zdrava šumska vegetacija"]
        ];
    }

    else if (layer === "srtm") {
        items = [
            ["green", "Niže nadmorske visine"],
            ["yellow", "Srednje visine"],
            ["brown", "Više nadmorske visine"],
            ["white", "Najviši delovi"]
        ];
    }

    else if (layer === "chirps") {
        items = [
            ["#ffffcc", "Manje padavina"],
            ["#41b6c4", "Srednje padavine"],
            ["#225ea8", "Više padavina"]
        ];
    }

    else if (layer === "era5") {
        items = [
            ["blue", "Niža temperatura"],
            ["yellow", "Srednja temperatura"],
            ["red", "Viša temperatura"]
        ];
    }

    else if (layer === "gedi") {
        items = [
            ["#ffffcc", "Niža visina šume"],
            ["#41ab5d", "Srednja visina šume"],
            ["#005a32", "Veća visina šume"]
        ];
    }

    else if (layer === "forest-types") {
        items = [
            ["darkgreen", "Četinarske šume"],
            ["lightgreen", "Listopadne šume"]
        ];
    }

    else if (layer === "change") {
        items = [
            ["darkgreen", "Stabilna šuma"],
            ["red", "Gubitak šume"],
            ["lime", "Dobitak šume"]
        ];
    }

    else if (layer === "loss") {
        items = [
            ["red", "Gubitak šume"]
        ];
    }

    else if (layer === "gain") {
        items = [
            ["lime", "Dobitak šume"]
        ];
    }

    else if (layer === "builtup") {
        items = [
            ["purple", "Gubitak šume zbog izgradnje"]
        ];
    }

    legend.innerHTML = "<strong>Legenda</strong><br>";

    items.forEach(function (item) {
        legend.innerHTML += `
            <div style="display:flex; align-items:center; margin:6px 0;">
                <div style="
                    width:18px;
                    height:18px;
                    background:${item[0]};
                    margin-right:10px;
                    border:1px solid #555;">
                </div>
                <span>${item[1]}</span>
            </div>
        `;
    });
}

// --------------------------------------------------
// GRAFIKON POVRŠINE ŠUMA
// --------------------------------------------------

async function loadForestChart() {
    const response = await fetch("/api/forest-area-chart");
    const data = await response.json();

    const years = data.map(item => item.year);
    const areas = data.map(item => item.area_ha);

    const ctx = document.getElementById("forestChart");

    if (forestChart) {
        forestChart.destroy();
    }

    forestChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: years,
            datasets: [{
                label: "Površina šuma (ha)",
                data: areas,
                borderWidth: 2,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true
                },
                title: {
                    display: true,
                    text: "Promena površine šuma 2017–2024"
                }
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: "Površina (ha)"
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: "Godina"
                    }
                }
            }
        }
    });
}

// --------------------------------------------------
// POČETNO UČITAVANJE
// --------------------------------------------------

loadBoundary();
loadForestChart();
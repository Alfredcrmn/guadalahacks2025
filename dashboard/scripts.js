let chartTypeInstance;
let chartSideInstance;
let chartLinkInstance;
let chartTileInstance;
let chartDistributionInstance;


document.addEventListener("DOMContentLoaded", () => {
  const tileFilter = document.getElementById("tileFilter");
  const overviewTitle = document.querySelector(".filters-left h2");

  // Cargar los tiles desde tiles.json
  fetch("tiles.json")
    .then((response) => response.json())
    .then((tileIds) => {
      tileIds.forEach((tileId) => {
        const option = document.createElement("option");
        option.value = tileId;
        option.textContent = tileId;
        tileFilter.appendChild(option);
      });

      // Texto inicial
      overviewTitle.textContent = "Overview of errors in: All";

      // Cargar todos los errores al inicio
      loadAndDisplayAllErrors();
    })
    .catch((error) => {
      console.error("Error loading tiles.json:", error);
    });

  // Cambiar tile seleccionado
  tileFilter.addEventListener("change", async () => {
    const selected = tileFilter.value;
    const overviewTitle = document.querySelector(".filters-left h2");

    overviewTitle.textContent = selected
      ? `Overview of errors in: ${selected}`
      : "Overview of errors in: All";

    if (selected) {
      loadAndDisplayErrors(selected);
    } else {
      loadAndDisplayAllErrors();
    }
  });
});

// Función general que carga errores y renderiza las gráficas
async function loadAndDisplayErrors(tileId) {
  const errors = await loadErrorsForTile(tileId);
  console.log(`🔍 ${errors.length} errores cargados para tile ${tileId}`);
  renderCharts(errors);
}

// Carga errores desde las carpetas de validación
async function loadErrorsForTile(tileId) {
  const sources = [
    `/outputs/validation_multidigit/errors_${tileId}.json`,
    `/outputs/validation_side/errors_${tileId}.json`,
  ];

  let allErrors = [];

  for (const src of sources) {
    try {
      const res = await fetch(src);
      if (res.ok) {
        const data = await res.json();
        allErrors = allErrors.concat(data);
      } else {
        console.warn(`⚠️ Archivo no encontrado: ${src}`);
      }
    } catch (err) {
      console.warn(`⚠️ Error al cargar ${src}:`, err);
    }
  }

  return allErrors;
}

// Cargar y mostrar todos los errores combinados
async function loadAndDisplayAllErrors() {
  console.log("🔁 Cargando todos los errores...");

  const tileIds = await fetch("tiles.json")
    .then((res) => res.json())
    .catch((err) => {
      console.error("Error loading tiles.json:", err);
      return [];
    });

  let allErrors = [];

  for (const tileId of tileIds) {
    console.log(`📂 Tile ${tileId}`);
    const errors = await loadErrorsForTile(tileId);
    console.log(`→ ${errors.length} errores`);
    allErrors = allErrors.concat(errors);
  }

  console.log(`📊 Total de errores combinados: ${allErrors.length}`);

  if (allErrors.length === 0) {
    alert("No se encontraron errores en ninguno de los tiles.");
  }

  renderCharts(allErrors);
}

async function loadAndDisplayErrors(tileId) {
  const errors = await loadErrorsForTile(tileId);
  console.log(`🔍 ${errors.length} errores cargados para tile ${tileId}`);
  updateKPI(errors);  // ✅ Agrega esto
  renderCharts(errors);
}

async function loadAndDisplayAllErrors() {
  console.log("🔁 Cargando todos los errores...");

  const tileIds = await fetch("tiles.json")
    .then((res) => res.json())
    .catch((err) => {
      console.error("Error loading tiles.json:", err);
      return [];
    });

  let allErrors = [];

  for (const tileId of tileIds) {
    const errors = await loadErrorsForTile(tileId);
    allErrors = allErrors.concat(errors);
  }

  console.log(`📊 Total de errores combinados: ${allErrors.length}`);

  if (allErrors.length === 0) {
    alert("No se encontraron errores en ninguno de los tiles.");
  }

  updateKPI(allErrors);  // ✅ Agrega esto
  renderCharts(allErrors);
}


// Renderizar todas las gráficas
function renderCharts(errors) {
  renderChartByType(errors);
  renderChartBySideMismatch(errors);
  renderChartByLink(errors);
  renderChartByTile(errors);
  renderChartErrorDistribution(errors);
  renderErrorMap(errors);
}


// Errores por tipo
function renderChartByType(errors) {
  if (chartTypeInstance) chartTypeInstance.destroy();

  const counts = {};
  errors.forEach((e) => {
    const type = e.error_type;
    counts[type] = (counts[type] || 0) + 1;
  });

  const labels = Object.keys(counts);
  const values = Object.values(counts);

  chartTypeInstance = new Chart(document.getElementById("chartByType"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Errors by Type",
          data: values,
          backgroundColor: "#0077cc",
        },
      ],
    },
    options: {
      plugins: {
        title: {
          display: true,
          text: "Errors by Type",
          color: "white",
        },
        legend: {
          labels: {
            color: "white", // Add this line
          },
        },
      },
      responsive: true,
  scales: {
    y: { 
      beginAtZero: true,
      ticks: { color: 'white' }, // Add this line
      grid: { color: 'rgba(255, 255, 255, 0.1)' },
      border: { color: 'white' }
    },
    x: { // Add this block
      ticks: { color: 'white' },
      grid: { color: 'rgba(255, 255, 255, 0.1)' },
      border: { color: 'white' }
    }
  },
    },
  });
}

// Lado esperado vs real
function renderChartBySideMismatch(errors) {
  if (chartSideInstance) chartSideInstance.destroy();

  const mismatchCounts = {};
  errors.forEach((e) => {
    if (!e.expected_side || !e.actual_side) return;
    const combo = `${e.expected_side} → ${e.actual_side}`;
    mismatchCounts[combo] = (mismatchCounts[combo] || 0) + 1;
  });

  const labels = Object.keys(mismatchCounts);
  const values = Object.values(mismatchCounts);

  chartSideInstance = new Chart(document.getElementById("chartBySide"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Side Mismatches",
          data: values,
          backgroundColor: "#ff6600",
        },
      ],
    },
    options: {
      plugins: {
        title: {
          display: true,
          text: "Expected vs Actual Side",
          color: "white",
        },
        legend: {
          labels: {
            color: "white", // Add this line
          },
        },
      },
      responsive: true,
  scales: {
    y: { 
      beginAtZero: true,
      ticks: { color: 'white' }, // Add this line
      grid: { color: 'rgba(255, 255, 255, 0.1)' },
      border: { color: 'white' }
    },
    x: { // Add this block
      ticks: { color: 'white' },
      grid: { color: 'rgba(255, 255, 255, 0.1)' },
      border: { color: 'white' }
    }
  },
    },
  });
}

// Top 10 links con más errores
function renderChartByLink(errors) {
  if (chartLinkInstance) chartLinkInstance.destroy();

  const linkCounts = {};
  errors.forEach((e) => {
    const link = e.link_id;
    linkCounts[link] = (linkCounts[link] || 0) + 1;
  });

  const sorted = Object.entries(linkCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const labels = sorted.map(([link]) => `Link ${link}`);
  const values = sorted.map(([, count]) => count);

  chartLinkInstance = new Chart(document.getElementById("chartByLink"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Top 10 Link IDs with Most Errors",
          data: values,
          backgroundColor: "#33aa55",
        },
      ],
    },
    options: {
      plugins: {
        title: {
          display: true,
          text: "Top 10 Links with Errors",
          color: "white",
        },
        legend: {
          labels: {
            color: "white", // Add this line
          },
        },
      },
      responsive: true,
  scales: {
    y: { 
      beginAtZero: true,
      ticks: { color: 'white' }, // Add this line
      grid: { color: 'rgba(255, 255, 255, 0.1)' },
      border: { color: 'white' }
    },
    x: { // Add this block
      ticks: { color: 'white' },
      grid: { color: 'rgba(255, 255, 255, 0.1)' },
      border: { color: 'white' }
    }
  },
    },
  });
}

document.getElementById("downloadCsv").addEventListener("click", async () => {
  const selected = document.getElementById("tileFilter").value;
  const tileIds = await fetch("tiles.json").then(res => res.json());

  const tilesToDownload = selected ? [selected] : tileIds;

  const zip = new JSZip();

  for (const tileId of tilesToDownload) {
    const folder = zip.folder(`tile_${tileId}`);

    const files = [
      {
        name: `errors_multidigit_${tileId}.json`,
        path: `/outputs/validation_multidigit/errors_${tileId}.json`
      },
      {
        name: `errors_side_${tileId}.json`,
        path: `/outputs/validation_side/errors_${tileId}.json`
      },
      {
        name: `existence_${tileId}.geojson`,
        path: `/outputs/existence/existence_${tileId}.geojson`
      }
    ];

    for (const file of files) {
      try {
        const res = await fetch(file.path);
        if (!res.ok) {
          console.warn(`No se pudo cargar: ${file.path}`);
          continue;
        }
        const content = await res.text();
        folder.file(file.name, content);
      } catch (err) {
        console.error(`Error leyendo ${file.path}:`, err);
      }
    }
  }

  const zipBlob = await zip.generateAsync({ type: "blob" });
  const zipFileName = selected ? `tile_${selected}_errors.zip` : `all_tiles_errors.zip`;

  const link = document.createElement("a");
  link.href = URL.createObjectURL(zipBlob);
  link.download = zipFileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});

function renderChartByTile(errors) {
  if (chartTileInstance) chartTileInstance.destroy();

  const tileCounts = {};

  errors.forEach(e => {
    const tileId = e.tile_id || "Unknown";
    tileCounts[tileId] = (tileCounts[tileId] || 0) + 1;
  });

  const sorted = Object.entries(tileCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const labels = sorted.map(([tile]) => `Tile ${tile}`);
  const values = sorted.map(([, count]) => count);

  chartTileInstance = new Chart(document.getElementById("chartByTile"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Top Tiles by Error Count",
        data: values,
        backgroundColor: "#ff4477"
      }]
    },
    options: {
      indexAxis: 'y',
      plugins: {
        title: {
          display: true,
          text: "Top 10 Tiles with Most Errors",
          color: "white"
        },
        legend: { display: false }
      },
      responsive: true,
      scales: {
        x: {
          beginAtZero: true,
          ticks: { color: 'white' },
          grid: { color: 'rgba(255,255,255,0.1)' },
          border: { color: 'white' }
        },
        y: {
          ticks: { color: 'white' },
          grid: { color: 'rgba(255,255,255,0.1)' },
          border: { color: 'white' }
        }
      }
    }
  });
}


function renderChartErrorDistribution(errors) {
  if (chartDistributionInstance) chartDistributionInstance.destroy();

  const counts = {};
  errors.forEach(e => {
    const type = e.error_type || "Unknown";
    counts[type] = (counts[type] || 0) + 1;
  });

  const labels = Object.keys(counts);
  const values = Object.values(counts);

  const backgroundColors = labels.map((_, i) =>
    `hsl(${(i * 360) / labels.length}, 70%, 50%)`
  );

  chartDistributionInstance = new Chart(document.getElementById("chartErrorDistribution"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: backgroundColors
      }]
    },
    options: {
      plugins: {
        title: {
          display: true,
          text: "Error Type Distribution (%)",
          color: "white"
        },
        legend: {
          labels: { color: "white" }
        }
      },
      responsive: true
    }
  });
}

function renderErrorMap(errors) {
  const mapContainer = document.getElementById("chartMap");

  // Reset Leaflet map
  if (mapContainer._leaflet_id) {
    mapContainer._leaflet_id = null;
    mapContainer.innerHTML = "";
  }

  const map = L.map("chartMap").setView([19.43, -99.13], 12); // CDMX por defecto

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
  }).addTo(map);

  const bounds = [];

  errors.forEach((error) => {
    let lat, lon;

    if (error.lat && error.lon) {
      lat = error.lat;
      lon = error.lon;
    } else if (error.geometry && Array.isArray(error.geometry)) {
      [lon, lat] = error.geometry; // OJO: GeoJSON usa [lon, lat]
    }

    if (!lat || !lon) return;

    const marker = L.circleMarker([lat, lon], {
      radius: 5,
      fillColor: "#f00",
      fillOpacity: 0.7,
      color: "#fff",
      weight: 1,
    }).addTo(map);

    marker.bindPopup(`<b>${error.error_type}</b>`);
    bounds.push([lat, lon]);
  });

  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [20, 20] });
  }
}

function updateKPI(errors) {
  document.getElementById("kpi-total").textContent = errors.length;
  document.getElementById("kpi-tiles").textContent = new Set(errors.map(e => e.tile_id)).size;
  document.getElementById("kpi-links").textContent = new Set(errors.map(e => e.link_id)).size;
  document.getElementById("kpi-types").textContent = new Set(errors.map(e => e.error_type)).size;
}

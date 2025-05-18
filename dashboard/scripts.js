let chartTypeInstance;
let chartSideInstance;
let chartLinkInstance;

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

// Renderizar todas las gráficas
function renderCharts(errors) {
  renderChartByType(errors);
  renderChartBySideMismatch(errors);
  renderChartByLink(errors);
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

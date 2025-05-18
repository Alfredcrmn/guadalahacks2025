document.addEventListener("DOMContentLoaded", () => {
  const tileFilter = document.getElementById("tileFilter");
  const overviewTitle = document.querySelector(".filters-left h2");

  // Cargar los tiles desde tiles.json
  fetch("tiles.json")
    .then(response => response.json())
    .then(tileIds => {
      tileIds.forEach(tileId => {
        const option = document.createElement("option");
        option.value = tileId;
        option.textContent = tileId;
        tileFilter.appendChild(option);
      });

      // Establecer texto inicial del label
      const selected = tileFilter.value;
      overviewTitle.textContent = selected
        ? `Overview of errors in: ${selected}`
        : "Overview of errors in: All";
    })
    .catch(error => {
      console.error("Error loading tiles.json:", error);
    });

  // Actualizar texto cuando se cambia el selector
  tileFilter.addEventListener("change", () => {
    const selected = tileFilter.value;
    overviewTitle.textContent = selected
      ? `Overview of errors in: ${selected}`
      : "Overview of errors in: All";
  });
});

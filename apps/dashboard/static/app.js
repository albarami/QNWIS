async function fetchJSON(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Request failed (${response.status}): ${detail}`);
  }
  return response.json();
}

(async () => {
  try {
    const cards = await fetchJSON('/v1/ui/cards/top-sectors?n=5');
    const cardsContainer = document.getElementById('cards');
    cards.cards.forEach((card) => {
      const el = document.createElement('div');
      el.className = 'card';
      el.innerHTML = `
        <div class="title">${card.title}</div>
        <div class="sub">${card.subtitle}</div>
        <div class="kpi">${card.kpi} ${card.unit || ''}</div>
      `;
      cardsContainer.appendChild(el);
    });

    const sectorEmployment = await fetchJSON('/v1/ui/charts/sector-employment');
    const employmentTarget = document.getElementById('sector-employment');
    employmentTarget.innerText = `Categories: ${sectorEmployment.categories.length}`;
    if (typeof sectorEmployment.year === 'number') {
      const csvLink = document.getElementById('dl-csv');
      const svgLink = document.getElementById('dl-svg');
      const querySuffix = `year=${sectorEmployment.year}`;
      csvLink.href = `/v1/ui/export/csv?resource=sector-employment&${querySuffix}`;
      svgLink.href = `/v1/ui/export/svg?chart=sector-employment&${querySuffix}`;
    }

    const salary = await fetchJSON('/v1/ui/charts/salary-yoy?sector=Energy');
    document.getElementById('salary').innerText = `Points: ${salary.series.length}`;
  } catch (error) {
    console.error(error);
  }
})();

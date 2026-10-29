// Shared starting data for both target apps, so a skill learned in one
// can be checked against the same task in the other.
// Each dataset is a header row plus records. Variants let the benchmark
// run a learned skill on data the tutorial never showed.
window.EIDOS_DATASETS = {
  sales: [
    ["Region", "Month", "Product", "Units", "Revenue"],
    ["North", "Jan", "Lamp", 120, 3600],
    ["South", "Jan", "Desk", 45, 9000],
    ["East", "Feb", "Chair", 210, 8400],
    ["West", "Feb", "Lamp", 95, 2850],
    ["North", "Mar", "Desk", 60, 12000],
    ["South", "Mar", "Chair", 180, 7200],
    ["East", "Apr", "Lamp", 140, 4200],
    ["West", "Apr", "Desk", 30, 6000],
    ["North", "May", "Chair", 250, 10000],
    ["South", "May", "Lamp", 75, 2250],
  ],
  inventory: [
    ["Warehouse", "Week", "Item", "Stock", "Value"],
    ["Newark", "W1", "Bolts", 900, 450],
    ["Austin", "W1", "Panels", 40, 8800],
    ["Denver", "W2", "Cables", 310, 1240],
    ["Newark", "W2", "Panels", 25, 5500],
    ["Austin", "W3", "Bolts", 1200, 600],
    ["Denver", "W3", "Panels", 55, 12100],
    ["Newark", "W4", "Cables", 410, 1640],
    ["Austin", "W4", "Cables", 150, 600],
  ],
};

window.eidosDataset = function () {
  const p = new URLSearchParams(location.search);
  return window.EIDOS_DATASETS[p.get("data") || "sales"] || window.EIDOS_DATASETS.sales;
};

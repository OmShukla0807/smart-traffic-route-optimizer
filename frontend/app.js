/**
 * Smart Traffic Route Optimizer - Frontend Interactive Client Application
 */

const API_BASE = window.location.origin;

// State
let appState = {
  nodes: [],
  roads: [],
  vehicles: [],
  selectedSource: "NODE_CP",
  selectedDestination: "NODE_CYBER",
  selectedVehicle: "Petrol_Sedan",
  weatherCondition: "Clear",
  hourOfDay: 9,
  dayOfWeek: 1,
  weights: { time: 50, fuel: 30, weather: 20 },
  activeRouteKey: "all", // "all", "fastest", "eco", "weather_safe"
  lastResult: null
};

// Map Objects
let map = null;
let nodeMarkersLayer = null;
let routePolylinesLayer = null;
let routeLayers = {
  fastest: null,
  eco: null,
  weather_safe: null
};

// Color Palette for Routes
const ROUTE_COLORS = {
  fastest: { color: "#00e5ff", weight: 6, opacity: 0.9, glow: "rgba(0, 229, 255, 0.4)" },
  eco: { color: "#10b981", weight: 5, opacity: 0.9, glow: "rgba(16, 185, 129, 0.4)" },
  weather_safe: { color: "#f59e0b", weight: 5, opacity: 0.9, glow: "rgba(245, 158, 11, 0.4)" }
};

// -------------------------------------------------------------
// Initialization
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  initMap();
  setupEventListeners();
  await loadInitialData();
  await triggerRouteOptimization();
  await loadQueryHistory();
});

function initMap() {
  // Center on Delhi NCR
  map = L.map("leaflet-map", {
    zoomControl: false
  }).setView([28.6000, 77.2000], 11);

  // Add custom styled Dark Tile Layer (CartoDB Dark Matter)
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> | OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(map);

  L.control.zoom({ position: "bottomright" }).addTo(map);

  nodeMarkersLayer = L.layerGroup().addTo(map);
  routePolylinesLayer = L.layerGroup().addTo(map);
}

// -------------------------------------------------------------
// Load Metadata from Backend
// -------------------------------------------------------------
async function loadInitialData() {
  try {
    const [nodesRes, vehiclesRes] = await Promise.all([
      fetch(`${API_BASE}/api/nodes`).then(r => r.json()),
      fetch(`${API_BASE}/api/vehicles`).then(r => r.json())
    ]);

    appState.nodes = nodesRes.nodes || [];
    appState.vehicles = vehiclesRes.vehicles || [];

    populateNodeDropdowns();
    renderVehicleGrid();
    renderMapNodes();
  } catch (err) {
    console.error("Error loading initial data:", err);
  }
}

function populateNodeDropdowns() {
  const srcSelect = document.getElementById("select-source");
  const dstSelect = document.getElementById("select-destination");

  srcSelect.innerHTML = "";
  dstSelect.innerHTML = "";

  appState.nodes.forEach(node => {
    const opt1 = document.createElement("option");
    opt1.value = node.node_id;
    opt1.textContent = `${node.node_name} (${node.zone})`;
    if (node.node_id === appState.selectedSource) opt1.selected = true;
    srcSelect.appendChild(opt1);

    const opt2 = document.createElement("option");
    opt2.value = node.node_id;
    opt2.textContent = `${node.node_name} (${node.zone})`;
    if (node.node_id === appState.selectedDestination) opt2.selected = true;
    dstSelect.appendChild(opt2);
  });
}

function renderVehicleGrid() {
  const container = document.getElementById("vehicle-selector-grid");
  container.innerHTML = "";

  appState.vehicles.forEach(v => {
    const btn = document.createElement("button");
    btn.className = `vehicle-btn ${v.id === appState.selectedVehicle ? "active" : ""}`;
    btn.dataset.vehId = v.id;
    btn.innerHTML = `
      <span class="veh-icon">${v.icon}</span>
      <span class="veh-name">${v.name.split(" (")[0]}</span>
    `;

    btn.addEventListener("click", () => {
      document.querySelectorAll(".vehicle-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      appState.selectedVehicle = v.id;
      triggerRouteOptimization();
    });

    container.appendChild(btn);
  });
}

function renderMapNodes() {
  nodeMarkersLayer.clearLayers();

  appState.nodes.forEach(node => {
    const isSource = node.node_id === appState.selectedSource;
    const isDest = node.node_id === appState.selectedDestination;

    let markerColor = "#3b82f6";
    let badgeText = "📍";
    if (isSource) { markerColor = "#10b981"; badgeText = "🟢"; }
    if (isDest) { markerColor = "#ef4444"; badgeText = "🔴"; }

    const customIcon = L.divIcon({
      className: "delhi-node-marker",
      html: `<div style="background-color:${markerColor}; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:2px solid #fff; font-size:10px; box-shadow:0 0 10px rgba(0,0,0,0.5);">${badgeText}</div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });

    const marker = L.marker([node.latitude, node.longitude], { icon: customIcon })
      .bindTooltip(`<strong>${node.node_name}</strong><br><span style="color:#9ca3af">${node.zone}</span>`, {
        direction: "top",
        className: "custom-leaflet-tooltip"
      });

    nodeMarkersLayer.addLayer(marker);
  });
}

// -------------------------------------------------------------
// Route Optimization Request & Rendering
// -------------------------------------------------------------
async function triggerRouteOptimization() {
  const btn = document.getElementById("btn-optimize");
  btn.innerHTML = `<span>⏳ Optimizing Routes...</span>`;
  btn.disabled = true;

  const payload = {
    source_id: appState.selectedSource,
    destination_id: appState.selectedDestination,
    hour_of_day: parseInt(appState.hourOfDay),
    day_of_week: parseInt(appState.dayOfWeek),
    weather_condition: appState.weatherCondition,
    vehicle_type: appState.selectedVehicle,
    custom_weights: {
      time: appState.weights.time / 100.0,
      fuel: appState.weights.fuel / 100.0,
      weather: appState.weights.weather / 100.0
    }
  };

  try {
    const res = await fetch(`${API_BASE}/api/route`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (data.status === "success") {
      appState.lastResult = data;
      renderRoutesOnMap(data.routes);
      renderComparisonCards(data.routes);
      renderSavingsHighlight(data.routes);
      renderStepItinerary(data.routes[appState.activeRouteKey === "all" ? "fastest" : appState.activeRouteKey] || data.routes.fastest);
      renderMapNodes();
      loadQueryHistory();
    } else {
      alert("Route optimization failed: " + (data.message || "Unknown error"));
    }
  } catch (err) {
    console.error("Route calculation error:", err);
  } finally {
    btn.innerHTML = `<span>🚀 Run Multi-Objective Optimization</span>`;
    btn.disabled = false;
  }
}

function renderRoutesOnMap(routes) {
  routePolylinesLayer.clearLayers();
  routeLayers = { fastest: null, eco: null, weather_safe: null };

  const allLatLongs = [];

  // Draw routes: Weather-Safe, Eco, then Fastest
  const drawOrder = ["weather_safe", "eco", "fastest"];

  drawOrder.forEach(key => {
    const route = routes[key];
    if (!route || !route.found) return;

    const latlngs = route.path_coordinates.map(pt => [pt.lat, pt.lng]);
    latlngs.forEach(ll => allLatLongs.push(ll));

    const style = ROUTE_COLORS[key];
    const polyline = L.polyline(latlngs, {
      color: style.color,
      weight: style.weight,
      opacity: style.opacity,
      lineJoin: "round"
    });

    polyline.bindTooltip(`<strong>${route.mode_title}</strong><br>Time: ${route.total_time_min} min | Fuel: ${route.total_fuel_units} ${route.fuel_unit_name}`, {
      sticky: true
    });

    polyline.on("click", () => {
      selectActiveRoute(key);
    });

    routeLayers[key] = polyline;
    routePolylinesLayer.addLayer(polyline);
  });

  // Check weather advisories
  const weatherAdvisories = routes.fastest?.weather_advisories || [];
  const mapBanner = document.getElementById("map-weather-banner");
  const bannerText = document.getElementById("map-weather-banner-text");

  if (weatherAdvisories.length > 0) {
    mapBanner.classList.remove("hidden");
    bannerText.textContent = weatherAdvisories.join(" • ");
  } else {
    mapBanner.classList.add("hidden");
  }

  // Adjust map bounds
  if (allLatLongs.length > 0) {
    map.fitBounds(L.latLngBounds(allLatLongs), { padding: [40, 40] });
  }

  applyRouteVisibility();
}

function applyRouteVisibility() {
  const activeKey = appState.activeRouteKey;

  Object.keys(routeLayers).forEach(key => {
    const layer = routeLayers[key];
    if (!layer) return;

    if (activeKey === "all" || activeKey === key) {
      layer.setStyle({
        opacity: activeKey === "all" ? 0.85 : 1.0,
        weight: activeKey === key ? 8 : (activeKey === "all" ? ROUTE_COLORS[key].weight : 3)
      });
      if (!routePolylinesLayer.hasLayer(layer)) {
        routePolylinesLayer.addLayer(layer);
      }
    } else {
      layer.setStyle({ opacity: 0.15, weight: 3 });
    }
  });
}

function selectActiveRoute(key) {
  appState.activeRouteKey = key;
  
  // Update tabs
  document.querySelectorAll(".pill-tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.routeKey === key);
  });

  // Update cards
  document.querySelectorAll(".route-card").forEach(card => {
    card.classList.toggle("selected", card.dataset.routeKey === key);
  });

  applyRouteVisibility();

  const selectedRoute = appState.lastResult?.routes[key === "all" ? "fastest" : key] || appState.lastResult?.routes.fastest;
  if (selectedRoute) {
    renderStepItinerary(selectedRoute);
  }
}

// -------------------------------------------------------------
// UI Renderers: Analytics & Itinerary
// -------------------------------------------------------------
function renderComparisonCards(routes) {
  const container = document.getElementById("comparison-cards-container");
  container.innerHTML = "";

  const order = ["fastest", "eco", "weather_safe"];

  order.forEach(key => {
    const r = routes[key];
    if (!r || !r.found) return;

    const isSelected = (appState.activeRouteKey === key) || (appState.activeRouteKey === "all" && key === "fastest");
    const card = document.createElement("div");
    card.className = `route-card ${key} ${isSelected ? "selected" : ""}`;
    card.dataset.routeKey = key;

    card.innerHTML = `
      <div class="route-card-header">
        <div class="route-title-group">
          <span class="dot ${key}"></span>
          <span class="route-name">${r.mode_title}</span>
        </div>
        <span class="route-badge">${r.mode_badge}</span>
      </div>

      <div class="route-metrics-grid">
        <div class="metric-item">
          <span class="metric-lbl">ETA (Travel Time)</span>
          <span class="metric-val highlight-time">${r.total_time_min} min</span>
        </div>
        <div class="metric-item">
          <span class="metric-lbl">Fuel / Energy</span>
          <span class="metric-val highlight-eco">${r.total_fuel_units} ${r.fuel_unit_name.slice(0, 3)}</span>
        </div>
        <div class="metric-item">
          <span class="metric-lbl">Safety Score</span>
          <span class="metric-val highlight-safety">${r.weather_safety_score}%</span>
        </div>
      </div>

      <div class="route-metrics-grid" style="border-top:none; margin-top:4px; padding-top:0;">
        <div class="metric-item">
          <span class="metric-lbl">Distance</span>
          <span class="metric-val">${r.total_distance_km} km</span>
        </div>
        <div class="metric-item">
          <span class="metric-lbl">CO₂ Footprint</span>
          <span class="metric-val">${r.total_co2_kg} kg</span>
        </div>
        <div class="metric-item">
          <span class="metric-lbl">Est. Fuel Cost</span>
          <span class="metric-val">₹${r.total_cost_inr}</span>
        </div>
      </div>
    `;

    card.addEventListener("click", () => {
      selectActiveRoute(key);
    });

    container.appendChild(card);
  });
}

function renderSavingsHighlight(routes) {
  const savingsCard = document.getElementById("savings-card");
  const savingsDesc = document.getElementById("savings-desc");

  const fastest = routes.fastest;
  const eco = routes.eco;

  if (fastest && eco && fastest.total_fuel_units > 0) {
    const fuelDiff = fastest.total_fuel_units - eco.total_fuel_units;
    const pctSaved = Math.max(0, (fuelDiff / fastest.total_fuel_units) * 100).toFixed(1);
    const co2Saved = Math.max(0, fastest.total_co2_kg - eco.total_co2_kg).toFixed(2);
    const moneySaved = Math.max(0, fastest.total_cost_inr - eco.total_cost_inr).toFixed(1);

    if (fuelDiff > 0.05) {
      savingsCard.classList.remove("hidden");
      savingsDesc.innerHTML = `🌿 <strong>Eco-Friendly route saves ${pctSaved}% fuel</strong> (${fuelDiff.toFixed(2)} ${fastest.fuel_unit_name}) and <strong>${co2Saved} kg CO₂</strong> (₹${moneySaved} cost reduction) compared to the fastest speed path.`;
    } else {
      savingsCard.classList.remove("hidden");
      savingsDesc.innerHTML = `⚡ The fastest route is already highly energy-efficient for this origin-destination corridor!`;
    }
  } else {
    savingsCard.classList.add("hidden");
  }
}

function renderStepItinerary(route) {
  const container = document.getElementById("route-steps-list");
  const routeBadge = document.getElementById("selected-route-name");

  if (!route || !route.steps) {
    container.innerHTML = `<div class="empty-state">No route selected.</div>`;
    return;
  }

  routeBadge.textContent = route.mode_title;
  container.innerHTML = "";

  route.steps.forEach((step, idx) => {
    const row = document.createElement("div");
    row.className = "step-row";
    row.innerHTML = `
      <div class="step-left">
        <span class="step-road">${idx + 1}. ${step.road_name}</span>
        <span class="step-nodes">${step.from_name.split(" (")[0]} ➔ ${step.to_name.split(" (")[0]} (${step.road_type})</span>
      </div>
      <div class="step-right">
        <div><strong>${step.distance_km} km</strong></div>
        <div style="color:#9ca3af; font-size:0.68rem;">~${step.predicted_time_min} min</div>
      </div>
    `;
    container.appendChild(row);
  });
}

async function loadQueryHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/history?limit=6`);
    const data = await res.json();
    const container = document.getElementById("history-items-list");
    container.innerHTML = "";

    if (!data.history || data.history.length === 0) {
      container.innerHTML = `<div class="empty-state">No past queries in SQLite.</div>`;
      return;
    }

    data.history.forEach(item => {
      const row = document.createElement("div");
      row.className = "history-item";
      row.innerHTML = `
        <div>
          <span class="hist-route">${item.source_id.replace("NODE_", "")} ➔ ${item.destination_id.replace("NODE_", "")}</span>
          <span style="font-size:0.65rem; color:#6b7280; display:block;">${item.vehicle_type.replace("_", " ")} • ${item.weather_condition}</span>
        </div>
        <div style="text-align:right;">
          <span style="font-family:'JetBrains Mono'; font-weight:700; color:#38bdf8;">${item.fastest_time_min}m</span>
          <span style="font-size:0.65rem; color:#34d399; display:block;">-${item.eco_fuel_saved_percent}% fuel</span>
        </div>
      `;
      container.appendChild(row);
    });
  } catch (err) {
    console.error("Error fetching history:", err);
  }
}

// -------------------------------------------------------------
// Event Handlers
// -------------------------------------------------------------
function setupEventListeners() {
  document.getElementById("select-source").addEventListener("change", e => {
    appState.selectedSource = e.target.value;
    triggerRouteOptimization();
  });

  document.getElementById("select-destination").addEventListener("change", e => {
    appState.selectedDestination = e.target.value;
    triggerRouteOptimization();
  });

  document.getElementById("btn-swap-nodes").addEventListener("click", () => {
    const tmp = appState.selectedSource;
    appState.selectedSource = appState.selectedDestination;
    appState.selectedDestination = tmp;
    populateNodeDropdowns();
    triggerRouteOptimization();
  });

  // Weather selector
  document.getElementById("select-weather").addEventListener("change", e => {
    appState.weatherCondition = e.target.value;
    
    // Update navbar weather badge
    const weatherIconMap = {
      Clear: "☀️", Light_Rain: "🌦️", Heavy_Rain: "🌧️",
      Dense_Fog: "🌫️", Extreme_Heat: "🔥", Storm: "⛈️"
    };
    document.getElementById("nav-weather-icon").textContent = weatherIconMap[appState.weatherCondition] || "☀️";
    document.getElementById("nav-weather-text").textContent = e.target.options[e.target.selectedIndex].text.split(" (")[0];
    
    triggerRouteOptimization();
  });

  // Departure hour slider
  const sliderHour = document.getElementById("slider-hour");
  const valHour = document.getElementById("val-hour");
  sliderHour.addEventListener("input", e => {
    const h = parseInt(e.target.value);
    appState.hourOfDay = h;
    const period = h >= 12 ? "PM" : "AM";
    const displayH = h % 12 === 0 ? 12 : h % 12;
    const isRush = (h >= 8 && h <= 10) || (h >= 17 && h <= 20);
    valHour.textContent = `${displayH.toString().padStart(2, '0')}:00 ${period} ${isRush ? "(Peak Rush)" : "(Normal)"}`;
  });
  sliderHour.addEventListener("change", () => triggerRouteOptimization());

  document.getElementById("select-day").addEventListener("change", e => {
    appState.dayOfWeek = parseInt(e.target.value);
    triggerRouteOptimization();
  });

  // Weight sliders
  ["time", "fuel", "weather"].forEach(dim => {
    const slider = document.getElementById(`slider-w-${dim}`);
    const display = document.getElementById(`val-w-${dim}`);
    slider.addEventListener("input", e => {
      appState.weights[dim] = parseInt(e.target.value);
      display.textContent = `${e.target.value}%`;
    });
    slider.addEventListener("change", () => triggerRouteOptimization());
  });

  document.getElementById("btn-reset-weights").addEventListener("click", () => {
    appState.weights = { time: 50, fuel: 30, weather: 20 };
    document.getElementById("slider-w-time").value = 50;
    document.getElementById("val-w-time").textContent = "50%";
    document.getElementById("slider-w-fuel").value = 30;
    document.getElementById("val-w-fuel").textContent = "30%";
    document.getElementById("slider-w-weather").value = 20;
    document.getElementById("val-w-weather").textContent = "20%";
    triggerRouteOptimization();
  });

  document.getElementById("btn-optimize").addEventListener("click", triggerRouteOptimization);

  // Route tab pills
  document.querySelectorAll(".pill-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      selectActiveRoute(tab.dataset.routeKey);
    });
  });

  document.getElementById("btn-recenter").addEventListener("click", () => {
    map.setView([28.6000, 77.2000], 11);
  });

  document.getElementById("btn-refresh-history").addEventListener("click", loadQueryHistory);
}

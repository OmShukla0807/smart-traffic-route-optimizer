/**
 * Path Pilot - Client Application
 * Next-Gen Cyber-Cockpit, Multi-Objective Routing (Fastest, Eco, Clean Air AQI, Weather-Safe),
 * Live Incident Simulator, & Interactive Slide Deck Controller
 */

const API_BASE = window.location.origin;

// Global Application State
let appState = {
  currentView: "planner", // "planner" or "results"
  nodes: [],
  roads: [],
  vehicles: [
    { id: "Petrol_Sedan", name: "Petrol Sedan", icon: "🚗", fuel_unit: "Liters", efficiency_desc: "Standard fuel consumption with stop-and-go penalty." },
    { id: "Diesel_SUV", name: "Diesel SUV", icon: "🚙", fuel_unit: "Liters", efficiency_desc: "High torque, heavier gradient fuel penalty." },
    { id: "Electric_Vehicle", name: "Electric Vehicle", icon: "⚡", fuel_unit: "kWh", efficiency_desc: "High urban efficiency, zero direct tailpipe emissions." },
    { id: "Heavy_Truck", name: "Commercial Heavy Freight Truck", icon: "🚛", fuel_unit: "Liters", efficiency_desc: "High payload, lower top speeds on arterial roads." },
    { id: "Two_Wheeler", name: "Two-Wheeler / Motorbike", icon: "🏍️", fuel_unit: "Liters", efficiency_desc: "Nimble in congestion, higher vulnerability to weather." }
  ],
  weatherPresets: [],
  selectedSource: "NODE_CP",
  selectedDestination: "NODE_CYBER",
  selectedVehicle: "Petrol_Sedan",
  weatherCondition: "Clear",
  hourOfDay: 9,
  dayOfWeek: 1,
  customWeights: { time: 0.25, fuel: 0.25, aqi: 0.25, weather: 0.25 },
  useCustomWeights: false,
  activeRouteKey: "fastest", // "fastest", "eco", "clean_air", "weather_safe", "all"
  lastResult: null,
  currentMapLayer: "roadmap",
  currentSlide: 1,
  totalSlides: 8
};

// Leaflet Map State
let leafletMap = null;
let currentTileLayer = null;
let nodeMarkersLayer = null;
let routePolylinesLayer = null;
let routeLayers = { fastest: null, eco: null, clean_air: null, weather_safe: null };

// Tile Providers for Leaflet & Google Tiles
const MAP_TILE_PROVIDERS = {
  roadmap: {
    url: "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
    options: { attribution: '&copy; Google Maps', maxZoom: 20 }
  },
  satellite: {
    url: "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    options: { attribution: '&copy; Google Maps', maxZoom: 20 }
  },
  hybrid: {
    url: "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    options: { attribution: '&copy; Google Maps', maxZoom: 20 }
  },
  terrain: {
    url: "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}",
    options: { attribution: '&copy; Google Maps', maxZoom: 20 }
  },
  dark: {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    options: { attribution: '&copy; CARTO &copy; OpenStreetMap', maxZoom: 19 }
  }
};

const ROUTE_STYLES = {
  fastest: { color: "#00f0ff", weight: 6, opacity: 0.95, dashArray: null },
  eco: { color: "#10b981", weight: 5, opacity: 0.9, dashArray: "8, 6" },
  clean_air: { color: "#a855f7", weight: 5, opacity: 0.9, dashArray: "6, 4" },
  weather_safe: { color: "#f59e0b", weight: 5, opacity: 0.9, dashArray: "4, 6" }
};

// -------------------------------------------------------------
// DOM Ready Initialization
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  renderPlannerVehicles();
  setupPlannerEventListeners();
  setupResultsEventListeners();
  setupIncidentModalListeners();
  setupPresentationDeckListeners();

  await loadInitialMetadata();
});

// -------------------------------------------------------------
// Metadata Loader
// -------------------------------------------------------------
async function loadInitialMetadata() {
  try {
    const [nodesRes, roadsRes, vehiclesRes, weatherRes] = await Promise.all([
      fetch(`${API_BASE}/api/nodes`).then(r => r.json()),
      fetch(`${API_BASE}/api/roads`).then(r => r.json()),
      fetch(`${API_BASE}/api/vehicles`).then(r => r.json()),
      fetch(`${API_BASE}/api/weather-presets`).then(r => r.json())
    ]);

    appState.nodes = nodesRes.nodes || [];
    appState.roads = roadsRes.roads || [];
    appState.vehicles = vehiclesRes.vehicles || [];
    appState.weatherPresets = weatherRes.conditions || [];

    updatePlannerInputs();
    renderPlannerVehicles();
    populateIncidentRoadDropdown();
  } catch (err) {
    console.error("Error loading initial metadata:", err);
  }
}

function getNodeById(nodeId) {
  return appState.nodes.find(n => n.node_id === nodeId) || null;
}

function updatePlannerInputs() {
  const srcNode = getNodeById(appState.selectedSource);
  const dstNode = getNodeById(appState.selectedDestination);

  const inputSrc = document.getElementById("planner-search-source");
  const inputDst = document.getElementById("planner-search-dest");

  if (inputSrc && srcNode) {
    inputSrc.value = `${srcNode.node_name} (${srcNode.zone})`;
  }
  if (inputDst && dstNode) {
    inputDst.value = `${dstNode.node_name} (${dstNode.zone})`;
  }
}

function renderPlannerVehicles() {
  const container = document.getElementById("planner-vehicle-grid");
  if (!container || !appState.vehicles || appState.vehicles.length === 0) return;

  container.innerHTML = "";
  appState.vehicles.forEach(v => {
    const card = document.createElement("div");
    const isActive = appState.selectedVehicle === v.id;
    card.className = `vehicle-card-pill ${isActive ? "active" : ""}`;
    card.dataset.id = v.id;
    card.innerHTML = `
      <div class="veh-header">
        <span class="veh-icon">${v.icon}</span>
        <span class="veh-unit-tag">${v.fuel_unit || "Liters"}</span>
      </div>
      <span class="veh-name">${v.name.split(" (")[0]}</span>
      <span class="veh-desc">${v.efficiency_desc || ""}</span>
    `;

    card.addEventListener("click", () => {
      document.querySelectorAll(".vehicle-card-pill").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      appState.selectedVehicle = v.id;
    });

    container.appendChild(card);
  });
}

function populateIncidentRoadDropdown() {
  const select = document.getElementById("incident-road-select");
  if (!select || !appState.roads) return;

  select.innerHTML = "";
  appState.roads.forEach(r => {
    const opt = document.createElement("option");
    opt.value = r.road_id;
    opt.textContent = `[${r.road_id}] ${r.road_name} (${r.from_node} ➔ ${r.to_node}, ${r.distance_km}km, AQI:${r.aqi_index})`;
    select.appendChild(opt);
  });
}

// -------------------------------------------------------------
// Planner Event Listeners
// -------------------------------------------------------------
function setupPlannerEventListeners() {
  // Autocomplete search for origin & destination
  const setupAutocomplete = (inputId, dropdownId, stateKey) => {
    const input = document.getElementById(inputId);
    const dropdown = document.getElementById(dropdownId);
    if (!input || !dropdown) return;

    input.addEventListener("focus", () => showDropdown(input, dropdown, stateKey));
    input.addEventListener("input", () => showDropdown(input, dropdown, stateKey));

    document.addEventListener("click", (e) => {
      if (!input.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.add("hidden");
      }
    });
  };

  const showDropdown = (input, dropdown, stateKey) => {
    const query = input.value.toLowerCase().trim();
    dropdown.innerHTML = "";

    const filtered = appState.nodes.filter(n =>
      n.node_name.toLowerCase().includes(query) ||
      n.zone.toLowerCase().includes(query) ||
      (n.landmark && n.landmark.toLowerCase().includes(query))
    );

    if (filtered.length === 0) {
      dropdown.innerHTML = `<div class="dropdown-item empty">No transit hubs found</div>`;
    } else {
      filtered.forEach(node => {
        const item = document.createElement("div");
        item.className = "dropdown-item";
        item.innerHTML = `
          <span class="hub-name">${node.node_name}</span>
          <span class="hub-zone">${node.zone} • ${node.landmark || 'Metro Hub'}</span>
        `;
        item.addEventListener("click", () => {
          appState[stateKey] = node.node_id;
          input.value = `${node.node_name} (${node.zone})`;
          dropdown.classList.add("hidden");
        });
        dropdown.appendChild(item);
      });
    }
    dropdown.classList.remove("hidden");
  };

  setupAutocomplete("planner-search-source", "planner-src-dropdown", "selectedSource");
  setupAutocomplete("planner-search-dest", "planner-dst-dropdown", "selectedDestination");

  // Clear buttons
  document.getElementById("btn-planner-clear-src")?.addEventListener("click", () => {
    const input = document.getElementById("planner-search-source");
    if (input) { input.value = ""; input.focus(); }
  });
  document.getElementById("btn-planner-clear-dst")?.addEventListener("click", () => {
    const input = document.getElementById("planner-search-dest");
    if (input) { input.value = ""; input.focus(); }
  });

  // Swap endpoints
  document.getElementById("btn-planner-swap")?.addEventListener("click", () => {
    const temp = appState.selectedSource;
    appState.selectedSource = appState.selectedDestination;
    appState.selectedDestination = temp;
    updatePlannerInputs();
  });

  // Popular Trip Quick Chips
  document.querySelectorAll(".chip-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      appState.selectedSource = btn.dataset.src;
      appState.selectedDestination = btn.dataset.dst;
      updatePlannerInputs();
    });
  });

  // Departure Time Slider
  const hourSlider = document.getElementById("planner-hour-slider");
  const timeDisplay = document.getElementById("planner-time-display");
  if (hourSlider && timeDisplay) {
    hourSlider.addEventListener("input", (e) => {
      const h = parseInt(e.target.value, 10);
      appState.hourOfDay = h;

      const period = h >= 12 ? "PM" : "AM";
      const displayHour = h % 12 === 0 ? 12 : h % 12;
      const formatted = `${String(displayHour).padStart(2, "0")}:00 ${period}`;

      let rushTag = "";
      if ((h >= 8 && h <= 11) || (h >= 17 && h <= 21)) {
        rushTag = " (Peak Rush Hour)";
      } else if (h >= 0 && h <= 5) {
        rushTag = " (Off-Peak Night)";
      }
      timeDisplay.textContent = `${formatted}${rushTag}`;
    });
  }

  // Weather selector
  const weatherSelect = document.getElementById("planner-weather-select");
  const hazardPill = document.getElementById("weather-hazard-alert");
  const hazardDesc = document.getElementById("weather-hazard-desc");
  if (weatherSelect) {
    weatherSelect.addEventListener("change", (e) => {
      appState.weatherCondition = e.target.value;
      const preset = appState.weatherPresets.find(p => p.id === e.target.value);
      if (preset && hazardPill && hazardDesc) {
        hazardDesc.textContent = preset.description;
        hazardPill.className = `weather-mini-pill ${preset.hazard_level === 'Critical' ? 'alert' : preset.hazard_level === 'High' ? 'alert' : preset.hazard_level === 'Moderate' ? 'warn' : 'clear'}`;
      }
    });
  }

  // Submit Run AI Button
  document.getElementById("btn-find-routes")?.addEventListener("click", () => {
    executeRouteCalculation();
  });
}

// -------------------------------------------------------------
// Route Optimization Request & Results Renderer
// -------------------------------------------------------------
async function executeRouteCalculation() {
  if (appState.selectedSource === appState.selectedDestination) {
    alert("Please choose different starting and destination locations.");
    return;
  }

  const btn = document.getElementById("btn-find-routes");
  if (btn) btn.disabled = true;

  const payload = {
    source_id: appState.selectedSource,
    destination_id: appState.selectedDestination,
    hour_of_day: appState.hourOfDay,
    day_of_week: appState.dayOfWeek,
    weather_condition: appState.weatherCondition,
    vehicle_type: appState.selectedVehicle,
    custom_weights: appState.useCustomWeights ? appState.customWeights : null
  };

  try {
    const res = await fetch(`${API_BASE}/api/route`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to calculate route.");
    }

    const data = await res.json();
    appState.lastResult = data;

    // Switch View to Results Page
    document.getElementById("view-planner").classList.remove("active");
    document.getElementById("view-results").classList.add("active");
    appState.currentView = "results";

    renderResultsCockpit(data);
  } catch (e) {
    alert(`Error: ${e.message}`);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function renderResultsCockpit(data) {
  // Update Top Navigation Summary
  const src = data.source;
  const dst = data.destination;
  document.getElementById("res-start-name").textContent = src.name;
  document.getElementById("res-end-name").textContent = dst.name;

  const veh = appState.vehicles.find(v => v.id === appState.selectedVehicle);
  const vehIcon = veh ? veh.icon : "🚗";
  const h = appState.hourOfDay;
  const period = h >= 12 ? "PM" : "AM";
  const displayHour = h % 12 === 0 ? 12 : h % 12;
  const timeStr = `${String(displayHour).padStart(2, "0")}:00 ${period}`;

  document.getElementById("res-trip-meta").textContent =
    `${vehIcon} ${veh ? veh.name.split(" (")[0] : "Petrol"} • ${appState.weatherCondition} • ${timeStr}`;

  // Update Route Pill Time Badges
  const r = data.routes;
  if (r.fastest && r.fastest.found) {
    document.getElementById("pill-fastest-time").textContent = `${r.fastest.total_time_min}m`;
  }
  if (r.eco && r.eco.found) {
    document.getElementById("pill-eco-time").textContent = `${r.eco.total_time_min}m`;
  }
  if (r.clean_air && r.clean_air.found) {
    document.getElementById("pill-clean-air-time").textContent = `${r.clean_air.total_time_min}m`;
  }
  if (r.weather_safe && r.weather_safe.found) {
    document.getElementById("pill-weather-time").textContent = `${r.weather_safe.total_time_min}m`;
  }

  // Initialize or Re-center Map
  initOrUpdateMap(data);

  // Update Floating Bottom HUD
  updateBottomTelemetryHUD(appState.activeRouteKey);

  // Update Details Drawer Content
  populateDetailsDrawer(data);
}

// -------------------------------------------------------------
// Leaflet Map Initialization & Route Drawing
// -------------------------------------------------------------
function initOrUpdateMap(data) {
  const mapContainer = document.getElementById("results-map");
  if (!mapContainer) return;

  if (!leafletMap) {
    leafletMap = L.map("results-map", {
      zoomControl: false,
      attributionControl: false
    }).setView([28.6139, 77.2090], 11);

    L.control.zoom({ position: "bottomright" }).addTo(leafletMap);

    // Add Base Tile Layer
    const provider = MAP_TILE_PROVIDERS[appState.currentMapLayer] || MAP_TILE_PROVIDERS.roadmap;
    currentTileLayer = L.tileLayer(provider.url, provider.options).addTo(leafletMap);

    // Layer groups for markers & polylines
    nodeMarkersLayer = L.layerGroup().addTo(leafletMap);
    routePolylinesLayer = L.layerGroup().addTo(leafletMap);
  }

  // Clear previous layers
  nodeMarkersLayer.clearLayers();
  routePolylinesLayer.clearLayers();

  const srcNode = data.source;
  const dstNode = data.destination;

  // Add Glowing Start Marker
  const startIcon = L.divIcon({
    className: "custom-hub-marker start",
    html: "A",
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  });
  L.marker([srcNode.lat, srcNode.lng], { icon: startIcon })
    .bindPopup(`<strong>Origin:</strong> ${srcNode.name}`)
    .addTo(nodeMarkersLayer);

  // Add Glowing Dest Marker
  const destIcon = L.divIcon({
    className: "custom-hub-marker dest",
    html: "B",
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  });
  L.marker([dstNode.lat, dstNode.lng], { icon: destIcon })
    .bindPopup(`<strong>Destination:</strong> ${dstNode.name}`)
    .addTo(nodeMarkersLayer);

  // Plot All 4 Routes
  routeLayers = { fastest: null, eco: null, clean_air: null, weather_safe: null };
  const allBounds = L.latLngBounds([[srcNode.lat, srcNode.lng], [dstNode.lat, dstNode.lng]]);

  const routeKeys = ["weather_safe", "clean_air", "eco", "fastest"]; // draw order: fastest on top
  routeKeys.forEach(key => {
    const route = data.routes[key];
    if (route && route.found && route.path_coordinates && route.path_coordinates.length > 0) {
      const latlngs = route.path_coordinates.map(p => [p.lat, p.lng]);
      latlngs.forEach(pt => allBounds.extend(pt));

      const style = ROUTE_STYLES[key] || ROUTE_STYLES.fastest;
      const poly = L.polyline(latlngs, {
        color: style.color,
        weight: style.weight,
        opacity: style.opacity,
        dashArray: style.dashArray,
        lineCap: "round",
        lineJoin: "round"
      }).addTo(routePolylinesLayer);

      poly.bindPopup(`
        <div style="font-family:sans-serif; font-size:12px;">
          <strong style="color:${style.color};">${route.mode_title}</strong><br>
          🛣️ Corridor: <b>${route.route_summary_label}</b><br>
          ⏱️ ETA: <b>${route.total_time_min} min</b><br>
          📏 Distance: <b>${route.total_distance_km} km</b><br>
          ⛽ Fuel/Energy: <b>${route.total_fuel_units} ${route.fuel_unit_name}</b><br>
          🍃 AQI: <b>${route.avg_aqi_index} (${route.pollution_level})</b><br>
          🛡️ Safety: <b>${route.weather_safety_score}%</b>
        </div>
      `);

      routeLayers[key] = poly;
    }
  });

  leafletMap.fitBounds(allBounds, { padding: [60, 60], maxZoom: 14 });
  leafletMap.invalidateSize();
}

function updateBottomTelemetryHUD(routeKey) {
  if (!appState.lastResult) return;
  const rData = appState.lastResult.routes;
  const activeRoute = (routeKey === "all" || !rData[routeKey] || !rData[routeKey].found) ? rData.fastest : rData[routeKey];

  if (!activeRoute) return;

  document.getElementById("quick-mode-title").textContent = activeRoute.mode_title;
  document.getElementById("quick-corridor-label").textContent = activeRoute.route_summary_label;
  const engineTag = document.getElementById("quick-engine-tag");
  if (engineTag) engineTag.textContent = activeRoute.engine_used || "⚡ C++ Dijkstra";

  document.getElementById("quick-eta").textContent = `${activeRoute.total_time_min} min`;
  document.getElementById("quick-dist").textContent = `${activeRoute.total_distance_km} km`;
  document.getElementById("quick-fuel").textContent = `${activeRoute.total_fuel_units} ${activeRoute.fuel_unit_name}`;
  document.getElementById("quick-co2").textContent = `${activeRoute.total_co2_kg} kg CO₂`;
  document.getElementById("quick-aqi").textContent = `${activeRoute.avg_aqi_index} (${activeRoute.pollution_level.split(" (")[0]})`;
  document.getElementById("quick-safety").textContent = `${activeRoute.weather_safety_score}%`;

  // Highlight polylines based on selection
  Object.keys(routeLayers).forEach(k => {
    const poly = routeLayers[k];
    if (poly) {
      if (routeKey === "all" || routeKey === k) {
        poly.setStyle({ opacity: 0.95, weight: (routeKey === k ? 8 : 5) });
      } else {
        poly.setStyle({ opacity: 0.25, weight: 3 });
      }
    }
  });
}

function populateDetailsDrawer(data) {
  const compGrid = document.getElementById("drawer-comparison-cards");
  if (compGrid) {
    compGrid.innerHTML = "";
    ["fastest", "eco", "clean_air", "weather_safe"].forEach(k => {
      const r = data.routes[k];
      if (!r || !r.found) return;

      const aqiClass = r.avg_aqi_index <= 100 ? "aqi-good" : (r.avg_aqi_index <= 200 ? "aqi-mod" : (r.avg_aqi_index <= 300 ? "aqi-poor" : "aqi-hazard"));

      const card = document.createElement("div");
      card.className = `drawer-route-card ${appState.activeRouteKey === k ? "active" : ""}`;
      card.innerHTML = `
        <div class="d-card-header">
          <span class="d-card-title">${r.mode_title}</span>
          <span class="drawer-badge-pill">${r.mode_badge}</span>
        </div>
        <div style="font-size:0.8rem; font-weight:600; color:#38bdf8; margin: 4px 0 8px;">
          ${r.route_summary_label}
        </div>
        <div class="d-card-metrics">
          <div class="d-m-box">
            <span class="d-m-label">ETA</span>
            <span class="d-m-val" style="color:var(--cyan-core);">${r.total_time_min}m</span>
          </div>
          <div class="d-m-box">
            <span class="d-m-label">Distance</span>
            <span class="d-m-val">${r.total_distance_km}km</span>
          </div>
          <div class="d-m-box">
            <span class="d-m-label">Fuel</span>
            <span class="d-m-val">${r.total_fuel_units} ${r.fuel_unit_name}</span>
          </div>
          <div class="d-m-box">
            <span class="d-m-label">AQI</span>
            <span class="d-m-val"><span class="aqi-badge ${aqiClass}">${r.avg_aqi_index}</span></span>
          </div>
        </div>
      `;

      card.addEventListener("click", () => {
        document.querySelectorAll(".drawer-route-card").forEach(c => c.classList.remove("active"));
        card.classList.add("active");
        appState.activeRouteKey = k;
        updateBottomTelemetryHUD(k);
        populateDrawerSteps(data.routes[k]);
      });

      compGrid.appendChild(card);
    });
  }

  // Savings box
  const fastFuel = data.routes.fastest?.total_fuel_units || 1.0;
  const ecoFuel = data.routes.eco?.total_fuel_units || fastFuel;
  const savingsPct = fastFuel > 0 ? Math.max(0, ((fastFuel - ecoFuel) / fastFuel * 100).toFixed(1)) : 0;
  const co2Saved = Math.max(0, ((data.routes.fastest?.total_co2_kg || 0) - (data.routes.eco?.total_co2_kg || 0)).toFixed(2));

  const savingsBox = document.getElementById("drawer-savings-box");
  const savingsText = document.getElementById("drawer-savings-text");
  if (savingsBox && savingsText) {
    if (savingsPct > 0) {
      savingsText.textContent = `Eco-friendly route saves ${savingsPct}% fuel and abates ${co2Saved} kg of carbon emissions.`;
      savingsBox.classList.remove("hidden");
    } else {
      savingsBox.classList.add("hidden");
    }
  }

  populateDrawerSteps(data.routes.fastest);
  loadRecentHistory();
}

function populateDrawerSteps(route) {
  const list = document.getElementById("drawer-steps-list");
  const label = document.getElementById("drawer-active-route-label");
  if (!list || !route) return;

  if (label) label.textContent = `${route.mode_title} (${route.route_summary_label})`;
  list.innerHTML = "";

  if (!route.steps || route.steps.length === 0) {
    list.innerHTML = `<div style="font-size:0.8rem; color:var(--text-muted);">Direct node connection.</div>`;
    return;
  }

  route.steps.forEach((step, idx) => {
    const aqiClass = step.aqi_index <= 100 ? "aqi-good" : (step.aqi_index <= 200 ? "aqi-mod" : (step.aqi_index <= 300 ? "aqi-poor" : "aqi-hazard"));

    const item = document.createElement("div");
    item.className = "step-item";
    item.innerHTML = `
      <span class="step-index-badge">${idx + 1}</span>
      <div class="step-content">
        <span class="step-road-name">${step.road_name} (${step.road_type})</span>
        <span class="step-nodes">${step.from_name} ➔ ${step.to_name}</span>
        <div class="step-meta-row">
          <span>📏 ${step.distance_km} km</span>
          <span>⏱️ ${step.predicted_time_min} min</span>
          <span>⚡ Limit: ${step.speed_limit_kmh} km/h</span>
          <span><span class="aqi-badge ${aqiClass}">AQI ${step.aqi_index}</span></span>
        </div>
      </div>
    `;
    list.appendChild(item);
  });
}

async function loadRecentHistory() {
  const historyList = document.getElementById("drawer-history-list");
  if (!historyList) return;

  try {
    const res = await fetch(`${API_BASE}/api/history?limit=6`);
    const data = await res.json();
    const history = data.history || [];

    historyList.innerHTML = "";
    if (history.length === 0) {
      historyList.innerHTML = `<div style="font-size:0.8rem; color:var(--text-muted);">No queries logged yet.</div>`;
      return;
    }

    history.forEach(item => {
      const row = document.createElement("div");
      row.className = "history-item";
      row.innerHTML = `
        <div class="h-route-title">${item.source_name} ➔ ${item.destination_name}</div>
        <div class="h-meta-tags">
          <span>${item.vehicle_type}</span>
          <span>${item.weather_condition}</span>
          <span>ETA: ${item.fastest_time_min}m</span>
          <span style="color:var(--emerald-core);">Eco Save: ${item.eco_fuel_saved_percent}%</span>
        </div>
      `;
      historyList.appendChild(row);
    });
  } catch (err) {
    console.error("Error loading history:", err);
  }
}

// -------------------------------------------------------------
// Results View Navigation Listeners
// -------------------------------------------------------------
function setupResultsEventListeners() {
  // Back to Planner
  document.getElementById("btn-back-to-planner")?.addEventListener("click", () => {
    document.getElementById("view-results").classList.remove("active");
    document.getElementById("view-planner").classList.add("active");
    appState.currentView = "planner";
  });

  // Recenter map
  document.getElementById("btn-results-recenter")?.addEventListener("click", () => {
    if (leafletMap && appState.lastResult) {
      initOrUpdateMap(appState.lastResult);
    }
  });

  // Route Tabs switcher
  document.querySelectorAll(".map-route-pill").forEach(pill => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".map-route-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");

      const rKey = pill.dataset.route;
      appState.activeRouteKey = rKey;
      updateBottomTelemetryHUD(rKey);

      if (appState.lastResult) {
        const targetRoute = rKey === "all" ? appState.lastResult.routes.fastest : appState.lastResult.routes[rKey];
        populateDrawerSteps(targetRoute);
      }
    });
  });

  // Map Tile Style Selector
  const layerSelect = document.getElementById("select-map-layer");
  if (layerSelect) {
    layerSelect.addEventListener("change", (e) => {
      const selected = e.target.value;
      appState.currentMapLayer = selected;
      if (leafletMap && currentTileLayer) {
        leafletMap.removeLayer(currentTileLayer);
        const provider = MAP_TILE_PROVIDERS[selected] || MAP_TILE_PROVIDERS.roadmap;
        currentTileLayer = L.tileLayer(provider.url, provider.options).addTo(leafletMap);
        currentTileLayer.bringToBack();
      }
    });
  }

  // Drawer Toggle
  const toggleDrawerBtn = document.getElementById("btn-toggle-details");
  const closeDrawerBtn = document.getElementById("btn-close-drawer");
  const quickViewBtn = document.getElementById("btn-quick-view-steps");
  const drawer = document.getElementById("details-drawer");

  const openDrawer = () => drawer?.classList.remove("hidden");
  const closeDrawer = () => drawer?.classList.add("hidden");

  toggleDrawerBtn?.addEventListener("click", () => {
    if (drawer?.classList.contains("hidden")) openDrawer();
    else closeDrawer();
  });
  closeDrawerBtn?.addEventListener("click", closeDrawer);
  quickViewBtn?.addEventListener("click", openDrawer);

  document.getElementById("btn-drawer-refresh-history")?.addEventListener("click", loadRecentHistory);
}

// -------------------------------------------------------------
// Live Incident Simulation Modal Listeners
// -------------------------------------------------------------
function setupIncidentModalListeners() {
  const modal = document.getElementById("incident-modal");
  const openBtn = document.getElementById("btn-open-incident-modal");
  const closeBtn = document.getElementById("btn-close-incident-modal");
  const applyBtn = document.getElementById("btn-apply-incident");
  const clearBtn = document.getElementById("btn-clear-incidents");

  openBtn?.addEventListener("click", () => modal?.classList.remove("hidden"));
  closeBtn?.addEventListener("click", () => modal?.classList.add("hidden"));

  // Apply Incident
  applyBtn?.addEventListener("click", async () => {
    const roadId = document.getElementById("incident-road-select").value;
    const incType = document.getElementById("incident-type-select").value;
    const severity = document.getElementById("incident-severity-select").value;

    const payload = {
      road_id: roadId,
      incident_type: incType,
      severity: severity,
      description: `Simulated ${severity} ${incType} roadblock.`,
      is_active: true
    };

    try {
      const res = await fetch(`${API_BASE}/api/simulate-incident`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      modal?.classList.add("hidden");

      // Show Weather & Incident Alert Banner on Map
      const banner = document.getElementById("results-weather-banner");
      const bannerText = document.getElementById("results-weather-banner-text");
      if (banner && bannerText) {
        bannerText.textContent = `🚨 ACTIVE INCIDENT: Road ${roadId} is blocked (${severity} ${incType}). C++ Engine recalculated optimal bypass!`;
        banner.classList.remove("hidden");
      }

      // Re-run optimization immediately with updated road state
      if (appState.currentView === "results") {
        await executeRouteCalculation();
      }
    } catch (e) {
      alert(`Failed to apply incident: ${e.message}`);
    }
  });

  // Clear Incidents
  clearBtn?.addEventListener("click", async () => {
    try {
      await fetch(`${API_BASE}/api/clear-incidents`, { method: "POST" });
      modal?.classList.add("hidden");
      document.getElementById("results-weather-banner")?.classList.add("hidden");

      if (appState.currentView === "results") {
        await executeRouteCalculation();
      }
    } catch (e) {
      alert(`Failed to clear incidents: ${e.message}`);
    }
  });
}

// -------------------------------------------------------------
// Interactive Presentation Deck Controller
// -------------------------------------------------------------
function setupPresentationDeckListeners() {
  const modal = document.getElementById("presentation-modal");
  const openBtn = document.getElementById("btn-open-ppt");
  const closeBtn = document.getElementById("btn-close-deck");
  const prevBtn = document.getElementById("btn-slide-prev");
  const nextBtn = document.getElementById("btn-slide-next");
  const fsBtn = document.getElementById("btn-deck-fullscreen");
  const dots = document.querySelectorAll(".slide-dot");

  const showSlide = (n) => {
    if (n < 1) n = 1;
    if (n > appState.totalSlides) n = appState.totalSlides;
    appState.currentSlide = n;

    document.querySelectorAll(".ppt-slide").forEach(s => s.classList.remove("active"));
    const activeSlide = document.querySelector(`.ppt-slide[data-slide="${n}"]`);
    if (activeSlide) activeSlide.classList.add("active");

    dots.forEach((d, i) => {
      d.classList.toggle("active", i + 1 === n);
    });

    const indicator = document.getElementById("slide-num-indicator");
    if (indicator) indicator.textContent = `${n} / ${appState.totalSlides}`;
  };

  openBtn?.addEventListener("click", () => {
    modal?.classList.remove("hidden");
    showSlide(1);
  });

  closeBtn?.addEventListener("click", () => {
    modal?.classList.add("hidden");
  });

  prevBtn?.addEventListener("click", () => showSlide(appState.currentSlide - 1));
  nextBtn?.addEventListener("click", () => showSlide(appState.currentSlide + 1));

  dots.forEach(d => {
    d.addEventListener("click", () => {
      const sNum = parseInt(d.dataset.slide, 10);
      showSlide(sNum);
    });
  });

  // Fullscreen
  fsBtn?.addEventListener("click", () => {
    const card = document.querySelector(".presentation-card");
    if (!document.fullscreenElement) {
      card?.requestFullscreen().catch(err => console.log(err));
    } else {
      document.exitFullscreen();
    }
  });

  // Keyboard Navigation for Presentation Mode
  document.addEventListener("keydown", (e) => {
    if (modal && !modal.classList.contains("hidden")) {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") {
        showSlide(appState.currentSlide + 1);
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        showSlide(appState.currentSlide - 1);
      } else if (e.key === "Escape") {
        modal.classList.add("hidden");
      }
    }
  });
}

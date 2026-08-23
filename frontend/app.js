/**
 * Smart Traffic Route Optimizer - Multi-Page Client Application
 * Page 1: Dedicated Journey Planner & Endpoint Entry
 * Page 2: Clean Map & Route Navigation View with On-Demand Drawer
 * Integrated with Google Maps Platform & Real-Time Traffic
 */

const API_BASE = window.location.origin;
const GMAPS_KEY_STORAGE = "smart_traffic_gmaps_key";

// Application State
let appState = {
  currentView: "planner", // "planner" or "results"
  nodes: [],
  roads: [],
  vehicles: [],
  selectedSource: "NODE_CP",
  selectedDestination: "NODE_CYBER",
  selectedVehicle: "Petrol_Sedan",
  weatherCondition: "Clear",
  hourOfDay: 9,
  dayOfWeek: 1,
  activeRouteKey: "fastest", // "fastest", "eco", "weather_safe", "all"
  lastResult: null,
  currentMapLayer: "roadmap"
};

// Map Objects (Leaflet)
let leafletMap = null;
let currentTileLayer = null;
let trafficTileLayer = null;
let nodeMarkersLayer = null;
let routePolylinesLayer = null;
let routeLayers = { fastest: null, eco: null, weather_safe: null };
let isTrafficActive = true;

// Google Maps Native Objects
let googleMap = null;
let googleTrafficLayer = null;
let googlePolylines = { fastest: null, eco: null, weather_safe: null };
let googleMarkers = [];
let isGoogleMapsLoaded = false;

// Tile Providers for Google Maps & Leaflet
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

const ROUTE_COLORS = {
  fastest: { color: "#00e5ff", weight: 6, opacity: 0.95 },
  eco: { color: "#10b981", weight: 5, opacity: 0.9 },
  weather_safe: { color: "#f59e0b", weight: 5, opacity: 0.9 }
};

// -------------------------------------------------------------
// Initialization
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  setupPlannerEventListeners();
  setupResultsEventListeners();
  setupGoogleMapsModalListeners();
  
  // Try loading saved Google Maps API Key if present
  const savedKey = localStorage.getItem(GMAPS_KEY_STORAGE);
  if (savedKey) {
    const inputKey = document.getElementById("input-gmaps-api-key");
    if (inputKey) inputKey.value = savedKey;
    initGoogleMapsSdk(savedKey).catch(e => console.log("Google Maps SDK load fallback to tile renderer:", e));
  }

  await loadInitialData();
});

// -------------------------------------------------------------
// Google Maps SDK Loader
// -------------------------------------------------------------
function initGoogleMapsSdk(apiKey) {
  return new Promise((resolve, reject) => {
    if (window.google && window.google.maps) {
      isGoogleMapsLoaded = true;
      resolve(window.google.maps);
      return;
    }
    if (!apiKey) {
      reject(new Error("No Google Maps API Key"));
      return;
    }
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=geometry,places`;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      isGoogleMapsLoaded = true;
      resolve(window.google.maps);
    };
    script.onerror = (err) => reject(err);
    document.head.appendChild(script);
  });
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

    updatePlannerInputs();
    renderPlannerVehicles();
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

  if (srcNode && inputSrc) inputSrc.value = `${srcNode.node_name} (${srcNode.zone})`;
  if (dstNode && inputDst) inputDst.value = `${dstNode.node_name} (${dstNode.zone})`;
}

function renderPlannerVehicles() {
  const container = document.getElementById("planner-vehicle-grid");
  if (!container) return;
  container.innerHTML = "";

  appState.vehicles.forEach(v => {
    const btn = document.createElement("button");
    btn.className = `veh-pill-btn ${v.id === appState.selectedVehicle ? "active" : ""}`;
    btn.dataset.vehId = v.id;
    btn.innerHTML = `
      <span class="veh-pill-icon">${v.icon}</span>
      <span class="veh-pill-name">${v.name.split(" (")[0]}</span>
    `;

    btn.addEventListener("click", () => {
      document.querySelectorAll(".veh-pill-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      appState.selectedVehicle = v.id;
    });

    container.appendChild(btn);
  });
}

// -------------------------------------------------------------
// Autocomplete Search Logic for Page 1
// -------------------------------------------------------------
function setupSearchDropdown(inputId, dropdownId, onSelect) {
  const input = document.getElementById(inputId);
  const dropdown = document.getElementById(dropdownId);
  if (!input || !dropdown) return;

  const performSearch = () => {
    const q = input.value.trim().toLowerCase();
    const matches = q
      ? appState.nodes.filter(n => n.node_name.toLowerCase().includes(q) || n.zone.toLowerCase().includes(q) || n.node_id.toLowerCase().includes(q))
      : appState.nodes;

    renderDropdownItems(matches, dropdown, onSelect, q);
    dropdown.classList.remove("hidden");
  };

  input.addEventListener("input", performSearch);
  
  input.addEventListener("focus", () => {
    input.select();
    performSearch();
  });
  
  input.addEventListener("click", performSearch);

  document.addEventListener("click", e => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add("hidden");
    }
  });
}

function renderDropdownItems(items, dropdown, onSelect, query) {
  dropdown.innerHTML = "";
  if (items.length === 0) {
    dropdown.innerHTML = `<div style="padding:10px; color:#6b7280; font-size:0.75rem; text-align:center;">No matching locations found.</div>`;
    return;
  }

  items.slice(0, 10).forEach(node => {
    const div = document.createElement("div");
    div.className = "search-item";
    
    let titleHtml = node.node_name;
    if (query) {
      const idx = titleHtml.toLowerCase().indexOf(query);
      if (idx !== -1) {
        titleHtml = titleHtml.substring(0, idx) + 
          `<span class="search-item-match">${titleHtml.substring(idx, idx + query.length)}</span>` + 
          titleHtml.substring(idx + query.length);
      }
    }

    div.innerHTML = `
      <span class="search-item-title">${titleHtml}</span>
      <span class="search-item-zone">${node.zone} • ${node.node_id}</span>
    `;

    div.addEventListener("click", () => {
      onSelect(node);
      dropdown.classList.add("hidden");
    });

    dropdown.appendChild(div);
  });
}

// -------------------------------------------------------------
// View Switching Logic (Planner <-> Results)
// -------------------------------------------------------------
function switchView(viewName) {
  appState.currentView = viewName;

  const viewPlanner = document.getElementById("view-planner");
  const viewResults = document.getElementById("view-results");

  if (viewName === "planner") {
    viewResults.classList.remove("active");
    viewPlanner.classList.add("active");
  } else {
    viewPlanner.classList.remove("active");
    viewResults.classList.add("active");

    if (!leafletMap) {
      initResultsMap();
    } else {
      setTimeout(() => leafletMap.invalidateSize(), 150);
    }
  }
}

function initResultsMap() {
  const container = document.getElementById("results-map");
  if (!container) return;

  leafletMap = L.map("results-map", { zoomControl: false }).setView([28.5800, 77.2000], 11);

  // Default to Google Roadmap
  const provider = MAP_TILE_PROVIDERS[appState.currentMapLayer] || MAP_TILE_PROVIDERS.roadmap;
  currentTileLayer = L.tileLayer(provider.url, provider.options).addTo(leafletMap);

  // Google Live Traffic Layer (lyrs=h,traffic or mt1 overlay)
  trafficTileLayer = L.tileLayer("https://mt1.google.com/vt?lyrs=h,traffic&x={x}&y={y}&z={z}", {
    opacity: 0.9,
    maxZoom: 20
  }).addTo(leafletMap);

  L.control.zoom({ position: "bottomright" }).addTo(leafletMap);

  nodeMarkersLayer = L.layerGroup().addTo(leafletMap);
  routePolylinesLayer = L.layerGroup().addTo(leafletMap);
}

function changeMapTileLayer(providerKey) {
  appState.currentMapLayer = providerKey;
  if (!leafletMap) return;
  const provider = MAP_TILE_PROVIDERS[providerKey] || MAP_TILE_PROVIDERS.roadmap;
  if (currentTileLayer) {
    leafletMap.removeLayer(currentTileLayer);
  }
  currentTileLayer = L.tileLayer(provider.url, provider.options).addTo(leafletMap);

  if (trafficTileLayer && isTrafficActive) {
    leafletMap.removeLayer(trafficTileLayer);
    trafficTileLayer.addTo(leafletMap);
  }

  if (routePolylinesLayer) routePolylinesLayer.bringToFront();
}

function toggleTrafficLayer() {
  isTrafficActive = !isTrafficActive;
  const btn = document.getElementById("btn-toggle-traffic");

  if (trafficTileLayer && leafletMap) {
    if (isTrafficActive) {
      trafficTileLayer.addTo(leafletMap);
      if (btn) {
        btn.classList.add("active");
        btn.classList.remove("off");
        btn.innerHTML = "<span>🚦 Traffic: ON</span>";
      }
    } else {
      leafletMap.removeLayer(trafficTileLayer);
      if (btn) {
        btn.classList.remove("active");
        btn.classList.add("off");
        btn.innerHTML = "<span>🚦 Traffic: OFF</span>";
      }
    }
  }
}

// -------------------------------------------------------------
// Run Route Optimization
// -------------------------------------------------------------
async function executeRouteOptimization() {
  if (appState.selectedSource === appState.selectedDestination) {
    alert("Origin and Destination cannot be the same. Please choose different locations.");
    return;
  }

  const btn = document.getElementById("btn-find-routes");
  btn.innerHTML = `<span>⏳ Optimizing via Google Roads & ML...</span>`;
  btn.disabled = true;

  const payload = {
    source_id: appState.selectedSource,
    destination_id: appState.selectedDestination,
    hour_of_day: parseInt(appState.hourOfDay),
    day_of_week: parseInt(appState.dayOfWeek),
    weather_condition: appState.weatherCondition,
    vehicle_type: appState.selectedVehicle
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
      
      // Switch view to Results
      switchView("results");
      
      // Update Results Header
      const srcNode = getNodeById(appState.selectedSource);
      const dstNode = getNodeById(appState.selectedDestination);
      const vehObj = appState.vehicles.find(v => v.id === appState.selectedVehicle) || { icon: "🚗", name: "Petrol Sedan" };

      document.getElementById("res-start-name").textContent = srcNode?.node_name.split(" (")[0] || "Origin";
      document.getElementById("res-end-name").textContent = dstNode?.node_name.split(" (")[0] || "Destination";
      
      const hDisplay = appState.hourOfDay >= 12 ? `${appState.hourOfDay % 12 || 12}:00 PM` : `${appState.hourOfDay}:00 AM`;
      document.getElementById("res-trip-meta").textContent = `${vehObj.icon} ${vehObj.name.split(" (")[0]} • ${appState.weatherCondition} • ${hDisplay}`;

      // Update Map Route Tab Pill times
      if (data.routes.fastest) document.getElementById("pill-fastest-time").textContent = `${data.routes.fastest.total_time_min}m`;
      if (data.routes.eco) document.getElementById("pill-eco-time").textContent = `${data.routes.eco.total_time_min}m`;
      if (data.routes.weather_safe) document.getElementById("pill-weather-time").textContent = `${data.routes.weather_safe.total_time_min}m`;

      // Render Routes on Map
      renderMap(data.routes);
      renderMapNodes();

      // Select default route (Fastest)
      selectResultRoute("fastest");

      // Update Drawer
      renderDrawerComparison(data.routes);
      renderDrawerSavings(data.routes);
      loadDrawerHistory();

    } else {
      alert("Route optimization failed: " + (data.detail || data.message || "Unknown error"));
    }
  } catch (err) {
    console.error("Optimization query error:", err);
  } finally {
    btn.innerHTML = `<span>🚀 Calculate & Show Optimal Routes</span>`;
    btn.disabled = false;
  }
}

// -------------------------------------------------------------
// High-Precision Real-Road Polyline Snapping
// -------------------------------------------------------------
const clientGeometryCache = {};

async function getAccurateRoadPolyline(routeObj) {
  if (!routeObj || !routeObj.path_coordinates || routeObj.path_coordinates.length === 0) return [];

  // If backend already returned high-resolution curve points (> 15 points), use directly
  if (routeObj.path_coordinates.length > 15) {
    return routeObj.path_coordinates.map(p => [p.lat, p.lng]);
  }

  // Extract sequence of node coordinates from steps
  const waypoints = [];
  if (routeObj.steps && routeObj.steps.length > 0) {
    const firstNode = getNodeById(routeObj.steps[0].from_node);
    if (firstNode) waypoints.push([firstNode.longitude, firstNode.latitude]);
    routeObj.steps.forEach(s => {
      const n = getNodeById(s.to_node);
      if (n) waypoints.push([n.longitude, n.latitude]);
    });
  } else {
    routeObj.path_coordinates.forEach(p => waypoints.push([p.lng, p.lat]));
  }

  if (waypoints.length < 2) {
    return routeObj.path_coordinates.map(p => [p.lat, p.lng]);
  }

  const cacheKey = waypoints.map(w => `${w[0].toFixed(4)},${w[1].toFixed(4)}`).join(";");
  if (clientGeometryCache[cacheKey]) {
    return clientGeometryCache[cacheKey];
  }

  const url = `https://router.project-osrm.org/route/v1/driving/${cacheKey}?overview=full&geometries=geojson`;
  try {
    const resp = await fetch(url);
    const data = await resp.json();
    if (data.routes && data.routes.length > 0) {
      const realPoints = data.routes[0].geometry.coordinates.map(pt => [pt[1], pt[0]]);
      clientGeometryCache[cacheKey] = realPoints;
      return realPoints;
    }
  } catch (err) {
    console.warn("Client physical road snapping fallback:", err);
  }

  return routeObj.path_coordinates.map(p => [p.lat, p.lng]);
}

// -------------------------------------------------------------
// Map & Route Polylines Rendering
// -------------------------------------------------------------
async function renderMap(routes) {
  if (!routePolylinesLayer) return;
  routePolylinesLayer.clearLayers();
  routeLayers = { fastest: null, eco: null, weather_safe: null };

  const allPoints = [];
  const drawOrder = ["weather_safe", "eco", "fastest"];

  for (const key of drawOrder) {
    const r = routes[key];
    if (!r || !r.found) continue;

    // Fetch 100% real physical road geometry following actual streets
    const latlngs = await getAccurateRoadPolyline(r);
    latlngs.forEach(ll => allPoints.push(ll));

    const style = ROUTE_COLORS[key];
    const polyline = L.polyline(latlngs, {
      color: style.color,
      weight: style.weight,
      opacity: style.opacity,
      lineJoin: "round"
    });

    polyline.bindTooltip(`<strong>${r.mode_title}</strong><br>Time: ${r.total_time_min}m | Fuel: ${r.total_fuel_units} ${r.fuel_unit_name}`, { sticky: true });
    polyline.on("click", () => selectResultRoute(key));

    routeLayers[key] = polyline;
    routePolylinesLayer.addLayer(polyline);
  }

  // Weather Banner
  const advisories = routes.fastest?.weather_advisories || [];
  const banner = document.getElementById("results-weather-banner");
  const bannerText = document.getElementById("results-weather-banner-text");
  if (advisories.length > 0) {
    banner.classList.remove("hidden");
    bannerText.textContent = advisories.join(" • ");
  } else {
    banner.classList.add("hidden");
  }

  if (allPoints.length > 0 && leafletMap) {
    leafletMap.fitBounds(L.latLngBounds(allPoints), { padding: [50, 50] });
  }
}

function renderMapNodes() {
  if (!nodeMarkersLayer) return;
  nodeMarkersLayer.clearLayers();

  appState.nodes.forEach(node => {
    const isSource = node.node_id === appState.selectedSource;
    const isDest = node.node_id === appState.selectedDestination;

    let markerBg = "rgba(59, 130, 246, 0.85)";
    let border = "1px solid #93c5fd";
    let iconSymbol = "📍";

    if (isSource) { markerBg = "#10b981"; border = "2px solid #fff"; iconSymbol = "🟢"; }
    else if (isDest) { markerBg = "#ef4444"; border = "2px solid #fff"; iconSymbol = "🔴"; }

    const customIcon = L.divIcon({
      className: "delhi-node-marker",
      html: `<div style="background-color:${markerBg}; width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:${border}; font-size:10px; box-shadow:0 0 10px rgba(0,0,0,0.5);">${iconSymbol}</div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });

    const marker = L.marker([node.latitude, node.longitude], { icon: customIcon })
      .bindTooltip(`<strong>${node.node_name}</strong><br><span style="color:#9ca3af">${node.zone}</span>`, { direction: "top" });

    nodeMarkersLayer.addLayer(marker);
  });
}

function selectResultRoute(key) {
  appState.activeRouteKey = key;

  document.querySelectorAll(".map-route-pill").forEach(pill => {
    pill.classList.toggle("active", pill.dataset.route === key);
  });

  Object.keys(routeLayers).forEach(k => {
    const layer = routeLayers[k];
    if (!layer) return;

    if (key === "all" || key === k) {
      layer.setStyle({
        opacity: key === "all" ? 0.85 : 1.0,
        weight: key === k ? 8 : (key === "all" ? ROUTE_COLORS[k].weight : 3)
      });
      if (!routePolylinesLayer.hasLayer(layer)) routePolylinesLayer.addLayer(layer);
    } else {
      layer.setStyle({ opacity: 0.15, weight: 3 });
    }
  });

  const activeRoute = appState.lastResult?.routes[key === "all" ? "fastest" : key] || appState.lastResult?.routes.fastest;
  if (activeRoute) {
    document.getElementById("quick-mode-title").textContent = activeRoute.mode_title;
    document.getElementById("quick-mode-badge").textContent = activeRoute.mode_badge;
    document.getElementById("quick-eta").textContent = `${activeRoute.total_time_min} min`;
    document.getElementById("quick-dist").textContent = `${activeRoute.total_distance_km} km`;
    document.getElementById("quick-fuel").textContent = `${activeRoute.total_fuel_units} ${activeRoute.fuel_unit_name.slice(0, 3)}`;
    document.getElementById("quick-cost").textContent = `₹${activeRoute.total_cost_inr}`;
    document.getElementById("quick-safety").textContent = `${activeRoute.weather_safety_score}%`;

    renderDrawerItinerary(activeRoute);
  }
}

// -------------------------------------------------------------
// On-Demand Details Drawer Renderers
// -------------------------------------------------------------
function renderDrawerComparison(routes) {
  const container = document.getElementById("drawer-comparison-cards");
  if (!container) return;
  container.innerHTML = "";

  ["fastest", "eco", "weather_safe"].forEach(k => {
    const r = routes[k];
    if (!r || !r.found) return;

    const card = document.createElement("div");
    card.className = `route-card ${k} ${appState.activeRouteKey === k ? "selected" : ""}`;
    card.innerHTML = `
      <div class="route-card-header">
        <span class="route-name">${r.mode_title}</span>
        <span class="route-badge">${r.mode_badge}</span>
      </div>
      <div class="route-metrics-grid">
        <div class="metric-item">
          <span class="metric-lbl">ETA</span>
          <span class="metric-val" style="color:var(--accent-fastest)">${r.total_time_min} min</span>
        </div>
        <div class="metric-item">
          <span class="metric-lbl">Fuel / Energy</span>
          <span class="metric-val" style="color:var(--accent-eco)">${r.total_fuel_units} ${r.fuel_unit_name.slice(0, 3)}</span>
        </div>
        <div class="metric-item">
          <span class="metric-lbl">Safety Score</span>
          <span class="metric-val" style="color:var(--accent-weather)">${r.weather_safety_score}%</span>
        </div>
      </div>
      <div class="route-metrics-grid" style="border:none; margin-top:4px; padding:0;">
        <div class="metric-item"><span class="metric-lbl">Distance</span><span class="metric-val">${r.total_distance_km} km</span></div>
        <div class="metric-item"><span class="metric-lbl">CO₂</span><span class="metric-val">${r.total_co2_kg} kg</span></div>
        <div class="metric-item"><span class="metric-lbl">Est. Cost</span><span class="metric-val">₹${r.total_cost_inr}</span></div>
      </div>
    `;

    card.addEventListener("click", () => {
      selectResultRoute(k);
      document.querySelectorAll(".route-card").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
    });

    container.appendChild(card);
  });
}

function renderDrawerSavings(routes) {
  const box = document.getElementById("drawer-savings-box");
  const text = document.getElementById("drawer-savings-text");
  if (!box || !text) return;

  const fastest = routes.fastest;
  const eco = routes.eco;

  if (fastest && eco && fastest.total_fuel_units > 0) {
    const fuelDiff = fastest.total_fuel_units - eco.total_fuel_units;
    const pctSaved = Math.max(0, (fuelDiff / fastest.total_fuel_units) * 100).toFixed(1);
    const co2Saved = Math.max(0, fastest.total_co2_kg - eco.total_co2_kg).toFixed(2);

    if (fuelDiff > 0.05) {
      box.classList.remove("hidden");
      text.innerHTML = `🌿 <strong>Eco Route saves ${pctSaved}% fuel</strong> (${fuelDiff.toFixed(2)} ${fastest.fuel_unit_name}) and <strong>${co2Saved} kg CO₂</strong> compared to the fastest route.`;
    } else {
      box.classList.remove("hidden");
      text.innerHTML = `⚡ The fastest route is already highly energy-efficient for this corridor!`;
    }
  } else {
    box.classList.add("hidden");
  }
}

function renderDrawerItinerary(route) {
  const label = document.getElementById("drawer-active-route-label");
  const list = document.getElementById("drawer-steps-list");
  if (!label || !list) return;

  label.textContent = route.mode_title;
  list.innerHTML = "";

  if (!route.steps || route.steps.length === 0) {
    list.innerHTML = `<div style="padding:10px; color:#6b7280; font-size:0.75rem; text-align:center;">No step details available.</div>`;
    return;
  }

  route.steps.forEach((s, idx) => {
    const row = document.createElement("div");
    row.className = "step-row";
    row.innerHTML = `
      <div>
        <div class="step-road">${idx + 1}. ${s.road_name}</div>
        <div class="step-nodes">${s.from_name.split(" (")[0]} ➔ ${s.to_name.split(" (")[0]} (${s.road_type})</div>
      </div>
      <div style="text-align:right;">
        <div style="font-family:'JetBrains Mono'; font-weight:700; color:#fff;">${s.distance_km} km</div>
        <div style="color:#9ca3af; font-size:0.68rem;">~${s.predicted_time_min} min</div>
      </div>
    `;
    list.appendChild(row);
  });
}

async function loadDrawerHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/history?limit=5`);
    const data = await res.json();
    const list = document.getElementById("drawer-history-list");
    if (!list) return;
    list.innerHTML = "";

    if (!data.history || data.history.length === 0) {
      list.innerHTML = `<div style="padding:10px; color:#6b7280; font-size:0.75rem; text-align:center;">No past queries logged.</div>`;
      return;
    }

    data.history.forEach(item => {
      const row = document.createElement("div");
      row.className = "history-item";
      row.innerHTML = `
        <div>
          <span class="hist-route">${item.source_id.replace("NODE_", "")} ➔ ${item.destination_id.replace("NODE_", "")}</span>
          <span style="font-size:0.64rem; color:#6b7280; display:block;">${item.vehicle_type.replace("_", " ")} • ${item.weather_condition}</span>
        </div>
        <div style="text-align:right;">
          <span style="font-family:'JetBrains Mono'; font-weight:700; color:#38bdf8;">${item.fastest_time_min}m</span>
          <span style="font-size:0.64rem; color:#34d399; display:block;">-${item.eco_fuel_saved_percent}% fuel</span>
        </div>
      `;
      list.appendChild(row);
    });
  } catch (e) {
    console.error("Error fetching history:", e);
  }
}

// -------------------------------------------------------------
// Google Maps API Key Modal Listeners
// -------------------------------------------------------------
function setupGoogleMapsModalListeners() {
  const modal = document.getElementById("gmaps-key-modal");
  const openBtn = document.getElementById("btn-open-gmaps-modal");
  const closeBtn = document.getElementById("btn-close-gmaps-modal");
  const saveBtn = document.getElementById("btn-save-gmaps-key");
  const input = document.getElementById("input-gmaps-api-key");

  if (openBtn) {
    openBtn.addEventListener("click", () => {
      if (modal) modal.classList.remove("hidden");
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      if (modal) modal.classList.add("hidden");
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const key = input.value.trim();
      if (key) {
        localStorage.setItem(GMAPS_KEY_STORAGE, key);
        try {
          await initGoogleMapsSdk(key);
          alert("✅ Google Maps API Key activated successfully! Real Google Maps services are enabled.");
        } catch (e) {
          alert("Key saved! Live Google Maps tiles and traffic layers will be used.");
        }
      } else {
        localStorage.removeItem(GMAPS_KEY_STORAGE);
        alert("Google Maps API Key removed. Reverting to default high-definition road routing.");
      }
      if (modal) modal.classList.add("hidden");
    });
  }
}

// -------------------------------------------------------------
// Event Listeners Setup
// -------------------------------------------------------------
function setupPlannerEventListeners() {
  // Autocomplete Dropdowns for Source & Destination
  setupSearchDropdown("planner-search-source", "planner-src-dropdown", (node) => {
    appState.selectedSource = node.node_id;
    updatePlannerInputs();
  });

  setupSearchDropdown("planner-search-dest", "planner-dst-dropdown", (node) => {
    appState.selectedDestination = node.node_id;
    updatePlannerInputs();
  });

  // Clear Buttons
  const clearSrcBtn = document.getElementById("btn-planner-clear-src");
  if (clearSrcBtn) {
    clearSrcBtn.addEventListener("click", () => {
      const input = document.getElementById("planner-search-source");
      if (input) { input.value = ""; input.focus(); }
    });
  }

  const clearDstBtn = document.getElementById("btn-planner-clear-dst");
  if (clearDstBtn) {
    clearDstBtn.addEventListener("click", () => {
      const input = document.getElementById("planner-search-dest");
      if (input) { input.value = ""; input.focus(); }
    });
  }

  // Swap Button
  const swapBtn = document.getElementById("btn-planner-swap");
  if (swapBtn) {
    swapBtn.addEventListener("click", () => {
      const tmp = appState.selectedSource;
      appState.selectedSource = appState.selectedDestination;
      appState.selectedDestination = tmp;
      updatePlannerInputs();
    });
  }

  // Popular Quick Chips
  document.querySelectorAll(".quick-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      appState.selectedSource = chip.dataset.src;
      appState.selectedDestination = chip.dataset.dst;
      updatePlannerInputs();
      executeRouteOptimization();
    });
  });

  // Weather & Time
  const weatherSelect = document.getElementById("planner-weather-select");
  if (weatherSelect) {
    weatherSelect.addEventListener("change", e => {
      appState.weatherCondition = e.target.value;
    });
  }

  const hourSlider = document.getElementById("planner-hour-slider");
  const timeDisplay = document.getElementById("planner-time-display");
  if (hourSlider && timeDisplay) {
    hourSlider.addEventListener("input", e => {
      const h = parseInt(e.target.value);
      appState.hourOfDay = h;
      const period = h >= 12 ? "PM" : "AM";
      const displayH = h % 12 === 0 ? 12 : h % 12;
      const isRush = (h >= 8 && h <= 10) || (h >= 17 && h <= 20);
      timeDisplay.textContent = `${displayH.toString().padStart(2, '0')}:00 ${period} ${isRush ? "(Peak Rush)" : "(Normal)"}`;
    });
  }

  // Main CTA Button
  const findBtn = document.getElementById("btn-find-routes");
  if (findBtn) {
    findBtn.addEventListener("click", executeRouteOptimization);
  }
}

function setupResultsEventListeners() {
  // Back to Planner Button
  const backBtn = document.getElementById("btn-back-to-planner");
  if (backBtn) {
    backBtn.addEventListener("click", () => {
      switchView("planner");
    });
  }

  // Real-Time Google Traffic Layer Toggle
  const trafficBtn = document.getElementById("btn-toggle-traffic");
  if (trafficBtn) {
    trafficBtn.addEventListener("click", toggleTrafficLayer);
  }

  // Map Tile Layer Switcher (Google Roadmap / Satellite / Hybrid / Terrain / Dark)
  const mapLayerSelect = document.getElementById("select-map-layer");
  if (mapLayerSelect) {
    mapLayerSelect.addEventListener("change", (e) => {
      changeMapTileLayer(e.target.value);
    });
  }

  // Map Route Tabs
  document.querySelectorAll(".map-route-pill").forEach(pill => {
    pill.addEventListener("click", () => {
      selectResultRoute(pill.dataset.route);
    });
  });

  // Recenter Map
  const recenterBtn = document.getElementById("btn-results-recenter");
  if (recenterBtn) {
    recenterBtn.addEventListener("click", () => {
      if (leafletMap) leafletMap.setView([28.5800, 77.2000], 11);
    });
  }

  // Drawer Toggle
  const drawer = document.getElementById("details-drawer");
  const backdrop = document.getElementById("drawer-backdrop");

  const openDrawer = () => {
    if (drawer) drawer.classList.remove("hidden");
    if (backdrop) backdrop.classList.remove("hidden");
  };

  const closeDrawer = () => {
    if (drawer) drawer.classList.add("hidden");
    if (backdrop) backdrop.classList.add("hidden");
  };

  const btnToggle = document.getElementById("btn-toggle-details");
  if (btnToggle) btnToggle.addEventListener("click", openDrawer);

  const btnQuickSteps = document.getElementById("btn-quick-view-steps");
  if (btnQuickSteps) btnQuickSteps.addEventListener("click", openDrawer);

  const btnCloseDrawer = document.getElementById("btn-close-drawer");
  if (btnCloseDrawer) btnCloseDrawer.addEventListener("click", closeDrawer);

  if (backdrop) backdrop.addEventListener("click", closeDrawer);

  const btnRefreshHist = document.getElementById("btn-drawer-refresh-history");
  if (btnRefreshHist) btnRefreshHist.addEventListener("click", loadDrawerHistory);
}

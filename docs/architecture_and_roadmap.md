# Path Pilot — Architecture & System Specification

## 1. System Overview
**Path Pilot** is an intelligent transportation routing system that combines **Machine Learning Travel-Time & Energy Inference** with a high-speed **C++ Min-Heap Dijkstra Graph Engine** to solve urban congestion across Delhi NCR.

Instead of computing static geometric shortest paths, the system dynamically weights road corridors based on:
- Live and historical traffic density curves (Peak morning & evening rush hours)
- Dynamic weather hazards (Monsoon waterlogging, dense winter smog fog, extreme heatwaves)
- Powertrain fuel and battery kinetics (Petrol, Diesel SUV, Electric Vehicles with regenerative braking, Commercial Trucks, Two-Wheelers)
- Live incident blockades (Construction, emergency flyover closures, accident blockades)

---

## 2. Multi-Objective Pareto Strategies
The engine evaluates 4 distinct routing criteria:

1. **⚡ Fastest Route ($W_{\text{time}} = 1.0$)**:
   Minimizes ML-predicted travel time in minutes. Directs vehicles toward high-speed expressways and open bypass corridors.
2. **🌿 Eco-Friendly Route ($W_{\text{fuel}} = 0.85, W_{\text{time}} = 0.15$)**:
   Minimizes total fuel (Liters) or energy (kWh) and $CO_2$ emissions. Avoids stop-and-go congestion and steep elevation gradients.
3. **🛡️ Weather-Resilient Safe Route ($W_{\text{weather}} = 0.75, W_{\text{time}} = 0.15, W_{\text{fuel}} = 0.10$)**:
   Bypasses flood-prone underpasses (e.g. Minto Bridge, Yamuna Bank) and low-visibility smog bridges during hazardous weather conditions.
4. **🎛️ Custom Balanced Route**:
   Allows user-defined slider weighting for custom trade-offs.

---

## 3. Machine Learning Architecture
- **Dataset**: 131,040 observations spanning 20 Delhi transit nodes, 52 bidirectional corridors, 6 weather profiles, 5 powertrains, and 24 hours.
- **Preprocessing**:
  - Cyclical temporal transformation: $\sin(2\pi \cdot \text{hour}/24)$, $\cos(2\pi \cdot \text{hour}/24)$, $\sin(2\pi \cdot \text{day}/7)$, $\cos(2\pi \cdot \text{day}/7)$.
  - One-Hot Encoding for road types, weather conditions, vehicle categories.
  - StandardScaler normalization.
- **Models**:
  - Travel Time: **Gradient Boosting Regressor** ($R^2 = 0.9794$, $\text{MAE} = 1.78\text{ min}$).
  - Fuel / Energy: **Gradient Boosting Regressor** ($R^2 = 0.9961$, $\text{MAE} = 0.064\text{ L/kWh}$).
- **Artifacts**: Serialized into `ml/models/traffic_model.joblib`.

---

## 4. C++ Dijkstra High-Performance Solver
- **Data Structures**: `std::vector<std::vector<Edge>>` adjacency list, `std::priority_queue<std::pair<double, int>, ..., std::greater<...>>` Min-Heap.
- **Complexity**: $O((V + E) \log V)$ time, $O(V + E)$ space.
- **Performance**: Solves Delhi network paths in **$< 0.8$ milliseconds**.
- **Bridge**: Python subprocess with standard JSON I/O and pure-Python Dijkstra fallback for portability.

---

## 5. API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health, ML metrics, and C++ engine status |
| `GET` | `/api/nodes` | 20 Delhi NCR transit hubs with latitude/longitude/zone |
| `GET` | `/api/roads` | 52 road corridors with speed limits and risk scores |
| `GET` | `/api/vehicles` | Powertrain profiles and $CO_2$ emission factors |
| `GET` | `/api/weather-presets` | 6 weather profiles and hazard classifications |
| `POST` | `/api/route` | Computes Fastest, Eco, Weather-Safe, and Custom routes |
| `GET` | `/api/history` | Retrieves recent SQLite query logs |
| `GET` | `/api/analytics` | Network-wide statistics and benchmark tables |
| `POST` | `/api/simulate-incident` | Injects live road blockades or waterlogging |
| `POST` | `/api/clear-incidents` | Clears all active incident simulations |

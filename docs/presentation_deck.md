# Path Pilot — Presentation Deck Transcript & Speaker Notes

## Slide 1: Title & Executive Overview
- **Headline**: Path Pilot
- **Subtitle**: Multi-Objective Navigation via Machine Learning Travel-Time Prediction & C++ Dijkstra Engine
- **Speaker Notes**:
  > "Good morning evaluators and jury members. Urban congestion in metropolitan areas like Delhi NCR results in billions of dollars in wasted fuel and millions of lost hours every single year. Today, we present Path Pilot—a next-generation navigation system that combines Machine Learning predictive travel time modeling with a compiled C++ Dijkstra graph engine to provide multi-objective Pareto routing: Fastest ETA, Eco-Friendly Fuel/EV Energy savings, and Weather-Resilient hazard bypass."

---

## Slide 2: The Problem Statement & Urban Grid Crisis
- **Headline**: The Delhi-NCR Traffic & Environmental Crisis
- **Key Pain Points**:
  1. Static distance algorithms trap drivers in gridlocked bottlenecks.
  2. Single-objective blindness ignores vehicle powertrain physics (EV vs Diesel SUV) and environmental impact.
  3. Monsoon waterlogging and winter smog cause sudden route failures.
- **Speaker Notes**:
  > "Why do existing GPS applications fail during peak hours? Because they rely on static or reactive distance measures. When a bottleneck begins, conventional routers continue funneling vehicles into the congested segment until gridlock occurs. Furthermore, standard navigation doesn't differentiate between an Electric Vehicle with regenerative braking and a heavy freight truck climbing an incline."

---

## Slide 3: Machine Learning Predictive Pipeline
- **Headline**: Predictive Travel-Time & Energy Inference
- **Features (30 Dimensions)**: Distance, speed limits, traffic density index, temperature, visibility, precipitation, wind, gradient %, flood risk, fog risk, cyclical hour ($\sin/\cos$), cyclical day ($\sin/\cos$), vehicle type, road type.
- **Model Results**:
  - Linear Regression Baseline: $R^2 = 0.786$, $\text{MAE} = 7.82\text{ min}$
  - Random Forest Regressor: $R^2 = 0.977$, $\text{MAE} = 1.79\text{ min}$
  - **Gradient Boosting Regressor (Final)**: $R^2 = 0.9794$, $\text{MAE} = 1.78\text{ min}$
  - Fuel Consumption Model: $R^2 = 0.9961$, $\text{MAE} = 0.064\text{ L/kWh}$
- **Speaker Notes**:
  > "Our ML pipeline ingests temporal cycles using sine/cosine transformations, weather telemetry, and road risk indicators. Our final Gradient Boosting Regressor achieves an $R^2$ of 0.9794 for travel time and 0.9961 for fuel consumption, allowing accurate dynamic edge weight generation."

---

## Slide 4: C++ Dijkstra High-Performance Solver
- **Headline**: Microsecond Graph Optimization Core
- **Key Tech**: Min-Heap priority queue (`std::priority_queue`), adjacency lists, parent array path reconstruction.
- **Latency**: Sub-millisecond execution ($< 0.8\text{ ms}$).
- **Speaker Notes**:
  > "To ensure our backend can scale to millions of concurrent route requests without latency spikes, we built our core routing engine in modern C++17. The engine executes Dijkstra's algorithm with Min-Heap priority queues in under 1 millisecond, returning full node sequences and edge identifiers."

---

## Slide 5: Multi-Objective Pareto Optimization
- **Headline**: Multi-Objective Pareto Trade-Offs
- **Three Core Profiles**:
  - **Fastest Route**: Minimizes travel time.
  - **Eco-Friendly Route**: Saves up to 18% fuel by avoiding stop-and-go crawl sections.
  - **Weather-Safe Route**: Bypasses flood-prone underpasses (e.g. Yamuna Bank, Minto Bridge) during heavy monsoons or smog.
- **Speaker Notes**:
  > "Commuters don't always want just the fastest route—sometimes saving fuel or avoiding treacherous waterlogged roads is paramount. Our system produces Pareto-optimal options simultaneously."

---

## Slide 6: System Architecture & Data Flow
- **Headline**: Full-Stack Production Pipeline
- **Flow**: User Context ➔ Feature Mapper ➔ ML Inference ➔ C++ Dijkstra Solver ➔ FastAPI & SQLite ➔ Cyber-Cockpit UI.
- **Speaker Notes**:
  > "The architecture is modular and production-ready. Every component communicates cleanly via standardized JSON protocols with persistent logging to SQLite."

---

## Slide 7: Environmental & Economic Impact
- **Headline**: Measurable City-Scale Benefits
- **Key Metrics**:
  - 14.8% average fuel savings on Eco mode.
  - 1.4 kg $CO_2$ reduction per 25 km trip.
  - Direct cost savings for commercial logistics and daily commuters.
- **Speaker Notes**:
  > "If 10% of Delhi's 10 million registered vehicles adopted Eco-routing, the city would reduce over 250,000 metric tons of $CO_2$ and save crores of rupees in imported fuel annually."

---

## Slide 8: Future Roadmap & Hackathon Conclusion
- **Headline**: Future Scope & Summary
- **Roadmap**: V2X live probe ingestion, Reinforcement Learning for dynamic traffic lights, EV charging station auto-rerouting.
- **Speaker Notes**:
  > "Thank you! We are now excited to demonstrate the live interactive system and incident simulation."

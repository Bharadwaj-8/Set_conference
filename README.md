# Set_conference
# Dynamic Green Orchestrator (MacOS / Edge AI Prototype)

## Overview

The **Dynamic Green Orchestrator** is a context-aware orchestration system designed to optimize **energy consumption and carbon emissions** when executing large language model (LLM) queries.  

It dynamically decides whether a query should be processed **locally on edge devices** or **offloaded to the cloud**, based on:

- Device battery level  
- Network bandwidth  
- Real-time carbon intensity of the electricity grid

This prototype demonstrates a **sustainability-aware AI inference pipeline**, addressing the **Energy-Blindness Gap** in AI systems.

---

## Motivation

Modern AI systems often **ignore environmental impact** when deciding where and how to run computations. Offloading every LLM query to cloud servers:

- Increases **carbon emissions** if the power grid is fossil-fuel heavy  
- Drains **battery on edge devices** unnecessarily  
- May cause **latency issues** on weak networks  

The orchestrator uses **real-world sensor data** and **carbon intensity APIs** to make **carbon-aware, energy-efficient decisions**, allowing research on green AI without requiring physical deployment of heavy LLM models.

---

## Key Features

- **Battery Monitoring (MacOS):** Reads current battery percentage using `pmset`.  
- **Network Quality Assessment:** Measures real download speed with `speedtest-cli` and maps it to a normalized quality score.  
- **Carbon-Aware Scheduling:** Uses **Electricity Maps API** to get real-time carbon intensity of the grid.  
- **Sustainability Score:** Combines battery, network, and carbon data into a single score for decision-making.  
- **Dynamic Execution Routing:** Based on the sustainability score, queries are executed **on the edge** (locally) or **offloaded to cloud** (planned for future work).  
- **Future-Proof Design:** Modular architecture allows integration of split LLM inference and knowledge graph validation later.

---

## System Architecture

User Query --> Context Generator (battery, network, carbon)
|
V
Dynamic Green Orchestrator
|
Sustainability Score
|
Decision: EDGE / CLOUD
|
Edge LLM or Cloud LLM (future)
|
Response Output


---

## Components

| File | Purpose |
|------|---------|
| `context_real.py` | Real-time context sensing: battery %, network quality, carbon intensity |
| `main.py` | Orchestrator logic and decision engine, executes LLM locally if EDGE chosen |
| `.env` | Stores Electricity Maps API key securely (never commit) |
| `requirements.txt` | Required Python packages |
| `README.md` | Project documentation |


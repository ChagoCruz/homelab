## Homelab – Personal Life Infrastructure

**Built and maintained by Santiago Ramos**  
Full Stack Engineer | Backend Systems

A self-hosted, containerized backend for managing personal data, analytics, and AI-powered insights.
Built as the foundation for a long-term “Life Terminal” system.

**Status:** Active Development | Self-Hosted | Dockerized | Production-Deployed

## 🚀 Overview
Homelab is a self-hosted infrastructure project designed to centralize and manage personal life data — including finances, journal entries, expenses, health metrics, job tracking, and more. The system is designed with clear separation between development and production environments, emphasizing reproducibility, data durability, and secure remote access.

The goal is to build a production-grade backend architecture that:

- Runs locally and on a dedicated Ubuntu server
- Uses Docker for consistent environments
- Exposes a FastAPI backend
- Supports AI-powered insights
- Serves a Raspberry Pi touchscreen UI
- Is accessible securely over Tailscale

This project is both a practical tool and an ongoing exploration of backend architecture, containerization, and distributed personal systems.

## 🏗 Architecture
### Development Environment
- macOS (Apple Silicon)
- Docker Desktop
- PostgreSQL (containerized)

### Planned
- FastAPI container

### Production Environment
- Ubuntu Server (self-hosted)
- Docker Engine
- Persistent database volumes stored on hardware
- Accessed securely via Tailscale VPN

### Planned Frontend Layer
- Raspberry Pi with HyperPixel 720x720 touchscreen
- UI served over Tailscale
- Potential mobile / web access

## 🧰 Tech Stack
### Current
- PostgreSQL 16
- Docker & Docker Compose
- Environment variable configuration via .env

### In Progress
- FastAPI (Python)
- SQLAlchemy (async)
- RESTful API layer

### Planned
- AI integration for:
    - Data summaries
    - Pattern detection
    - Life analytics dashboards
- Raspberry Pi UI
- Mobile-accessible frontend
- Authentication layer
- Metrics & observability

## 📦 Repository Structure
```
homelab/
├── README.md
├── docker-compose.yml
├── .env
├── db/
│   └── init/
│       └── (SQL initialization scripts)
```

As the project evolves, the structure will expand to include:

api/
frontend/
infrastructure/

## ⚙️ Getting Started (Development)
1. Clone the Repository
    ```bash
    git clone https://github.com/ChagoCruz/homelab.git
    cd homelab
    ```
2. Create Environment File
Create a .env file:
    ```env
    POSTGRES_DB=homelab
    POSTGRES_USER=homelab
    POSTGRES_PASSWORD=homelab
    ```

3. Start Containers
    ```bash
    docker compose up -d
    ```
4. Verify Running Containers
    ```bash
    docker ps
    ```

The PostgreSQL container should now be running and accessible locally.

## 💾 Data Persistence Strategy
### Production (Ubuntu Server)
- Uses Docker named volumes
- Data stored on physical hardware
- Survives container restarts

### Development (macOS)
- Flexible configuration
- Can use ephemeral volumes for quick iteration
- Data durability is not required

This separation ensures:
Reliable production data
Fast and disposable development workflows

## 🔐 Remote Access
The production server is accessed securely using:
Tailscale VPN
SSH over private network
Port-restricted database access
No public database exposure.

## 🧠 Long-Term Vision
Homelab is the backend foundation for a larger system:
The “Life Terminal”

A personal operating system that:
Tracks financial data
Stores journal entries
Manages job applications
Logs workouts and health metrics
Generates AI summaries and analytics
Runs on a dedicated Raspberry Pi touchscreen

Future goals include:
AI-driven dashboards
Natural language queries over life data
Intelligent daily summaries
Personal knowledge graph integration

## 📈 Roadmap
 - [x] Dockerized PostgreSQL
 - [x] Environment configuration
 - [x] Production server deployment
 - [ ] FastAPI backend container
 - [ ] Database schema versioning
 - [ ] Authentication layer
 - [ ] API documentation (OpenAPI)
 - [ ] AI integration layer
 - [ ] Raspberry Pi UI
 - [ ] Mobile-accessible frontend
 - [ ] Observability & metrics

## 🎯 Why This Project Exists
This project serves three purposes:
- Personal Infrastructure – Owning and understanding my own data systems
- Architectural Practice – Designing production-grade backend systems
- Continuous Learning – Exploring AI integration, containerization, and distributed self-hosted systems

It reflects a belief that software should empower individuals to build their own tools — not just consume them.


## 📄 License

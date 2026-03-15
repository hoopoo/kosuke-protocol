# Kosuke Protocol

**An Intelligence Ecosystem for Meaning Generation in the Age of AI**

Kosuke Protocol is a boundary-crossing intelligence ecosystem designed to generate meaning through interactions between human experience, cultural fragments, and AI systems.

The system models human thinking as a dynamic loop:

**Sampling → Connection → Fluke → Reflection → Meaning**

## Core Concepts

- **Fragment**: A minimal unit of thought (sentence, quote, observation, idea)
- **Sampling**: Retrieving fragments from the ecosystem
- **Fluke**: A low-probability but meaningful conceptual jump between distant fragments
- **Reflection**: Human interpretation of flukes
- **Meaning**: Emergent insight expressed through writing

## Architecture

```
Text Sources
      │
      ▼
Fragment Ingestion (chunking + embedding)
      │
      ▼
Vector Memory (ChromaDB)
      │
      ▼
Sampling Engine (random / semantic / thematic / temporal)
      │
      ▼
Fluke Engine (distance + resonance + tension + context)
      │
      ▼
Reflection Interface (React UI)
      │
      ▼
Living Book Export (Markdown)
```

## Fluke Engine

The core innovation of Kosuke Protocol. The Fluke Engine pairs distant fragments and generates productive conceptual tensions.

### Fluke Score Formula

```
FlukeScore = 0.35 × Distance + 0.30 × CoreResonance + 0.20 × Tension + 0.15 × ContextFit
```

- **Distance** (0.35): Semantic distance between fragment embeddings via cosine distance
- **Core Resonance** (0.30): How much fragments resonate with core concepts (boundary, uncertainty, body, city, meaning, etc.)
- **Tension** (0.20): Productive contradiction potential (AI × body, optimization × uncertainty, etc.)
- **Context Fit** (0.15): Relevance to the user's current exploration

### LLM Integration

When an OpenAI API key is configured, the Fluke Engine uses GPT-4o-mini to generate:
- Tension analysis between fragment pairs
- Reflection prompts that provoke genuine thinking

Falls back to heuristic generation when no API key is available.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI |
| Vector Memory | ChromaDB |
| Frontend | React, TypeScript, Tailwind CSS |
| AI Layer | OpenAI API (optional) |

## Quick Start

### Backend

```bash
cd kosuke-backend
cp .env.example .env  # Add your OPENAI_API_KEY
poetry install
poetry run fastapi dev app/main.py
```

Backend runs at http://localhost:8000

### Frontend

```bash
cd kosuke-frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/fragments` | Add a single fragment |
| POST | `/fragments/ingest` | Ingest and chunk longer text |
| GET | `/fragments` | List all fragments |
| GET | `/fragments/{id}` | Get a fragment |
| DELETE | `/fragments/{id}` | Delete a fragment |
| POST | `/sample` | Sample fragments (random/semantic/thematic/temporal) |
| POST | `/fluke` | Generate a fluke connection |
| POST | `/reflections` | Save a reflection |
| GET | `/reflections` | List reflections |
| POST | `/export/markdown` | Export as Living Book markdown |
| GET | `/stats` | Ecosystem statistics |

## Design Principles

1. Prioritize meaning generation over retrieval accuracy
2. Encourage unexpected connections
3. Maintain human reflection at the center
4. Treat fragments as living components of an ecosystem
5. Avoid over-optimization

## Philosophy

Kosuke Protocol is not designed to answer questions. It is designed to generate meaningful questions. The system prioritizes provocation over explanation.

> *Kosuke Protocol is an intelligence ecosystem that generates meaning through sampling, connection, and fluke.*

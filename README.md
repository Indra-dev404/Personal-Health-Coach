# Health Monitoring Agent

A lightweight health monitoring agent that compresses medical history and wellness data to provide personalized recommendations with efficient processing.

## Features

- Medical history compression with lossless algorithms
- Wellness data tracking (vitals, activities, symptoms)
- Personalized health recommendations
- AES-256 encryption for data security
- HIPAA-compliant access controls

## Installation

```bash
pip install -e .
```

## Development

Install with development dependencies:

```bash
pip install -e ".[dev]"
```

## Testing

Run all tests:

```bash
pytest
```

Run property-based tests only:

```bash
pytest tests/property/
```

Run with coverage:

```bash
pytest --cov=src/health_monitoring_agent
```

## Requirements

- Python 3.9+
- 2GB RAM minimum
- 500MB available storage

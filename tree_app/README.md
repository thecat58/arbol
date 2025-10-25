# Árbol de Decisión - Aplicación

Esta aplicación carga un flujo (PlantUML-like) desde `flujo.txt`, lo parsea a una estructura de árbol y expone una API simple con FastAPI.

Archivos importantes:
- `app/main.py` - servidor FastAPI
- `app/tree_parser.py` - parser minimalista para `flujo.txt`
- `app/static/` - frontend estático

Instalación y ejecución (venv recomendado):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visitar: http://127.0.0.1:8000

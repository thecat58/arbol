from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import json
from datetime import datetime
from app.tree_parser import parse_flujo, Node
import sqlite3
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data.db')

app = FastAPI(title="Asistente de Selección Tecnológica")

# Modelos de datos
class Answer(BaseModel):
    questionId: str
    answerId: str
    phase: int

class ProjectSession(BaseModel):
    id: str
    answers: List[Answer]
    timestamp: datetime

class Recommendation(BaseModel):
    frontend: List[str]
    backend: List[str]
    database: List[str]
    architecture: List[str]
    methodology: List[str]
    security: List[str]

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), 'static')
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Load tree at startup
ROOT = None

@app.on_event("startup")
@app.on_event("startup")
@app.on_event("startup")
@app.on_event("startup")
def load_tree():
    global ROOT

    posibles_rutas = [
        os.path.join(os.path.dirname(__file__), 'flujo.txt'),
        os.path.join(os.path.dirname(__file__), '..', 'flujo.txt'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'flujo.txt'),
        os.path.join(Path.cwd(), 'flujo.txt'),
    ]

    flujo_path = None
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            flujo_path = ruta
            break

    if flujo_path is None:
        raise RuntimeError("No se encontró flujo.txt en ninguna de las rutas esperadas")

    print(f"✅ Archivo flujo.txt encontrado en: {flujo_path}")

    with open(flujo_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # 🔹 Aquí se construye el árbol base
   # 🔹 Aquí se construye el árbol base
    ROOT = parse_flujo(text)

    # 🔹 Añadir recomendaciones globales al árbol
    frontend_rec = Node("rec_frontend", "React + Vite (Frontend rápido y moderno)", "recommendation")
    backend_rec = Node("rec_backend", "Node.js con Express (Backend ágil y escalable)", "recommendation")
    db_rec = Node("rec_db", "PostgreSQL (Base de datos relacional confiable)", "recommendation")
    arch_rec = Node("rec_arch", "Microservicios con escalado horizontal", "recommendation")
    meth_rec = Node("rec_meth", "Scrum o Kanban (metodologías ágiles)", "recommendation")
    sec_rec = Node("rec_sec", "Implementa JWT, HTTPS y backups regulares", "recommendation")

    # 🔹 Crear un nodo final de recomendaciones generales
    final_recs = Node("phase_final", "📌 Recomendaciones generales", "phase")
    final_recs.add_child(frontend_rec)
    final_recs.add_child(backend_rec)
    final_recs.add_child(db_rec)
    final_recs.add_child(arch_rec)
    final_recs.add_child(meth_rec)
    final_recs.add_child(sec_rec)

    ROOT.add_child(final_recs)

    # 🔹 Conectar al árbol raíz
    ROOT.add_child(final_recs)

    # Inicializar base de datos
    init_db()


def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # create database and tables if not exist
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        timestamp TEXT
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        question_id TEXT,
        answer_id TEXT,
        phase INTEGER,
        FOREIGN KEY(session_id) REFERENCES sessions(id)
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        category TEXT,
        recommendation TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(id)
    )
    ''')
    conn.commit()
    conn.close()

@app.get("/tree")
def get_tree():
    global ROOT
    if ROOT is None:
        load_tree()
    if ROOT is None:
        raise HTTPException(status_code=500, detail="Tree not loaded")
    return JSONResponse(content=ROOT.to_dict())

@app.get("/decision")
def get_decision(side: str = "left"):
    if ROOT is None:
        raise HTTPException(status_code=500, detail="Tree not loaded")
    side = side.lower()
    if side not in ("left", "right"):
        raise HTTPException(status_code=400, detail="side must be 'left' or 'right'")
    node = ROOT.get_side(side)
    if node is None:
        raise HTTPException(status_code=404, detail="Side not found")
    return JSONResponse(content=node.to_dict())

class Question(BaseModel):
    id: str
    text: str
    options: List[Dict[str, str]]

@app.get("/questions/{phase}")
async def get_questions(phase: int):
    global ROOT
    if ROOT is None:
        load_tree()
    if ROOT is None:
        raise HTTPException(status_code=500, detail="Tree not loaded")
    
    questions = ROOT.get_phase_questions(phase)
    
    result = []
    for q in questions:
        options = []
        for child in q.children:
            if child.node_type == "option":
                display_text = child.text
                if getattr(child, 'children', None):
                    recs = [c.text for c in child.children if getattr(c, 'node_type', '') == 'recommendation']
                    if recs:
                        display_text = ' / '.join(recs)
                option_data = {"id": child.id, "text": display_text, "label": child.text}
                if child.metadata:
                    option_data["metadata"] = child.metadata
                options.append(option_data)
        
        question_data = {
            "id": q.id,
            "text": q.text,
            "options": options,
            "phase": phase
        }
        if q.metadata:
            question_data["metadata"] = q.metadata
        result.append(question_data)
    
    return result

@app.post("/evaluate")
async def evaluate_answers(answers: List[Answer]):
    if ROOT is None:
        raise HTTPException(status_code=500, detail="Tree not loaded")
    
    # Helper: find node by id
    def find_node(node: Node, node_id: str) -> Optional[Node]:
        if node.id == node_id:
            return node
        for c in node.children:
            found = find_node(c, node_id)
            if found:
                return found
        return None
    def categorize(text: str) -> str:
        t = text.lower()
        keywords = {
            'frontend': ['react', 'vue', 'angular', 'svelte', 'html', 'css', 'spa', 'webgl', 'canvas', 'frontend', 'ui', 'ux', 'tailwind', 'bootstrap'],
            'backend': ['node', 'django', 'flask', 'spring', 'java', 'go', 'rust', 'php', 'express', 'laravel', 'backend', 'api', 'servidor'],
            'database': ['sql', 'mysql', 'postgres', 'postgresql', 'mongodb', 'firebase', 'hadoop', 'spark', 'database', 'db', 'sqlite', 'oracle', 'nosql'],
            'architecture': ['microserv', 'monolit', 'arquitectura', 'cloud', 'kubernetes', 'docker', 'serverless', 'cloud-native', 'infraestructura', 'scalable'],
            'methodology': ['scrum', 'kanban', 'waterfall', 'mvp', 'metodolog', 'ágil', 'agile', 'iterativo', 'devops'],
            'security': ['oauth', 'jwt', 'ssl', 'cifrado', 'security', 'compliance', 'iso', 'auth', 'seguridad', 'sso', 'protección'],
        }

        for category, keys in keywords.items():
            if any(k in t for k in keys):
                return category

        # Si no se reconoce, devolver 'other' en lugar de 'backend'
        return 'other'

    # Collect recommendation texts from selected options
    rec_texts = []
    for ans in answers:
        opt = find_node(ROOT, ans.answerId)
        if opt:
            # collect recommendation-type children under the option
            for child in opt.children:
                if getattr(child, 'node_type', '') == 'recommendation':
                    rec_texts.append(child.text)

    if not rec_texts:
        # Si no hay recomendaciones derivadas, usar las globales que agregamos al árbol
        global_recs = [
            "React + Vite (Frontend rápido y moderno)",
            "Node.js con Express (Backend ágil y escalable)",
            "PostgreSQL (Base de datos relacional confiable)",
            "Microservicios con escalado horizontal",
            "Scrum o Kanban (metodologías ágiles)",
            "Implementa JWT, HTTPS y backups regulares"
        ]
        rec_texts.extend(global_recs)

    # Deduplicate preserving order
    seen = set()
    rec_texts_unique = []
    for r in rec_texts:
        if r not in seen:
            seen.add(r)
            rec_texts_unique.append(r)

    # categorize
    recommendations: Dict[str, List[str]] = {
        'frontend': [],
        'backend': [],
        'database': [],
        'architecture': [],
        'methodology': [],
        'security': [],
        'other': []  # ← agregamos esta categoría extra
    }

    for r in rec_texts_unique:
        cat = categorize(r)
        if cat not in recommendations:
            recommendations["other"].append(r)
        else:
            recommendations[cat].append(r)


    # RULE-BASED ENRICHMENT: apply more precise recommendations based on answers
    # Helper to get option text and question text
    def get_option_and_question_text(answer: Answer):
        opt_node = find_node(ROOT, answer.answerId)
        if not opt_node:
            return None, None
        # find parent question by searching nodes whose children include opt_node
        parent_q = None
        def find_parent(node: Node):
            nonlocal parent_q
            for c in node.children:
                if c is opt_node:
                    parent_q = node
                    return True
                if find_parent(c):
                    return True
            return False
        find_parent(ROOT)
        return opt_node.text, (parent_q.text if parent_q else None)

    for ans in answers:
        opt_text, q_text = get_option_and_question_text(ans)
        if not opt_text or not q_text:
            continue
        qt = q_text.lower()
        ot = opt_text.lower()

        # Tipo de Aplicación
        if 'tipo' in qt and 'aplicaci' in qt:
            if 'web' in ot:
                recommendations['frontend'].extend(['React', 'Vue.js', 'HTML5/CSS3'])
                recommendations['backend'].extend(['Node.js (Express)', 'Django (Python)'])
                recommendations['database'].append('PostgreSQL')
                recommendations['architecture'].append('Monolito modulable / Microservicios según escala')
            elif 'móvil' in ot or 'movil' in ot:
                recommendations['frontend'].extend(['React Native', 'Flutter'])
                recommendations['backend'].append('Node.js / Django')
                recommendations['database'].append('PostgreSQL / Firebase (según necesidades)')
                recommendations['architecture'].append('Backend escalable (Microservicios si es enterprise)')
            elif 'escritorio' in ot:
                recommendations['frontend'].append('Electron / Tauri')
                recommendations['backend'].append('Go / .NET / Java')
            elif 'híbrida' in ot:
                recommendations['frontend'].extend(['Ionic', 'Capacitor', 'React Native'])
                recommendations['backend'].append('Node.js')
            elif 'enterprise' in ot or 'enterpris' in ot:
                recommendations['backend'].extend(['Java (Spring)', 'Go'])
                recommendations['architecture'].append('Arquitectura enterprise, alta disponibilidad')

        # Ámbito Principal
        if 'ámbito' in qt or 'ambito' in qt:
            # accept multiple user-friendly synonyms
            if any(k in ot for k in ['b2c', 'consumidor', 'consumo', 'cliente', 'público', 'publico', 'público general', 'público general']):
                recommendations['frontend'].append('SPA (React/Vue) con enfoque UX y rendimiento')
                recommendations['backend'].append('Node.js con CDN y caching')
                recommendations['methodology'].append('Ágil (Ciclos cortos, MVP)')
            elif any(k in ot for k in ['b2b', 'empresa', 'empresas', 'negocio', 'negocios']):
                recommendations['backend'].append('Java Spring / .NET para mantenibilidad y SLAs')
                recommendations['security'].append('OAuth2, SSO, cumplimiento de normativas')
                recommendations['database'].append('PostgreSQL / Oracle')
            elif any(k in ot for k in ['interna', 'uso interno', 'herramienta interna', 'interno']):
                recommendations['backend'].append('Python (Django/Flask) para rapidez de desarrollo')
                recommendations['database'].append('SQLite / PostgreSQL según tamaño')
            elif any(k in ot for k in ['educacional', 'educacion', 'formacion', 'formación']):
                recommendations['frontend'].append('React/Vanilla + accesibilidad (a11y)')
                recommendations['methodology'].append('MVP + feedback de usuarios')
            elif any(k in ot for k in ['comercio', 'comercio electrónico', 'e-commerce', 'ventas', 'ventas en línea']):
                # E-commerce specific suggestions
                recommendations['frontend'].append('React + librerías de comercio (o Headless CMS)')
                recommendations['backend'].append('Node.js / Django con integración de pasarelas de pago (Stripe/PayPal)')
                recommendations['database'].append('PostgreSQL / Managed DB con respaldo y escalado')
                recommendations['architecture'].append('CDN, caching, búsqueda (ElasticSearch), escalado horizontal')
                recommendations['security'].append('PCI-DSS considerations, HTTPS, protección contra fraudes')

        # Característica prioritaria
        if 'característica' in qt or 'caracteristica' in qt:
            if 'velocidad' in ot or 'rápido' in ot:
                recommendations['backend'].append('Node.js / Serverless (deploy rápido)')
                recommendations['methodology'].append('Ciclos cortos, prototipado rápido')
            if 'alto rendimiento' in ot or 'rendimiento' in ot:
                recommendations['backend'].append('Go / Rust')
                recommendations['architecture'].append('Servicios optimizados, benchmarking')
            if 'escalabilidad' in ot:
                recommendations['architecture'].append('Microservicios + Kubernetes')

        # Tipo de interfaz
        if 'interfaz' in qt:
            if 'simple' in ot:
                recommendations['frontend'].append('HTML/CSS/JS simple')
            if 'interactiva' in ot:
                recommendations['frontend'].append('SPA (React/Vue)')
            if 'rica' in ot:
                recommendations['frontend'].append('WebGL / Canvas')
            if 'tiempo real' in ot or 'real' in ot:
                recommendations['architecture'].append('Sockets / WebRTC (ej: Socket.IO)')

        # Gestión de datos
        if 'estructura' in qt or 'estructura de datos' in qt:
            if 'estructurada' in ot:
                recommendations['database'].append('RDBMS (PostgreSQL, MySQL)')
            if 'semi' in ot:
                recommendations['database'].append('MongoDB / Firebase')
            if 'no estructurada' in ot or 'no estructur' in ot:
                recommendations['database'].append('Data lake / almacenamiento en blob (S3)')

        # Volumen
        if 'volumen' in qt:
            if 'pequeño' in ot:
                recommendations['database'].append('DB local o soluciones gratuitas (SQLite, managed small DB)')
            if 'grande' in ot or 'masivo' in ot:
                recommendations['architecture'].append('Escalado horizontal, shards, particionado')

        # Seguridad e integraciones
        if 'integraciones' in qt or 'pagos' in qt:
            if 'pagos' in ot or 'stripe' in ot or 'paypal' in ot:
                recommendations['backend'].append('Integración con Stripe/PayPal SDKs')
        if 'seguridad' in qt:
            if 'enterprise' in ot or 'compliance' in ot or 'iso' in ot:
                recommendations['security'].append('Compliance ISO, SSO, auditoría y logging')
            if 'cifrado' in ot or 'extremo' in ot:
                recommendations['security'].append('Cifrado extremo a extremo, gestión de claves')

    # Deduplicate recommendations per category
    for k in recommendations:
        seen_k = set()
        out = []
        for it in recommendations[k]:
            if it not in seen_k:
                seen_k.add(it)
                out.append(it)
        recommendations[k] = out

    # persist session + answers + recommendations to sqlite
    session_id = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR IGNORE INTO sessions(id, timestamp) VALUES(?, ?)', (session_id, datetime.utcnow().isoformat()))
        for a in answers:
            cur.execute('INSERT INTO answers(session_id, question_id, answer_id, phase) VALUES(?, ?, ?, ?)',
                        (session_id, a.questionId, a.answerId, a.phase))
        for cat, items in recommendations.items():
            for it in items:
                cur.execute('INSERT INTO recommendations(session_id, category, recommendation) VALUES(?, ?, ?)',
                            (session_id, cat, it))
        conn.commit()
    finally:
        conn.close()

    return Recommendation(**recommendations)

@app.post("/save-session")
async def save_session(session: ProjectSession):
    # Save session into SQLite DB (and keep JSON file as optional backup)
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR IGNORE INTO sessions(id, timestamp) VALUES(?, ?)', (session.id, session.timestamp.isoformat()))
        for a in session.answers:
            cur.execute('INSERT INTO answers(session_id, question_id, answer_id, phase) VALUES(?, ?, ?, ?)',
                        (session.id, a.questionId, a.answerId, a.phase))
        conn.commit()
    finally:
        conn.close()

    # optional: also append to sessions.json for human-readable backup
    try:
        sessions_file = "sessions.json"
        sessions = []
        if os.path.exists(sessions_file):
            with open(sessions_file, 'r') as f:
                sessions = json.load(f)
        session_dict = session.dict()
        session_dict["timestamp"] = session_dict["timestamp"].isoformat()
        sessions.append(session_dict)
        with open(sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)
    except Exception:
        # non-fatal if file write fails
        pass

    return {"status": "success", "session_id": session.id}

@app.get("/phases")
def get_phases():
    global ROOT
    if ROOT is None:
        load_tree()
    if ROOT is None:
        raise HTTPException(status_code=500, detail="Tree not loaded")
    phases = []
    for node in ROOT.children:
        # buscar nodos de tipo 'phase'
        if getattr(node, 'node_type', '') == 'phase' or node.id.startswith('phase'):
            phases.append({"id": node.id, "text": node.text})
    return phases

@app.get("/")
def index():
    static_index = os.path.join(os.path.dirname(__file__), 'static', 'index.html')
    return FileResponse(static_index, media_type='text/html')

@app.get("/api/questions")
def api_questions():
    global ROOT
    if ROOT is None:
        load_tree()
    if ROOT is None:
        raise HTTPException(status_code=500, detail="Tree not loaded")

    # mapeo coloquial para opciones específicas
    colloquial_map = {
        "B2C": "Consumidores — gente/usuarios finales",
        "B2B": "Empresas — clientes/organizaciones",
        "Interna": "Uso interno — solo para tu equipo/empresa"
    }

    out = []
    for phase in ROOT.children:
        node = phase.to_dict()
        # recorrer preguntas y opciones y aplicar texto coloquial si corresponde
        for child in node.get("children", []):
            if child.get("type") == "question":
                for opt in child.get("children", []):
                    if opt.get("type") == "option":
                        txt = opt.get("text", "")
                        if txt in colloquial_map:
                            # reemplaza el texto mostrado por una versión más coloquial
                            opt["text"] = colloquial_map[txt]
                            # opcional: dejar el valor original en otra clave
                            opt["original_text"] = txt
        out.append(node)
    return out

if __name__ == '__main__':
    uvicorn.run('app.main:app', host='127.0.0.1', port=8000, reload=True)

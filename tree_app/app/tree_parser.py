import re
from typing import Optional, List, Dict


class Node:
    def __init__(self, id: str, text: str, node_type: str = "question"):
        self.id = id
        self.text = text
        self.node_type = node_type  # root, phase, question, option, recommendation
        self.children: List["Node"] = []
        self.phase: Optional[int] = None
        self.metadata: Dict = {}
    def get_recommendations(self) -> dict:
        """
        Recorre el árbol y devuelve todas las recomendaciones encontradas,
        agrupadas por categoría (frontend, backend, etc.),
        junto con una breve descripción de su propósito.
        """
        recs = {
            'frontend': [],
            'backend': [],
            'database': [],
            'architecture': [],
            'methodology': [],
            'security': []
        }

        # Diccionario de descripciones para las tecnologías más comunes
        tech_descriptions = {
            'React': 'Librería JavaScript para construir interfaces web interactivas (Frontend).',
            'Vue': 'Framework progresivo para interfaces web rápidas y reactivas (Frontend).',
            'Angular': 'Framework completo de Google para aplicaciones SPA (Frontend).',
            'HTML': 'Lenguaje base para el contenido de páginas web (Frontend).',
            'CSS': 'Lenguaje para estilos y diseño visual en la web (Frontend).',
            'Node.js': 'Entorno de ejecución de JavaScript para construir servidores (Backend).',
            'Django': 'Framework de Python para desarrollo rápido de aplicaciones web seguras (Backend).',
            'Flask': 'Microframework de Python para APIs y servicios pequeños (Backend).',
            'Spring': 'Framework Java muy usado en entornos empresariales (Backend).',
            'Go': 'Lenguaje de Google enfocado en rendimiento y concurrencia (Backend).',
            'PostgreSQL': 'Sistema de gestión de base de datos relacional potente y open-source (Base de datos).',
            'MySQL': 'Base de datos relacional ampliamente usada (Base de datos).',
            'MongoDB': 'Base de datos NoSQL orientada a documentos (Base de datos).',
            'Firebase': 'Plataforma de Google con base de datos en tiempo real y autenticación integrada (Backend/DB).',
            'Microservicios': 'Arquitectura que divide la app en servicios independientes escalables (Arquitectura).',
            'Monolito': 'Arquitectura centralizada, más simple pero menos escalable (Arquitectura).',
            'Scrum': 'Metodología ágil basada en iteraciones cortas y roles definidos (Metodología).',
            'Kanban': 'Metodología ágil visual con enfoque en flujo continuo de tareas (Metodología).',
            'OAuth2': 'Estándar para autenticación segura entre servicios (Seguridad).',
            'JWT': 'Mecanismo de autenticación basado en tokens seguros (Seguridad).',
            'SSL': 'Protocolo de cifrado para proteger las comunicaciones (Seguridad).',
        }

        # Clasificador de categorías
        def categorize(text: str) -> str:
            t = text.lower()
            if any(k in t for k in ['react', 'vue', 'html', 'css', 'angular', 'frontend']):
                return 'frontend'
            if any(k in t for k in ['node', 'django', 'flask', 'spring', 'java', 'go', 'backend']):
                return 'backend'
            if any(k in t for k in ['sql', 'mysql', 'postgres', 'mongodb', 'database', 'firebase', 'db']):
                return 'database'
            if any(k in t for k in ['microserv', 'arquitectura', 'monolit', 'cloud']):
                return 'architecture'
            if any(k in t for k in ['scrum', 'kanban', 'metodolog']):
                return 'methodology'
            if any(k in t for k in ['oauth', 'jwt', 'ssl', 'security', 'cifrado']):
                return 'security'
            return 'backend'

        # Recorre el árbol y recolecta recomendaciones
        def traverse(node):
            if getattr(node, 'node_type', '') == 'recommendation':
                cat = categorize(node.text)
                recs[cat].append(node.text)
            for child in getattr(node, 'children', []):
                traverse(child)

        traverse(self)

        # Eliminar duplicados y agregar descripción
        for category, items in recs.items():
            unique = []
            seen = set()
            for it in items:
                if it not in seen:
                    seen.add(it)
                    desc = tech_descriptions.get(it.strip(), f"Tecnología o práctica relacionada con {category}.")
                    unique.append({
                        "nombre": it,
                        "descripcion": desc,
                        "categoria": category.capitalize()
                    })
            recs[category] = unique

        return recs


    def add_child(self, node: "Node"):
        self.children.append(node)

    def to_dict(self) -> Dict:
        res = {
            "id": self.id,
            "text": self.text,
            "type": self.node_type,
            "children": [c.to_dict() for c in self.children],
        }
        if self.phase is not None:
            res["phase"] = self.phase
        if self.metadata:
            res["metadata"] = self.metadata
        return res


def parse_flujo(text: str) -> Node:
    """
    Parsea un flujo PlantUML simplificado y construye un árbol:
      - partition -> nodo 'phase'
      - líneas que terminan en '?' -> preguntas (question)
      - if(...) then (...) / elseif(...) -> opciones (option) como hijos de la última pregunta
      - otras acciones ':texto;' -> recommendations (hijo de la última opción o de la fase)
    Soporta tanto ':¿Qué...?;' como ':Pregunta 1: Texto?;'
    """
    lines = text.splitlines()
    root = Node("root", "root", node_type="root")

    partition_re = re.compile(r'partition\s*"([^"]+)"', re.IGNORECASE)
    # acepta preguntas como ':¿Texto?;' o ':Pregunta 1: Texto?;'
    question_re = re.compile(r":\s*(?:Pregunta\s*\d*\s*:)?\s*(¿?\s*.+?\?)\s*;", re.IGNORECASE)
    # if (X) then (LABEL)
    if_then_re = re.compile(r"if\s*\(([^)]+)\)\s*then\s*\(([^)]+)\)", re.IGNORECASE)
    # elseif (X) then (LABEL)
    elseif_re = re.compile(r"elseif\s*\(([^)]+)\)\s*then\s*\(([^)]+)\)", re.IGNORECASE)
    # acción/resultado general ':Texto;'
    action_re = re.compile(r":\s*([^;]+);")

    current_phase: Optional[Node] = None
    phase_num = 0
    last_question: Optional[Node] = None
    last_option: Optional[Node] = None

    qcount = 0
    optcount = 0
    recount = 0

    for raw in lines:
        ln = raw.strip()
        if not ln or ln.startswith("'"):
            continue

        # nueva partición -> fase
        m_part = partition_re.search(ln)
        if m_part:
            title = m_part.group(1).strip()
            m_ph = re.search(r"FASE\s*(\d+)", title.upper())
            if m_ph:
                phase_num = int(m_ph.group(1))
            else:
                phase_num += 1
            current_phase = Node(f"phase{phase_num}", title, node_type="phase")
            current_phase.phase = phase_num
            root.add_child(current_phase)
            last_question = None
            last_option = None
            continue

        # pregunta explícita
        m_q = question_re.search(ln)
        if m_q:
            qtext = m_q.group(1).strip()
            qtext = qtext.lstrip("¿").strip()
            qcount += 1
            qnode = Node(f"q{phase_num}_{qcount}", qtext, node_type="question")
            qnode.phase = phase_num
            if current_phase:
                current_phase.add_child(qnode)
            else:
                root.add_child(qnode)
            last_question = qnode
            last_option = None
            continue

        # if (...) then (LABEL)
        m_if = if_then_re.search(ln)
        if m_if and last_question:
            label = m_if.group(2).strip()
            optcount += 1
            opt = Node(f"o{phase_num}_{optcount}", label, node_type="option")
            last_question.add_child(opt)
            last_option = opt
            continue

        # elseif (...) then (LABEL)
        m_elseif = elseif_re.search(ln)
        if m_elseif and last_question:
            label = m_elseif.group(2).strip()
            optcount += 1
            opt = Node(f"o{phase_num}_{optcount}", label, node_type="option")
            last_question.add_child(opt)
            last_option = opt
            continue

        # acción / resultado general
        m_act = action_re.search(ln)
        if m_act:
            text_act = m_act.group(1).strip()
            low = text_act.lower()
            # ignorar controles y metadatos comunes
            if low.startswith("inicio") or low.startswith("stop") or low.startswith("end") or low.startswith("title") or low.startswith("endif"):
                continue
            recount += 1
            rec = Node(f"r{phase_num}_{recount}", text_act, node_type="recommendation")
            if last_option:
                last_option.add_child(rec)
            elif last_question:
                # si no hay opción, pero hay pregunta, agregar a la pregunta
                last_question.add_child(rec)
            elif current_phase:
                # si no hay opción ni pregunta, pero hay fase, agregar a la fase
                current_phase.add_child(rec)
            else:
                # por último, agregar al root
                root.add_child(rec)
            continue

    return root

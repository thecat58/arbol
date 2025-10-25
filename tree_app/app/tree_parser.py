import re
from typing import Optional, List, Dict

class Node:
    def __init__(self, id: str, text: str, node_type: str = "question"):
        self.id = id
        self.text = text
        self.node_type = node_type  # question, option, recommendation
        self.children: List[Node] = []
        self.phase: Optional[int] = None
        self.metadata: Dict = {}

    def add_child(self, node: 'Node'):
        self.children.append(node)

    def to_dict(self) -> Dict:
        result = {
            "id": self.id,
            "text": self.text,
            "type": self.node_type,
            "children": [c.to_dict() for c in self.children]
        }
        if self.phase:
            result["phase"] = self.phase
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def get_phase_questions(self, phase: int) -> List['Node']:
        """Obtiene todas las preguntas de una fase específica."""
        questions = []
        if self.phase == phase and self.node_type == "question":
            questions.append(self)
        for child in self.children:
            questions.extend(child.get_phase_questions(phase))
        return questions

    def get_recommendations(self) -> Dict[str, str]:
        """Recopila todas las recomendaciones basadas en las respuestas seleccionadas."""
        recommendations = {
            "frontend": [],
            "backend": [],
            "database": [],
            "architecture": [],
            "methodology": [],
            "security": []
        }
        
        def collect_recommendations(node: 'Node'):
            if node.node_type == "recommendation":
                category = node.metadata.get("category", "general")
                if category in recommendations:
                    recommendations[category].append(node.text)
            for child in node.children:
                collect_recommendations(child)
        
        collect_recommendations(self)
        return recommendations


def parse_flujo(text: str) -> Node:
    """
    Parser improved to extract phases, questions and options from the PlantUML-like flujo.
    Produces a tree where root.children are phase nodes, phase nodes contain question nodes,
    and question nodes contain option nodes (which may contain recommendation children).
    """
    lines = text.splitlines()
    root = Node('root', 'root', node_type='root')

    current_phase_node: Optional[Node] = None
    phase_num = 0
    last_question: Optional[Node] = None
    last_option: Optional[Node] = None

    # counters for ids
    qcount = 0
    optcount = 0
    actcount = 0

    partition_re = re.compile(r"partition\s*\"([^\"]+)\"")
    question_re = re.compile(r":\s*Pregunta\s*\d*:\s*([^;\?]+)\??;")
    if_then_re = re.compile(r"if \(([^)]+)\)\s*then\s*\(([^)]+)\)")
    elseif_re = re.compile(r"elseif\s*\(([^)]+)\)")
    action_re = re.compile(r":([^;]+);")

    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("'"):
            continue

        # partition -> phase
        m_part = partition_re.search(ln)
        if m_part:
            title = m_part.group(1).strip()
            # try to extract phase number from title
            m_phase = re.search(r"FASE\s*(\d+)", title.upper())
            if m_phase:
                phase_num = int(m_phase.group(1))
            else:
                phase_num += 1
            current_phase_node = Node(f'phase{phase_num}', title, node_type='phase')
            current_phase_node.phase = phase_num
            root.add_child(current_phase_node)
            last_question = None
            last_option = None
            continue

        # question
        m_q = question_re.search(ln)
        if m_q:
            qtext = m_q.group(1).strip()
            qcount += 1
            qnode = Node(f'q{phase_num}_{qcount}', qtext, node_type='question')
            qnode.phase = phase_num
            if current_phase_node:
                current_phase_node.add_child(qnode)
            else:
                root.add_child(qnode)
            last_question = qnode
            last_option = None
            continue

        # if ... then (OPTION)
        m_if = if_then_re.search(ln)
        if m_if and last_question:
            opt_label = m_if.group(2).strip()
            optcount += 1
            opt = Node(f'o{phase_num}_{optcount}', opt_label, node_type='option')
            last_question.add_child(opt)
            last_option = opt
            continue

        # elseif (OPTION)
        m_elseif = elseif_re.search(ln)
        if m_elseif and last_question:
            label = m_elseif.group(1).strip()
            optcount += 1
            opt = Node(f'o{phase_num}_{optcount}', label, node_type='option')
            last_question.add_child(opt)
            last_option = opt
            continue

        # general action/result lines like :Selecciona WEB;
        m_act = action_re.search(ln)
        if m_act:
            text = m_act.group(1).strip()
            # ignore question markers and start/stop
            if text.lower().startswith('pregunta') or text.lower().startswith('inicio'):
                continue
            actcount += 1
            rec = Node(f'r{phase_num}_{actcount}', text, node_type='recommendation')
            if last_option:
                last_option.add_child(rec)
            elif current_phase_node:
                current_phase_node.add_child(rec)
            else:
                root.add_child(rec)
            continue

    return root

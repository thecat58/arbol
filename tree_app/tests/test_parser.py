from app.tree_parser import parse_flujo


def test_parse_basic():
    text = ":Pregunta 1: Tipo de Aplicación?;\nif (WEB) then (WEB)\n:Selecciona WEB;"
    root = parse_flujo(text)
    assert root is not None
    assert len(root.children) >= 1

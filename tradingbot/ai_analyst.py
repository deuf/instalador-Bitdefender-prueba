"""Análisis de noticias con IA (Claude) — sentimiento REAL, no contar palabras.

En vez del léxico básico del analizador, esto envía los titulares a Claude, que
los LEE y entiende el contexto (distingue "riesgo menor" de "se desploma por
pérdidas"). Devuelve un sentimiento numérico, una etiqueta y un resumen razonado.

Requiere:
  - pip install anthropic
  - una clave en la variable de entorno ANTHROPIC_API_KEY

⚠️ Es una herramienta de APOYO. Claude entiende las noticias mucho mejor que
contar palabras, pero NO predice el precio: cuando tú lees una noticia, los
grandes fondos ya la han operado. Úsalo para decidir mejor, no como oráculo.

Uso directo (para probar):
    python -m tradingbot.ai_analyst AAPL
"""

from __future__ import annotations

import json
import os

# Modelo por defecto. Puedes cambiarlo con AI_MODEL (p.ej. claude-haiku-4-5 para
# abaratar, claude-opus-4-8 para máxima calidad).
DEFAULT_MODEL = os.getenv("AI_MODEL", "claude-opus-4-8")

# Esquema de salida estructurada: obliga a Claude a responder en este formato.
_SCHEMA = {
    "type": "object",
    "properties": {
        "sentimiento": {"type": "number", "description": "de -1 (muy negativo) a 1 (muy positivo)"},
        "etiqueta": {"type": "string", "enum": ["positivo", "neutral", "negativo"]},
        "resumen": {"type": "string", "description": "una o dos frases explicando el porqué"},
        "riesgos": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["sentimiento", "etiqueta", "resumen", "riesgos"],
    "additionalProperties": False,
}


def analyze_news(symbol: str, titles: list[str], model: str | None = None) -> dict | None:
    """Analiza titulares con Claude. Devuelve dict con sentimiento/etiqueta/resumen/riesgos."""
    if not titles:
        return None
    try:
        import anthropic
    except ImportError as exc:
        raise ImportError("Falta 'anthropic'. Instala con: pip install anthropic") from exc

    client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno
    headlines = "\n".join(f"- {t}" for t in titles)
    prompt = (
        f"Eres un analista financiero. Evalúa el sentimiento de mercado de estos "
        f"titulares recientes sobre {symbol}, desde el punto de vista de un inversor. "
        f"Recuerda que una noticia suele estar ya descontada por el mercado cuando se "
        f"publica, así que valora el impacto NETO esperado, no solo el tono.\n\n"
        f"Titulares:\n{headlines}"
    )
    resp = client.messages.create(
        model=model or DEFAULT_MODEL,
        max_tokens=1024,
        system="Responde de forma objetiva y concisa, solo con el análisis pedido.",
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
    )
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


def main() -> None:
    import sys

    from .analyzer import fetch_news_titles

    if len(sys.argv) < 2:
        raise SystemExit("Uso: python -m tradingbot.ai_analyst SIMBOLO")
    symbol = sys.argv[1]
    titles = fetch_news_titles(symbol)
    if not titles:
        print(f"No se encontraron titulares para {symbol}.")
        return
    print(f"\n{len(titles)} titulares de {symbol}:")
    for t in titles:
        print(f"  - {t}")
    result = analyze_news(symbol, titles)
    print("\nAnálisis de Claude:")
    print(f"  Sentimiento : {result['sentimiento']:+.2f}  ({result['etiqueta']})")
    print(f"  Resumen     : {result['resumen']}")
    if result["riesgos"]:
        print("  Riesgos     :")
        for r in result["riesgos"]:
            print(f"    - {r}")
    print()


if __name__ == "__main__":
    main()

from pipeline.componentUtilities.schemas import Triple
from typing import List, Optional

# ---------------------------------------------------------------------------
# Rule-based conversion (no LLM)
# ---------------------------------------------------------------------------


def _clean_uri_part(text: str) -> str:
    """Normalize for use in URIs: strip, spaces to underscores, remove quotes (invalid in SPARQL IRIs)."""
    s = text.strip().replace(" ", "_")
    s = s.replace('"', "").replace("'", "")
    return s


def _format_uri_rule_based(text: str, base_url: str) -> str:
    cleaned = _clean_uri_part(text)
    if cleaned.startswith("http"):
        return f"<{cleaned}>"
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return cleaned
    return f"<{base_url}{cleaned}>"


def _format_object_rule_based(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("http"):
        return f"<{cleaned}>"
    is_numeric = cleaned.replace(".", "", 1).replace("-", "", 1).isdigit()
    is_quoted = cleaned.startswith('"') and cleaned.endswith('"')
    if is_numeric or is_quoted:
        return f'"{cleaned}"' if not is_quoted else cleaned
    return _format_uri_rule_based(text, "http://dbpedia.org/resource/")


def convert_to_dbpedia_format_rule_based(triples: List[Triple]) -> List[str]:
    ntriples = []
    for t in triples:
        s = _format_uri_rule_based(t.subject, "http://dbpedia.org/resource/")
        p = _format_uri_rule_based(t.predicate, "http://dbpedia.org/ontology/")
        o = _format_object_rule_based(t.object)
        ntriples.append(f"{s} {p} {o} .")
    return ntriples


# ---------------------------------------------------------------------------
# LLM-based conversion: one LLM call per triple -> one DBpedia N-Triple line
# ---------------------------------------------------------------------------

_FORMAT_TRIPLE_PROMPT_KEY = "format_triple_to_dbpedia"


def _format_triple_to_dbpedia_llm(t: Triple, model_config: dict) -> str:
    """Ask the LLM to convert a single triple (subject, predicate, object) into one valid DBpedia N-Triple line."""
    from pipeline.prompts.prompts import prompts
    from pipeline.utility import create_prompt
    from pipeline.componentUtilities.llm import call_LLM

    user_tpl = prompts[_FORMAT_TRIPLE_PROMPT_KEY]["user"]
    system_tpl = prompts[_FORMAT_TRIPLE_PROMPT_KEY]["system"]
    user_prompt = create_prompt(user_tpl, "{subject}", t.subject)
    user_prompt = create_prompt(user_prompt, "{predicate}", t.predicate)
    user_prompt = create_prompt(user_prompt, "{object}", t.object)
    system_prompt = create_prompt(system_tpl, "{subject}", t.subject)
    system_prompt = create_prompt(system_prompt, "{predicate}", t.predicate)
    system_prompt = create_prompt(system_prompt, "{object}", t.object)
    line = call_LLM(user_prompt, system_prompt, model_config).strip()
    if line and not line.endswith("."):
        line = line.rstrip() + " ."
    return line


def convert_to_dbpedia_format(
    triples: List[Triple], model_config: Optional[dict] = None
) -> List[str]:
    """Convert triples to DBpedia N-Triples. When model_config is provided, use LLM (one call per triple); else rule-based."""
    if model_config is None:
        return convert_to_dbpedia_format_rule_based(triples)

    ntriples = []
    for t in triples:
        line = _format_triple_to_dbpedia_llm(t, model_config)
        ntriples.append(line)
    return ntriples

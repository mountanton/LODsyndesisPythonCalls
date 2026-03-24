import requests
from SPARQLWrapper import SPARQLWrapper, JSON

def lodsyndesis_facts(entity, max_triples=500, same_as="No"):
    url = (
        "https://demos.isl.ics.forth.gr/lodsyndesis/rest-api/allFacts"
        f"?uri={entity}&maxTriples={max_triples}&sameAs={same_as}"
    )

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print("[ERROR] Failed to fetch data:", e)
        return ""


def nquads_to_ntriples(nquads_text):
    triples = []

    for line in nquads_text.splitlines():
        line = line.strip()

        if not line or not line.endswith("."):
            continue

        # Split by tab (LODsyndesis format)
        parts = line.split("\t")

        # Expecting: subject, predicate, object, graph
        if len(parts) < 3:
            continue

        subject = parts[0]
        predicate = parts[1]
        obj = parts[2]

        triple = f"{subject} {predicate} {obj} ."
        triples.append(triple)

    return triples


def save_to_nt(triples, output_file):
    """
    Saves triples to .nt file.
    """
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            for triple in triples:
                f.write(triple + "\n")
        print(f"[INFO] Saved {len(triples)} triples to {output_file}")
    except Exception as e:
        print("[ERROR] Failed to save file:", e)


def dbpedia_triples(entity, max_triples=500):
    

    sparql = SPARQLWrapper("http://dbpedia.org/sparql")

    query = f"""
    SELECT ?s ?p ?o WHERE {{
        {{ <{entity}> ?p ?o . BIND(<{entity}> AS ?s) }}
        UNION
        {{ ?s ?p <{entity}> . BIND(<{entity}> AS ?o) }}
        FILTER(!regex(?p, "wiki"))
    }}
    LIMIT {max_triples}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    triples = []

    try:
        results = sparql.query().convert()

        for res in results["results"]["bindings"]:
            s = res["s"]["value"]
            p = res["p"]["value"]
            o = res["o"]["value"]

            # Format object correctly
            if res["o"]["type"] == "uri":
                o_formatted = f"<{o}>"
            else:
                o_formatted = f"\"{o}\""

            triple = f"<{s}> <{p}> {o_formatted} ."
            triples.append(triple)

    except Exception as e:
        print("[ERROR] DBpedia query failed:", e)

    return triples

if __name__ == "__main__":
    entity = "http://dbpedia.org/resource/Aristotle"
    max_triples = 1000
    same_as = "No"

    #"LODsyndesis" or "DBpedia"
    source = "LODsyndesis"   # change to "DBpedia" if needed

    print(f"[INFO] Using source: {source}")

    # ---------------- SELECT SOURCE ----------------
    if source == "LODsyndesis":
        print("[INFO] Fetching from LODsyndesis...")

        nquads_data =lodsyndesis_facts(entity, max_triples, same_as)

        if not nquads_data:
            print("[ERROR] No data retrieved.")
            exit()

        triples = nquads_to_ntriples(nquads_data)

    elif source == "DBpedia":
        print("[INFO] Fetching from DBpedia SPARQL...")

        triples = dbpedia_triples(entity, max_triples)

        if not triples:
            print("[ERROR] No data retrieved.")
            exit()

    else:
        print("[ERROR] Invalid source. Choose 'LODsyndesis' or 'DBpedia'")
        exit()

    # ---------------- SAVE FILE ----------------
    output_file = f"output//{source.lower()}_triples.nt"

    with open(output_file, "w", encoding="utf-8") as f:
        for triple in triples:
            f.write(triple + "\n")

    print(f"[INFO] Saved {len(triples)} triples to {output_file}")
    print("[DONE]")
import yaml
import requests
import spacy
import json
import urllib.parse
import time

# -------------------------------
# Load configuration
# -------------------------------
with open("conf.yaml", "r") as f:
    config = yaml.safe_load(f)

selected_tool = config["tool"].lower()
output_file = config["output"]["file"]
text = config["text"]

# -------------------------------
# DBpedia Spotlight
# -------------------------------
def extract_spotlight(text):
    if not config["dbpedia_spotlight"]["enabled"]:
        return []
    try:
        confidence = str(config["dbpedia_spotlight"]["confidence"])
        headers = config["dbpedia_spotlight"]["headers"]
        url_text = urllib.parse.quote(text)
        url = f"{config['dbpedia_spotlight']['url']}?text={url_text}&confidence={confidence}"
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        output = response.json()
        results = set()
        entities = []
        for e in output.get("Resources", []):
            score = float(e.get('@similarityScore', 0))
            key = e['@surfaceForm']
            if key not in results:
                results.add(key)
                entities.append({
                    "entity": e['@surfaceForm'],
                    "uri": e['@URI']
                })
        return entities
    except Exception as ex:
        print("Spotlight error:", ex)
        return []

# -------------------------------
# Stanford CoreNLP
# -------------------------------

# WAT extraction
def extract_wat(text):
    if not config["wat"]["enabled"]:
        return []
    try:
        headers = {"Accept": "application/json; charset=utf-8"}
        url = config["wat"]["url"]
        params = {
            "lang": config["wat"]["lang"],
            "gcube-token": config["wat"]["gcube_token"],
            "text": text
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        output = response.json()
        rho_threshold = config["wat"]["rho_threshold"]
        results = []
        for ann in output.get("annotations", []):
            if ann['rho'] > rho_threshold:
                results.append({
                    "entity": ann['spot'],
                    "uri": f"http://dbpedia.org/resource/{ann['title']}"
                })
        return results
    except Exception as ex:
        print("WAT error:", ex)
        return []


# -------------------------------
# Main function
# -------------------------------
def extract_entities(text):
    if selected_tool == "spotlight":
        return extract_spotlight(text)
    elif selected_tool == "wat":
        return extract_wat(text)
    else:
        raise ValueError(f"Unknown tool selected: {selected_tool}")

# -------------------------------
# Run extraction and save JSON
# -------------------------------
if __name__ == "__main__":
    start_time = time.time()  # start timer
    entities = extract_entities(text)
    end_time = time.time()    # end timer
    elapsed = end_time - start_time

    # Save structured JSON to file
    with open(output_file, "w") as f:
        json.dump(entities, f, indent=2)

    print(f"Entities extracted using {selected_tool} in {elapsed:.2f} seconds")
    print(f"Saved to {output_file}")

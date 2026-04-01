# 🧠 Overview

This project performs **entity linking** on input text using:

- DBpedia Spotlight  
- WAT (Wikipedia Annotation Tool)  

It identifies entities in text and links them to knowledge base URIs (e.g., DBpedia or Wikipedia).

The system is configurable via a YAML file and supports switching between tools.

---

# ⚙️ Configuration (`conf.yaml`)

The system is controlled through a YAML configuration file.

## 🔹 Example

```yaml
tool: "spotlight" # spotlight or wat

text: "Mahi-mahi (or Coryphaena hippurus) live in the ocean"

dbpedia_spotlight:
  url: "https://api.dbpedia-spotlight.org/en/annotate"
  confidence: 0.6
  headers:
    Accept: "application/json"
  enabled: true

wat:
  url: "https://wat.d4science.org/wat/tag/tag"
  gcube_token: "YOUR_TOKEN_HERE"
  rho_threshold: 0.1
  lang: "en"
  enabled: true

output:
  file: "entities_output.json"

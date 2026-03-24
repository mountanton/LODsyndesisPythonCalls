import requests
import json


def download_json(uri, file_suffix ):
    output_file="output/sameAs_"+file_suffix+".json"
    url = "https://demos.isl.ics.forth.gr/lodsyndesis/rest-api/objectCoreference"
    
    headers = {
        "Accept": "application/json"
    }
    
    params = {
        "uri": uri
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"JSON response saved to {output_file}")
    else:
        print(f"Request failed with status code: {response.status_code}")

download_json("http://dbpedia.org/resource/Aristotle","Aristotle")

download_json("http://dbpedia.org/resource/Bali","Bali")
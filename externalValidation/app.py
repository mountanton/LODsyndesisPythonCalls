# ---------------- SAFE RUNTIME GUARDS ----------------
import traceback


_global_model = None

def get_model():
    """Loads the model once and reuses it for all subsequent calls."""
    global _global_model
    if _global_model is None:
        _global_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    return _global_model

    
def safe_requests_get(url, headers=None, timeout=10):
    try:
        import requests
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return []
    except Exception:
        print("[WARN] Request failed:", url)
        return []

def safe_sparql_query(sparql):
    try:
        return sparql.query().convert()
    except Exception:
        print("[WARN] SPARQL query failed")
        return {"results": {"bindings": []}, "boolean": False}
# -----------------------------------------------------
from SPARQLWrapper import SPARQLWrapper, JSON
from sentence_transformers import SentenceTransformer
import numpy as np
import re
import time
import yaml
import json
import requests
from urllib.request import urlopen
from urllib.error import HTTPError

def checkURIExistence(entity,isProperty):
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    # Query for the description of "Capsaicin", filtered by language
    sparql.setQuery("ASK WHERE { {"+entity+" ?p ?o} UNION {?o ?p "+entity+"}}")
    if(isProperty):
        sparql.setQuery("ASK WHERE { {?s "+entity+"  ?o}}")
    sparql.setReturnFormat(JSON)
    result = safe_sparql_query(sparql)
    #print(result)
    results=""
    dictionary=[]
    i=0
    # The return data contains "bindings" (a list of dictionaries)
    if(result["boolean"]==True):
        return(entity+" exists")
    else:
        return(entity+" notAvailable")

def most_similar(sentences,fullURIs, similarity_matrix,matrix,k):
    if matrix=='Cosine Similarity':
        similar_ix=np.argsort(similarity_matrix[0])[::-1]
    i=0
    retValue=""
    max=0
    #print("The most similar properties of "+fullURIs[0])
    for ix in similar_ix:
        if ix==0:
            continue
        i=i+1
        if i == k+1:
            break
        retValue=retValue+str(similarity_matrix[0][ix])+ '\t'+fullURIs[ix]+"\tMost Similar Triples\n"
        if(i==1):
            #retValue=fullURIs[ix]
            max=similarity_matrix[0][ix]
        #if(i==2 and "dbpedia" in fullURIs[ix] and similarity_matrix[0][ix]==max):
            #retValue=fullURIs[ix]
    return retValue
        #print (documentsLabels[ix])

wkdProps={}

def readWkdProps():
    with open("wkdProps.txt", "r", encoding="utf-8") as f: #pipeline/componentUtilities/externalValidation/
        for line in f: # files are iterable
            x=str(line).replace("b'","").replace("'","").replace(r"\n","")
            prop=str(x).split(",")[0]
            label=str(x).split(",")[1].replace("\n","")
            wkdProps[prop]=label
    #print(wkdProps)

def getBestPredicate(entity,property,fullProperty):
    url = "https://demos.isl.ics.forth.gr/lodsyndesis/rest-api/allFacts?uri="+entity
    sentences = [re.sub( '(?<!^)(?=[A-Z])', ' ',property).lower()]
    response =requests.get(url,
                    headers={'Accept': 'application/json'})
    response_json = response.json()

    fullURIs=[fullProperty]
    #print(response_json)
    for hit in response_json:
      if(hit["predicate"]!='<http://www.w3.org/2002/07/owl#sameAs>' and hit["predicate"]!='<http://www.w3.org/2002/07/owl#equivalentClass>'):
          if(hit["predicate"]=='<http://www.w3.org/2002/07/owl#equivalentProperty>'):
              pred1 = hit["subject"].replace("<","").replace(">","")
              pred2 = hit["object"].replace("<","").replace(">","")
              pred1Split=pred1.split("/")
              pred2Split=pred1.split("/")
              if(not pred1 in fullURIs):
                sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred1Split[len(pred1Split)-1]).lower())
                fullURIs.append(pred1)
              if(not pred2 in fullURIs):
                sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred2Split[len(pred2Split)-1]).lower())
                fullURIs.append(pred2)
          else:
            pred1 = hit["predicate"].replace("<","").replace(">","")
            pred1Split=pred1.split("/")
            if(not pred1 in fullURIs):
              sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred1Split[len(pred1Split)-1]).lower())
              fullURIs.append(pred1)

    model = get_model()
    embeddings = model.encode(sentences)
    pairwise_similarities=np.dot(embeddings,embeddings.T)
    retValue=most_similar(sentences,fullURIs,pairwise_similarities,'Cosine Similarity',5)
    return retValue

currentEntity=""
sentences=[""]
fullURIs=[""]
def getBestPredicateObject(entity,property,fullProperty,object,fullObject,topK,maxTriples):
    global currentEntity
    global sentences
    global fullURIs
    sentences[0] = re.sub( '(?<!^)(?=[A-Z])', ' ',property).lower()+ " "+re.sub( '(?<!^)(?=[A-Z])', ' ',object).lower()
    fullURIs[0]=fullProperty+" "+fullObject
    if(currentEntity!=entity or len(sentences)==1):
      url = "https://demos.isl.ics.forth.gr/lodsyndesis/rest-api/allFacts?uri="+entity+"&maxTriples="+maxTriples+"&sameAs=No"
      try:
        response =requests.get(url,
                      headers={'Accept': 'application/json'})
        response.raise_for_status()
      except requests.exceptions.HTTPError:
         response_json = []
      else:
         response_json = response.json()

     # response_json = response.json()
      currentEntity=entity
      #print(response_json)
      for hit in response_json:
        if(hit["predicate"]!='<http://www.w3.org/2002/07/owl#sameAs>' and hit["predicate"]!='<http://www.w3.org/2002/07/owl#equivalentClass>'):
            if(hit["predicate"]!='<http://www.w3.org/2002/07/owl#equivalentProperty>'):
              pred1 = hit["predicate"].replace("<","").replace(">","")
              obj1=hit["object"].replace("<","").replace(">","").replace("_"," ")
              pred1Split=pred1.split("/")
              if(hit["object"].replace("<","").replace(">","")==entity):
                obj1=hit["subject"].replace("<","").replace(">","").replace("_"," ")
              obj1Split=obj1.split("/")
              pred1SplitCell=pred1Split[len(pred1Split)-1].split('#') # to add
              if("http://www.wikidata.org/entity/" in pred1):
                wkdPred=pred1.replace("http://www.wikidata.org/entity/","").replace("c","").replace("*","")
                wkdPredicate=wkdPred
                if(wkdPred in wkdProps):
                  wkdPredicate=str(wkdProps[wkdPred])
                  #print(wkdPredicate)
                sentences.append(wkdPredicate+" "+re.sub( '(?<!^)(?=[A-Z])', ' ',obj1Split[len(obj1Split)-1]).lower())
                fullURIs.append(pred1+ "\t"+hit["object"].replace("<","").replace(">","")+ "\t"+hit["provenance"])
              else:
                sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred1SplitCell[len(pred1SplitCell)-1]).lower()+" "+re.sub( '(?<!^)(?=[A-Z])', ' ',obj1Split[len(obj1Split)-1]).lower())
                fullURIs.append(pred1+ "\t"+hit["object"].replace("<","").replace(">","")+ "\t"+hit["provenance"])
      response =getAllDBpediaTriples("<"+entity+">",maxTriples)
      currentEntity=entity
      #print(response_json)
      for hit in response["results"]["bindings"]:
        if(hit["predicate"]["value"]!='http://www.w3.org/2002/07/owl#sameAs' and hit["predicate"]["value"]!='http://www.w3.org/2002/07/owl#equivalentClass'):
            if(hit["predicate"]["value"]!='<http://www.w3.org/2002/07/owl#equivalentProperty>'):
              pred1 = hit["predicate"]["value"].replace("<","").replace(">","")
              if(hit["object"]["type"]=="literal" and "xml:lang" in hit["object"].keys() and hit["object"]["xml:lang"]!="en"):
               continue
              obj1=hit["object"]["value"].replace("<","").replace(">","").replace("_"," ")
              pred1Split=pred1.split("/")
              obj1Split=obj1.split("/")
              pred1SplitCell=pred1Split[len(pred1Split)-1].split('#') # to add
              sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred1SplitCell[len(pred1SplitCell)-1]).lower()+" "+re.sub( '(?<!^)(?=[A-Z])', ' ',obj1Split[len(obj1Split)-1]).lower())
              fullURIs.append(pred1+ "\t"+hit["object"]["value"].replace("<","").replace(">","")+ "\t<http://dbpedia.org/current>")

    else:
       print(currentEntity)


    model = get_model()
    #print(sentences)
    embeddings = model.encode(sentences)
    pairwise_similarities=np.dot(embeddings,embeddings.T)
    retValue=most_similar(sentences,fullURIs,pairwise_similarities,'Cosine Similarity',topK)
    return retValue

# Print the response


def checkDBpedia(entity,predicate,obj):
  if("\\" in obj):
     obj=obj.replace("\\","")
  # Specify the DBPedia endpoint
  sparql = SPARQLWrapper("http://dbpedia.org/sparql")
  # Query for the description of "Capsaicin", filtered by language
  sparql.setQuery("ASK WHERE { {"+entity+" "+predicate+" "+obj.replace("'","")+"}}")
  sparql.setReturnFormat(JSON)
  try:
    result = safe_sparql_query(sparql)
  except HTTPError as e:
    return []
  results=""
  dictionary=[]
  i=0
  # The return data contains "bindings" (a list of dictionaries)
  if(result["boolean"]==True):
      # We want the "value" attribute of the "comment" field
      dictionary.append({
      "predicate": predicate,
      "provenance": '<http://dbpedia.org/current>',
      "subject": entity,
      "object": obj,
      "threshold": "1.0"
     })
  if(dictionary==[]):
    sparql.setQuery("SELECT  ?predicate WHERE { {"+entity+" ?predicate "+ obj+"} UNION {"+obj+ "?predicate " +entity+" } . filter(!regex(?predicate,'wiki'))}")
    if('"' in obj ):
       sparql.setQuery("SELECT  ?predicate WHERE { "+entity+" ?predicate "+ obj.replace("'","")+" . filter(!regex(?predicate,'wiki'))}")
    sparql.setReturnFormat(JSON)
    result = safe_sparql_query(sparql)
   # print(result)
    for hit in result["results"]["bindings"]:
      # We want the "value" attribute of the "comment" field
       dictionary.append({
      "predicate": '<'+hit["predicate"]["value"]+'>',
      "provenance": '<http://dbpedia.org/current>',
      "subject": entity,
      "object": obj,
      "threshold": "0.5"
     })
  if(dictionary==[]):
    sparql.setQuery("SELECT  ?obj WHERE { {"+entity+" "+predicate+" ?obj} UNION {?obj "+predicate+ " " +entity+" }}")
    sparql.setReturnFormat(JSON)
    result = safe_sparql_query(sparql)
  #  print(result)
    for hit in result["results"]["bindings"]:
      objNew=hit["obj"]["value"]
      if "http" in objNew:
          objNew="<"+objNew+">"
      dictionary.append({
      "predicate": predicate,
      "provenance": '<http://dbpedia.org/current>',
      "subject": entity,
      "object": objNew,
      "threshold": "0.5"
     })
  #if(dictionary==[]):
    sparql.setQuery("SELECT  ?obj WHERE { {"+entity+" "+predicate.replace("http://dbpedia.org/ontology/","http://dbpedia.org/property/")+" ?obj} UNION {?obj "+predicate.replace("http://dbpedia.org/ontology/","http://dbpedia.org/property/")+ " " +entity+" }}")
    sparql.setReturnFormat(JSON)
    result = safe_sparql_query(sparql)
   # print(result)
    for hit in result["results"]["bindings"]:
      objNew=hit["obj"]["value"]
      if "http" in objNew:
        objNew="<"+objNew+">"
      # We want the "value" attribute of the "comment" field
      dictionary.append({
      "predicate": predicate.replace("http://dbpedia.org/ontology/","http://dbpedia.org/property/"),
      "provenance": '<http://dbpedia.org/current>',
      "subject": entity,
      "object": objNew,
      "threshold": "0.5"
     })
  return dictionary

def getAllDBpediaTriples(entity,maxTriples):
  sparql = SPARQLWrapper("http://dbpedia.org/sparql")
  # Query for the description of "Capsaicin", filtered by language
  sparql.setQuery("SELECT * WHERE { {"+entity+" ?predicate ?object } UNION {?object ?predicate " +entity+" }. filter(!regex(?predicate,'wiki'))} limit "+maxTriples)
  sparql.setReturnFormat(JSON)
  result = safe_sparql_query(sparql)
  return result

def getBestPredicateObjectDBpedia(entity,property,fullProperty,object,fullObject,topK,maxTriples):
    global currentEntity
    global sentences
    global fullURIs
    sentences[0] = re.sub( '(?<!^)(?=[A-Z])', ' ',property).lower()+ " "+re.sub( '(?<!^)(?=[A-Z])', ' ',object).lower()
    fullURIs[0]=fullProperty+" "+fullObject
    if(currentEntity!=entity or len(sentences)==1):
      response =getAllDBpediaTriples(entity,maxTriples)
      currentEntity=entity
      #print(response_json)
      for hit in response["results"]["bindings"]:
        if(hit["predicate"]["value"]!='http://www.w3.org/2002/07/owl#sameAs' and hit["predicate"]["value"]!='http://www.w3.org/2002/07/owl#equivalentClass'):
            if(hit["predicate"]["value"]!='<http://www.w3.org/2002/07/owl#equivalentProperty>'):
              pred1 = hit["predicate"]["value"].replace("<","").replace(">","")
              if(hit["object"]["type"]=="literal" and "xml:lang" in hit["object"].keys() and hit["object"]["xml:lang"]!="en"):
               continue
              obj1=hit["object"]["value"].replace("<","").replace(">","").replace("_"," ")
              pred1Split=pred1.split("/")
              obj1Split=obj1.split("/")
              pred1SplitCell=pred1Split[len(pred1Split)-1].split('#') # to add
              sentences.append(re.sub( '(?<!^)(?=[A-Z])', ' ',pred1SplitCell[len(pred1SplitCell)-1]).lower()+" "+re.sub( '(?<!^)(?=[A-Z])', ' ',obj1Split[len(obj1Split)-1]).lower())
              fullURIs.append(pred1+ "\t"+hit["object"]["value"].replace("<","").replace(">","")+ "\t<http://dbpedia.org/current>")
    else:
       print(currentEntity)

    model = get_model()
    #print(sentences)
    embeddings = model.encode(sentences)
    pairwise_similarities=np.dot(embeddings,embeddings.T)
    retValue=most_similar(sentences,fullURIs,pairwise_similarities,'Cosine Similarity',topK)
    return retValue

def calculateSimilarity(pred1, obj1,pred2, obj2):
    model = get_model()
    newPred1=pred1.replace(">","").replace('_',' ').split("/")
    newObj1=obj1.replace(">","").replace('"','').replace('_','').split("/")
    sentence1= re.sub( '(?<!^)(?=[A-Z])', ' ',newPred1[len(newPred1)-1]).lower()+ " "+re.sub( '(?<!^)(?=[A-Z])', ' ',newObj1[len(newObj1)-1]).lower()
    #print(pred2)
    if("http://www.wikidata.org/entity/" in pred2):
        wkdPred=pred2.replace("http://www.wikidata.org/entity/","").replace("c","").replace("*","").replace(">","").replace("<","")
        wkdPredicate=wkdPred
        if(wkdPred in wkdProps):
          wkdPredicate=str(wkdProps[wkdPred])
          #print(wkdPredicate)
        newObj2=obj2.replace(">","").replace('_',' ').replace('"','').split("/")
        sentence2= wkdPredicate+" "+re.sub( '(?<!^)(?=[A-Z])', ' ',newObj2[len(newObj2)-1]).lower()
    else:
      if("#" in pred2):
        newPred2=pred2.replace(">","").replace('_',' ').split("#")
      else:
        newPred2=pred2.replace(">","").replace('_',' ').split("/")   
      newObj2=obj2.replace(">","").replace('_',' ').replace('"','').split("/")
      sentence2= re.sub( '(?<!^)(?=[A-Z])', ' ',newPred2[len(newPred2)-1]).lower()+ " "+re.sub( '(?<!^)(?=[A-Z])', ' ',newObj2[len(newObj2)-1]).lower()
    #print(sentence1, sentence2)
    sentencesBoth=[sentence1,sentence2]
    embeddings = model.encode(sentencesBoth)
    pairwise_similarities=np.dot(embeddings,embeddings.T)
    return str(pairwise_similarities[0][1])

def sortSimilarities(entForPrint,sentences,topK):
    sentencesSplit=sentences.split("\n")
    key_value = {}
    cnt=0
    finalSort={}
    for entry in sentencesSplit:
      entrySplit=entry.split("\t")
      if len(entrySplit)==6:
        threshold=entrySplit[0]
        triple=entrySplit[1].replace("<","").replace(">","")+"\t"+entrySplit[2].replace("<","").replace(">","")+"\t"+entrySplit[3].replace("<","").replace(">","")+"\t"+entrySplit[4].replace("<","").replace(">","")
        typeOfEv=entrySplit[5]
        key_value[threshold]=triple+"\t"+typeOfEv
    for i in sorted(key_value.keys(),reverse=True):
        newTriple=key_value[i].split("\t")
        finalSort["top"+str(cnt+1)]={"threshold":i,"subject":newTriple[0],"predicate":newTriple[1],"object":newTriple[2],"provenance":newTriple[3],"type":newTriple[4]}
        #print(finalSort)
        cnt=cnt+1
        if(cnt==topK):
          break
    return finalSort

def returnValueToDictionary(entForPrint,retVal):
   similarTriples=retVal.split("\n")
   finalSort={}
   cnt=1
   for striple in similarTriples:
    if(striple==""):
     break
    newTriple=striple.replace("<","").replace(">","").split("\t")
    finalSort["top"+str(cnt)]={"threshold":newTriple[0],"subject":entForPrint,"predicate":newTriple[1],"object":newTriple[2],"provenance":newTriple[3],"type":newTriple[4]}
    cnt=cnt+1
   return finalSort

def initAfterReq():
    global currentEntity
    global sentences
    global fullURIs
    currentEntity=""
    sentences=[""]
    fullURIs=[""]


def findRelevantFacts(inputTriples,KG,topKValue="3",maxTriples="800"):
    if(wkdProps=={}):
        readWkdProps()
    topK=int(topKValue)
    responseDictionary={}
    tripleID=1
    correctCount=0
    samePredicateOrObjectCount=0
    bestMatchCount=0
    retValue=""
    currentEntity=""
    response_json=[]
    for fct in inputTriples:
        try:
        #print(fct)
            start = time.time()
            factSplit=fct.split("> ")
            dbpediaTriples=[]
            if(len(factSplit)>=3):
                entity=factSplit[0].split("<")[1]
                predicateSplit=factSplit[1].replace("<","").split("#")
                predicate=predicateSplit[len(predicateSplit)-1]
                obj=factSplit[2].replace("<","").replace('"',"").replace(" .","").split("^^")
                if(obj[0].isnumeric()):
                    obj[0]='"'+obj[0]+'"'
                facts=predicate+ " "+obj[0]
                if(KG!="LODsyndesis"):
                    if "http" in factSplit[2].split("^^")[0]:
                        dbpediaTriples=checkDBpedia("<"+entity+">",factSplit[1]+">",factSplit[2].replace(" .","").split("^^")[0]+">")
                    else:
                        dbpediaTriples=checkDBpedia("<"+entity+">",factSplit[1]+">",factSplit[2].replace(" .","").split("^^")[0])
                if(KG=="Both" or KG=="LODsyndesis" ):
                    url = "https://demos.isl.ics.forth.gr/lodsyndesis/rest-api/factChecking?uri="+entity+"&fact="+facts.replace("#","/")+"&threshold=0.5"
                # A GET request to the API
                    response =requests.get(url,
                                headers={'Accept': 'application/json'})
            else:
                continue
            # Print the response
            if KG!="DBpedia":
                response_json = response.json()
            else:
                response_json = []
            #if(response_json==[] and "http://dbpedia.org/ontology/" in facts and KG!="DBpedia"):
            #    url = "http://localhost:8081/LODsyndesis/rest-api/factChecking?uri="+entity+"&fact="+facts.replace("http://dbpedia.org/ontology/","http://dbpedia.org/property/")+"&threshold=0.5"
            #    response =requests.get(url,
            #                    headers={'Accept': 'application/json'})
            #    response_json = response.json()

            correct=""
            samePredicateOrObject=""
            bestMatch=""
            if(entity!=currentEntity):
                initAfterReq()

            response_json.extend(dbpediaTriples)
            if(response_json==[]):
                newPred=predicate.split("/")
                newObj=obj[0].split("/")
                if(KG!="DBpedia"):
                    bestPredicate=  getBestPredicateObject(entity,newPred[len(newPred)-1],predicate,newObj[len(newObj)-1].replace("_"," "),obj[0],topK,maxTriples) # getBestPredicateObjectDBpedia("<"+entity+">",newPred[len(newPred)-1],predicate,newObj[len(newObj)-1].replace("_"," "),obj[0],topK) # #getBestPredicate(entity,newPred[len(newPred)-1],predicate)
                    retValue=str(bestPredicate)
                else:
                    bestPredicate= getBestPredicateObjectDBpedia("<"+entity+">",newPred[len(newPred)-1],predicate,newObj[len(newObj)-1].replace("_"," "),obj[0],topK,maxTriples)  # getBestPredicateObjectDBpedia("<"+entity+">",newPred[len(newPred)-1],predicate,newObj[len(newObj)-1].replace("_"," "),obj[0],topK) # #getBestPredicate(entity,newPred[len(newPred)-1],predicate)
                    retValue=str(bestPredicate)
            else:
                for entry in response_json:
                    if entry["threshold"]=="1.0":
                        correct=entry["threshold"]+"\t"+entry["subject"]+ "\t"+entry["predicate"]+"\t"+entry["object"]+"\t"+ entry["provenance"]+"\tSame Triple\n"
                    else:
                        if("<"+predicate.replace("property","ontology")+">"==entry["predicate"].replace("property","ontology") and obj[0].replace('"',"").replace("<","").replace(">","").lower()==entry["object"].replace('"',"").replace("<","").replace(">","").lower()):
                            correct="1.0\t"+entry["subject"]+ "\t"+entry["predicate"]+"\t"+entry["object"]+"\t"+ entry["provenance"]+"\tSame Triple\n"
                        elif("<"+predicate.replace("property","ontology")+">"==entry["predicate"].replace("property","ontology") or entry["predicate"]==factSplit[1]+">"):
                            similarity=calculateSimilarity(predicate,obj[0],entry["predicate"],entry["object"])
                            samePredicateOrObject+=similarity+"\t"+entry["subject"]+ "\t"+entry["predicate"]+"\t"+entry["object"]+"\t"+ entry["provenance"]+"\tSame Predicate - Different Object\n"
                        elif(obj[0].replace('"',"").replace("<","").replace(">","").lower()==entry["object"].replace('"',"").replace("<","").replace(">","").lower()):
                            similarity=calculateSimilarity(predicate,obj[0],entry["predicate"],entry["object"])
                            samePredicateOrObject+=similarity+"\t"+entry["subject"]+ "\t"+entry["predicate"]+"\t"+entry["object"]+"\t"+ entry["provenance"]+"\tSame Object - Different Predicate\n"
                        else:
                            similarity=calculateSimilarity(predicate,obj[0],entry["predicate"],entry["object"])
                            bestMatch+=similarity+"\t"+entry["subject"]+ "\t"+entry["predicate"]+"\t"+entry["object"]+"\t"+ entry["provenance"]+"\tMost Similar Triples\n"
            print("#"+str(tripleID)+" "+"Triple: "+fct)

            #print("Fact Checking Triple(s) and Provenance")
            if(correct!=""):
                correctSort={}
                correctTriple=correct.replace(">","").replace("<","").split("\t")
                correctSort["top1"]={"threshold":"1.0","subject":correctTriple[1],"predicate":correctTriple[2],"object":correctTriple[3],"provenance":correctTriple[4],"type":"Same or Equivalent Triple"}
                responseDictionary[tripleID-1]={"fact":{"subject":entity.replace("<","").replace(">",""),
                                                                "predicate":factSplit[1].replace("<","").replace(">",""),"object":factSplit[2].replace("<","").replace(">","")},
                                                                "KG_Facts":correctSort}
                correctCount=correctCount+1
            elif(samePredicateOrObject!=""):
                responseDictionary[tripleID-1]={"fact":{"subject":entity.replace("<","").replace(">",""),
                                                                "predicate":factSplit[1].replace("<","").replace(">",""),"object":factSplit[2].replace("<","").replace(">","")},"KG_Facts":sortSimilarities(entity,samePredicateOrObject,topK)}
                samePredicateOrObjectCount=samePredicateOrObjectCount+1
            elif(bestMatch!=""):
                responseDictionary[tripleID-1]={"fact":{"subject":entity.replace("<","").replace(">",""),
                                                                "predicate":factSplit[1].replace("<","").replace(">",""),"object":factSplit[2].replace("<","").replace(">","")},"KG_Facts":sortSimilarities(entity,bestMatch,topK)}
                bestMatchCount=bestMatchCount+1
            else:
                if(retValue==""):
                    responseDictionary[tripleID-1]={"fact":{"subject":entity.replace("<","").replace(">",""),
                                                                "predicate":factSplit[1].replace("<","").replace(">",""),"object":factSplit[2].replace("<","").replace(">","")},"KG_Facts":{}}
                else:
                    responseDictionary[tripleID-1]={"fact":{"subject":entity.replace("<","").replace(">",""),
                                                                "predicate":factSplit[1].replace("<","").replace(">",""),"object":factSplit[2].replace("<","").replace(">","")},"KG_Facts":returnValueToDictionary(entity,retValue)}
                bestMatchCount=bestMatchCount+1
            end = time.time()
            tripleID=tripleID+1
        except Exception as e:
            print("[ERROR] Triple processing failed:", fct)
            traceback.print_exc()
            tripleID = tripleID + 1
            continue
    initAfterReq()
    return  json.dumps(responseDictionary)  #request.data #.get_json()

def validate_relevant_facts(results_dict, threshold=0.65):
    validation_summary = {}  # Store results in JSON-like dict

    for idx, triple_info in results_dict.items():
        fact = triple_info.get("fact", {})
        KG_Facts = triple_info.get("KG_Facts", {})

        validated_facts = {}

        for key, kg_fact in KG_Facts.items():
            if "threshold" in kg_fact:
                sim_score = float(kg_fact["threshold"])
                status = "VALIDATED" if sim_score >= threshold else "NOT VALIDATED"

                validated_facts[key] = {
                    "subject": kg_fact.get("subject", ""),
                    "predicate": kg_fact.get("predicate", ""),
                    "object": kg_fact.get("object", ""),
                    "provenance": kg_fact.get("provenance", ""),
                    "type": kg_fact.get("type", ""),
                    "similarity": sim_score,
                    "status": status
                }

        if validated_facts:
            validation_summary[idx] = {
                "fact": fact,
                "topK_KG_facts": validated_facts
            }
        else:
            validation_summary[idx] = {
                "fact": fact,
                "topK_KG_facts": {},
                "type": "Entity Not Found",
                "status": "NOT VALIDATED"
            }

    return validation_summary




def load_config(path="conf.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    cfg = load_config()

    facts = cfg["facts"]
    KG = cfg["KG"]
    topK = cfg["topK"]
    threshold=cfg["threshold"]
    maxTriples=str(cfg["maxTriples"])
    #Find the top-k most relevant triples
    results = findRelevantFacts(facts,KG, topK,maxTriples)
    printFactChecking=False
    results_dict = json.loads(results)
    if(printFactChecking==True):
      print("Relevant Facts Results:")
      print(json.dumps(results_dict, indent=4, ensure_ascii=False))
    
    #Validating based on the threshold and the top-1 relevant fact
    validation_summary=validate_relevant_facts(results_dict,threshold)
    # Write to file
    output_file = f"output/validation_summary_{KG}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(validation_summary, f, indent=4, ensure_ascii=False)

    print(f"Validation summary written to {output_file}")
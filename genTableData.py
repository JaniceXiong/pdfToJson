import json
import re

ref_pattern = re.compile("<(ref|table|figure)(.*?)>")

def clean(text):
    clean_text = []
    for sent in text:
        clean_text.append(re.sub(ref_pattern,"",sent))

    return clean_text

if __name__ == '__main__':
    json_path = '5057.json'
    with open(json_path,'r',encoding='utf-8') as json_f:
        paper = json.load(json_f)

    texts = paper["Papertext"]
    tables = paper["Tables"]
    
    for table in tables:
        tid = table["id"]
        tdesc = table["Description"]
        idxes = []
        
        if(tid != ""):
            query = "<table id=#" + tid + ">"
            
            for i, text in enumerate(texts):
                for j, sent in enumerate(text):
                    if(sent.find(query) != -1):
                        idxes.append((i,j))
            
            tdocs = []
            for tidx, sidx in idxes:
                if(tidx != 0):
                    preSection = clean(texts[tidx-1])
                else:
                    preSection = []

                section = clean(texts[tidx])

                if(tidx != len(texts)-1):
                    postSection = clean(texts[tidx+1])
                else:
                    postSection = []
                
                tdoc = {
                    "Sections":{
                        "preSection" : preSection,
                        "Section" : section,
                        "postSection" : postSection
                    },
                    "SentenceID" : sidx
                }

                tdocs.append(tdoc)
        
        meta_data = {
            "id" : tid,
            "Description" : tdesc,
            "Document" : tdocs
        }

        print(meta_data['Document'][0])


        
                

                

                        


        

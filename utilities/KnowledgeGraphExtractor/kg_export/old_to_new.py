import sys
import json


def read_file(file_path):
    with open(file_path) as json_file:
        data = json.load(json_file)
    return data


def write_file(file_path, rest):
    file_name = file_path.split(".")[0]
    with open('%s-newExtract.json' % (file_name), 'w') as f:
        json.dump(rest, f)


valid_keys = ["faqs", "unmappedpath", "synonyms"]
data = read_file(sys.argv[1])
result = {}
for key,val in data.items():
    if key not in valid_keys:
        continue
    if key == "faqs":
        result[key]=[]
        if not val:
            continue

        for faq_entry in val:
            obj = {}
            for faq_key,faq_val in faq_entry.items():
                if not faq_val:
                    obj[faq_key] = faq_val
                    continue
                if faq_key == "tags":
                    new_tags = []
                    for raw_tag in faq_val:
                        new_tags.append(raw_tag.get('name').split(":")[0])
                    obj[faq_key] = new_tags

                elif faq_key == "terms":
                    new_terms = []
                    status = False
                    for raw_term in faq_val:
                        import copy
                        new_term = copy.deepcopy(raw_term)
                        if ":" in new_term:
                            new_term = new_term.split(":")[0]
                        new_terms.append(new_term)
                    obj[faq_key] = new_terms
                else:
                    obj[faq_key] = faq_val



            result[key].append(obj)
    else:
        result[key] = val
print(result["faqs"][0:10])
write_file("/home/lakshmikaivalya/Desktop/ont_analyzer/result.json",result)



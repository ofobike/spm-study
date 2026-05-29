import json

with open('assets/questions/case_studies.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Update existing cases with new fields
for case in data['case_studies']:
    case['difficulty'] = 'medium'
    case['total_score'] = 25
    case['chapters'] = [case['chapter']]
    for q in case['questions']:
        q['question_type'] = 'choice'
        q['score'] = 5

with open('assets/questions/case_studies.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Updated {len(data['case_studies'])} existing cases with new fields")

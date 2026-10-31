import json
data = json.load(open('outbound_leads.json', 'r', encoding='utf-8'))
print(f"Total leads: {len(data)}\n")
for b in data:
    print(f"  [{b['business_type']:20}] {b['name'][:40]:40} phone={b['phone']} email={b['email']}")

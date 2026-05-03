import re

import networkx as nx

MEDICAL_GRAPH = {
    "Cough": ["Common Cold", "Influenza", "Bronchitis", "Pneumonia", "Asthma"],
    "Throat Irritation": ["Allergic Rhinitis", "Viral Pharyngitis", "Acid Reflux", "Postnasal Drip"],
    "Sore Throat": ["Viral Pharyngitis", "Strep Throat", "Tonsillitis", "COVID-19", "Mononucleosis"],
    "Fever": ["Influenza", "COVID-19", "Pneumonia", "Urinary Tract Infection", "Dengue Fever"],
    "Chest Pain": ["Angina", "Heart Attack", "Pneumonia", "Acid Reflux", "Costochondritis"],
    "Shortness of Breath": ["Asthma", "Pneumonia", "Pulmonary Embolism", "Heart Failure", "COPD"],
    "Fatigue": ["Anemia", "Hypothyroidism", "Depression", "Influenza", "Chronic Fatigue Syndrome"],
    "Runny Nose": ["Common Cold", "Allergic Rhinitis", "Sinusitis", "Influenza"],
    "Headache": ["Migraine", "Tension Headache", "Sinusitis", "Hypertension", "Dehydration"],
    "Nausea": ["Gastroenteritis", "Food Poisoning", "Migraine", "Pregnancy", "Medication Side Effect"],
}

G = nx.Graph()
for symptom, conditions in MEDICAL_GRAPH.items():
    symptom_id = symptom.lower()
    for condition in conditions:
        G.add_edge(symptom_id, condition.lower(), relation="is_associated_with")


def get_context(query: str) -> dict:
    query_lower = query.lower()
    tokens = [token for token in re.split(r"[\s\W_]+", query_lower) if token]
    tokenized_query = " ".join(tokens)

    matches = []
    for symptom, conditions in MEDICAL_GRAPH.items():
        symptom_lower = symptom.lower()
        if symptom_lower in query_lower or symptom_lower in tokenized_query:
            matches.append(
                f"{symptom} -> {', '.join(conditions)}"
            )

    if not matches:
        return {"has_matches": False, "context": "No specific graph-based symptom or disease matches found."}

    return {"has_matches": True, "context": "\n".join(matches)}


def get_graph_data() -> dict:
    nodes = []
    edges = []
    seen_nodes = set()

    for symptom, conditions in MEDICAL_GRAPH.items():
        if symptom not in seen_nodes:
            nodes.append({"id": symptom, "label": symptom})
            seen_nodes.add(symptom)

        for condition in conditions:
            if condition not in seen_nodes:
                nodes.append({"id": condition, "label": condition})
                seen_nodes.add(condition)
            edges.append({"source": symptom, "target": condition})

    return {"nodes": nodes, "edges": edges}


def traverse_graph(query: str) -> str:
    return get_context(query)

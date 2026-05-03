import re

import networkx as nx

MEDICAL_GRAPH = {
    # Respiratory Symptoms
    "Persistent Cough": ["Lung Cancer", "Tuberculosis", "Bronchitis", "COPD", "Asthma", "Whooping Cough"],
    "Cough": ["Common Cold", "Influenza", "Bronchitis", "Pneumonia", "Asthma", "COVID-19"],
    "Blood in Sputum": ["Lung Cancer", "Tuberculosis", "Pulmonary Embolism", "Bronchiectasis"],
    "Hemoptysis": ["Lung Cancer", "Tuberculosis", "Pulmonary Embolism", "Bronchiectasis", "Lung Abscess"],
    "Shortness of Breath": ["Asthma", "COVID-19", "Heart Failure", "Pneumonia", "Pulmonary Embolism", "COPD", "Anemia"],
    "Wheezing": ["Asthma", "COPD", "Bronchitis", "Heart Failure", "Anaphylaxis"],
    
    # Chest Symptoms
    "Chest Pain": ["Lung Cancer", "Pneumonia", "Pleuritis", "Heart Attack", "Angina", "GERD", "Pulmonary Embolism"],
    "Chest Tightness": ["Asthma", "Angina", "Heart Attack", "GERD", "Anxiety"],
    
    # Systemic / Cancer Symptoms
    "Unexplained Weight Loss": ["Lung Cancer", "Tuberculosis", "Lymphoma", "Stomach Cancer", "Colon Cancer", "HIV/AIDS", "Hyperthyroidism"],
    "Fatigue": ["Anemia", "Hypothyroidism", "Cancer", "Heart Failure", "Depression", "Influenza", "COVID-19", "Chronic Fatigue Syndrome"],
    "Night Sweats": ["Tuberculosis", "Lymphoma", "Leukemia", "Menopause", "HIV/AIDS"],
    "Fever": ["Influenza", "COVID-19", "Bacterial Infection", "Malaria", "Tuberculosis", "Lymphoma"],
    "Swollen Lymph Nodes": ["Lymphoma", "Leukemia", "Tuberculosis", "Mononucleosis", "HIV/AIDS", "Bacterial Infection"],
    
    # Throat / ENT Symptoms
    "Throat Irritation": ["Allergic Rhinitis", "Viral Pharyngitis", "Acid Reflux", "Postnasal Drip", "Laryngitis"],
    "Sore Throat": ["Strep Throat", "Tonsillitis", "Flu", "Mononucleosis", "COVID-19"],
    "Hoarseness": ["Laryngitis", "Lung Cancer", "Thyroid Cancer", "GERD", "Vocal Cord Nodules"],
    "Runny Nose": ["Common Cold", "Allergic Rhinitis", "Flu", "Sinusitis"],
    
    # Neurological Symptoms
    "Headache": ["Migraine", "Tension Headache", "Hypertension", "Meningitis", "Brain Tumor", "Sinusitis"],
    "Dizziness": ["Vertigo", "Anemia", "Hypotension", "Stroke", "Inner Ear Infection"],
    "Seizures": ["Epilepsy", "Brain Tumor", "Meningitis", "Hypoglycemia", "Stroke"],
    "Memory Loss": ["Alzheimer's Disease", "Dementia", "Stroke", "Depression", "Brain Tumor"],
    "Numbness": ["Multiple Sclerosis", "Stroke", "Peripheral Neuropathy", "Diabetes", "Carpal Tunnel"],
    
    # Gastrointestinal Symptoms
    "Nausea": ["Gastroenteritis", "Pregnancy", "Migraine", "Appendicitis", "Food Poisoning"],
    "Vomiting": ["Gastroenteritis", "Food Poisoning", "Appendicitis", "Meningitis", "Bulimia"],
    "Abdominal Pain": ["Appendicitis", "IBS", "Gastritis", "Colon Cancer", "Kidney Stones", "Pancreatitis"],
    "Blood in Stool": ["Colon Cancer", "Hemorrhoids", "Crohn's Disease", "Ulcerative Colitis", "Diverticulitis"],
    "Jaundice": ["Hepatitis", "Liver Cancer", "Gallstones", "Pancreatitis", "Hemolytic Anemia"],
    "Bloating": ["IBS", "Lactose Intolerance", "Celiac Disease", "Colon Cancer", "Ovarian Cancer"],
    
    # Cardiovascular Symptoms
    "Palpitations": ["Arrhythmia", "Anxiety", "Hyperthyroidism", "Anemia", "Heart Failure"],
    "Leg Swelling": ["Heart Failure", "Deep Vein Thrombosis", "Kidney Disease", "Liver Disease", "Lymphedema"],
    "High Blood Pressure": ["Hypertension", "Kidney Disease", "Adrenal Tumor", "Sleep Apnea"],
    
    # Musculoskeletal Symptoms
    "Joint Pain": ["Rheumatoid Arthritis", "Osteoarthritis", "Lupus", "Gout", "Lyme Disease"],
    "Back Pain": ["Herniated Disc", "Muscle Strain", "Kidney Stones", "Osteoporosis", "Spinal Tumor"],
    "Muscle Weakness": ["Multiple Sclerosis", "ALS", "Myasthenia Gravis", "Hypothyroidism", "Stroke"],
    
    # Skin Symptoms
    "Rash": ["Eczema", "Psoriasis", "Lupus", "Allergic Reaction", "Shingles", "Lyme Disease"],
    "Jaundice Skin": ["Hepatitis", "Liver Cancer", "Gallstones", "Hemolytic Anemia"],
    "Pale Skin": ["Anemia", "Leukemia", "Internal Bleeding", "Hypothyroidism"],
    
    # Urological Symptoms
    "Blood in Urine": ["Kidney Cancer", "Bladder Cancer", "Kidney Stones", "UTI", "Prostate Cancer"],
    "Frequent Urination": ["Diabetes", "UTI", "Prostate Cancer", "Overactive Bladder", "Pregnancy"],
    
    # Endocrine Symptoms
    "Excessive Thirst": ["Diabetes Type 1", "Diabetes Type 2", "Diabetes Insipidus", "Hypercalcemia"],
    "Weight Gain": ["Hypothyroidism", "Cushing's Syndrome", "PCOS", "Depression", "Heart Failure"],
    "Heat Intolerance": ["Hyperthyroidism", "Menopause", "Anxiety", "Multiple Sclerosis"],
    
    # Eye Symptoms
    "Vision Loss": ["Glaucoma", "Macular Degeneration", "Diabetic Retinopathy", "Stroke", "Brain Tumor"],
    "Double Vision": ["Multiple Sclerosis", "Stroke", "Brain Tumor", "Myasthenia Gravis"],
    
    # Cancer-Specific
    "Lump in Breast": ["Breast Cancer", "Fibroadenoma", "Cyst", "Mastitis"],
    "Difficulty Swallowing": ["Esophageal Cancer", "Throat Cancer", "GERD", "Stroke", "Achalasia"],
    "Bone Pain": ["Bone Cancer", "Multiple Myeloma", "Metastatic Cancer", "Osteoporosis", "Paget's Disease"],
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

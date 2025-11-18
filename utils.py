from datetime import datetime, timedelta
import os
import re
from sqlalchemy import or_
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_pagination(page, per_page=10):
    """Helper function to get pagination parameters."""
    return {
        'page': max(1, int(page) if str(page).isdigit() else 1),
        'per_page': min(50, max(1, int(per_page) if str(per_page).isdigit() else 10))
    }

def apply_case_filters(query, args):
    """Apply filters to case query based on request arguments."""
    from models import Case  # Import here to avoid circular imports
    
    # Filter by client
    client_id = args.get('client_id')
    if client_id and client_id.isdigit():
        query = query.filter(Case.client_id == int(client_id))
    
    # Filter by status
    status = args.get('status')
    if status in ['open', 'in_progress', 'closed']:
        query = query.filter(Case.status == status)
    
    # Filter by priority
    priority = args.get('priority')
    if priority in ['high', 'medium', 'low']:
        query = query.filter(Case.priority == priority)
    
    # Search by title or description
    search = args.get('search')
    if search:
        search = f"%{search}%"
        query = query.filter(
            or_(
                Case.title.ilike(search),
                Case.description.ilike(search),
                # Case.case_number does not exist; limit search to title/description
            )
        )
    
    return query

def get_sort_params(args, default_sort='-created_at'):
    """Get sort parameters from request arguments."""
    from models import Case  # Import here to avoid circular imports
    
    sort = args.get('sort', default_sort)
    sort_field = sort.lstrip('-')
    sort_order = 'desc' if sort.startswith('-') else 'asc'
    
    # Map sort fields to model columns
    sort_mapping = {
        'title': Case.title,
        'status': Case.status,
        'priority': Case.priority,
        'created_at': Case.created_at,
        'updated_at': Case.updated_at,
        'client_name': 'Client.last_name'  # This will be handled specially
    }
    
    # Default sort column if the requested one doesn't exist
    sort_column = sort_mapping.get(sort_field, Case.created_at)
    
    # Special handling for client name sorting
    if sort_field == 'client_name':
        from models import Client
        sort_column = Client.last_name
    
    return sort_field, sort_order


def extract_entities(text):
    """Extract entities using regex patterns."""
    if not text:
        return {}
    
    patterns = {
        'dates': r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        'emails': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone_numbers': r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        'amounts': r'\$\d+(?:\.\d{1,2})?\b|\b\d+\s*(?:dollars|USD)\b',
        'locations': r'\b(?:\d+\s+[\w\s]+,?\s+[A-Z]{2}\s+\d{5}\b|\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Lane|Ln\.?|Drive|Dr\.?|Court|Ct\.?|Way|Terrace|Trl\.?|Trail|Plaza|Pl\.?|Square|Sq\.?|Circle|Cir\.?|Highway|Hwy\.?|Freeway|Fwy\.?|Turnpike|Tpke\.?|Parkway|Pkwy\.?|Alley|Aly\.?|Bend|Bnd\.?|Cove|Cv\.?|Creek|Crk\.?|Grove|Grv\.?|Hollow|Hlw\.?|Island|Isl\.?|Junction|Jct\.?|Knoll|Knl\.?|Meadow|Mdw\.?|Mountain|Mtn\.?|Oval|Ovl\.?|Path|Pth\.?|Ridge|Rdg\.?|Run|Rn\.?|Spring|Spg\.?|Summit|Smt\.?|View|Vw\.?|Village|Vlg\.?|Way|Wy\.?))\b',
    }
    
    entities = {}
    for entity_type, pattern in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            entities[entity_type] = list(set(matches))  # Remove duplicates
    
    return entities

def classify_case(description):
    """Classify case using keyword matching and rules."""
    if not description or not description.strip():
        return 'other', 0.0
    
    description_lower = description.lower()
    
    # Define keywords and their weights for each category
    category_keywords = {
        'family': {
            'divorce': 2, 'custody': 2, 'child support': 2, 'alimony': 2, 'marriage': 1,
            'spousal support': 2, 'paternity': 2, 'adoption': 2, 'guardianship': 1
        },
        'criminal': {
            'arrest': 2, 'bail': 2, 'felony': 2, 'misdemeanor': 2, 'theft': 2,
            'assault': 2, 'dui': 2, 'battery': 2, 'robbery': 2, 'fraud': 2
        },
        'civil': {
            'lawsuit': 2, 'negligence': 2, 'injury': 2, 'damages': 2, 'breach': 2,
            'contract': 2, 'tort': 2, 'compensation': 1, 'liability': 2
        },
        'employment': {
            'employer': 2, 'employee': 2, 'termination': 2, 'discrimination': 2,
            'harassment': 2, 'wage': 2, 'overtime': 2, 'wrongful termination': 2
        },
        'real_estate': {
            'property': 2, 'lease': 2, 'landlord': 2, 'tenant': 2, 'eviction': 2,
            'mortgage': 2, 'deed': 2, 'zoning': 1, 'title': 1
        }
    }
    
    # Calculate scores for each category
    scores = {category: 0 for category in category_keywords}
    for category, keywords in category_keywords.items():
        for keyword, weight in keywords.items():
            if keyword in description_lower:
                scores[category] += weight
    
    # Get the category with the highest score
    if not any(scores.values()):
        return 'other', 0.5
    
    best_category = max(scores, key=scores.get)
    confidence = min(1.0, scores[best_category] / 10.0)  # Normalize to 0-1 range
    
    return best_category, confidence

def analyze_case(description):
    """Analyze case description and provide structured insights."""
    if not description or not description.strip():
        return {
            'category': 'other',
            'confidence': 0.0,
            'entities': {},
            'suggested_actions': [
                'Review case details',
                'Schedule client meeting',
                'Gather additional information'
            ],
            'risk_level': 'medium',
            'summary': 'No description provided.'
        }
    
    # Classify the case
    category, confidence = classify_case(description)
    
    # Extract entities
    entities = extract_entities(description)
    
    # Define suggested actions based on category
    suggested_actions = {
        'family': [
            'Schedule initial consultation with family law attorney',
            'Gather financial documents',
            'Prepare list of assets and debts',
            'Document child custody preferences',
            'Review state-specific family law requirements'
        ],
        'criminal': [
            'Document all events and evidence',
            'Gather witness statements',
            'Review police reports',
            'Prepare for arraignment',
            'Discuss possible defense strategies'
        ],
        'civil': [
            'Document all relevant communications',
            'Gather supporting evidence',
            'Calculate potential damages',
            'Review applicable statutes of limitations',
            'Prepare demand letter if applicable'
        ],
        'employment': [
            'Document all incidents with dates and details',
            'Gather employment contracts and policies',
            'Review company handbook',
            'Document any witnesses',
            'Review state employment laws'
        ],
        'real_estate': [
            'Review all property documents',
            'Check property title and liens',
            'Document all communications',
            'Review lease/contract terms',
            'Schedule property inspection if needed'
        ]
    }
    
    # Default actions if category not found
    default_actions = [
        'Review case details',
        'Schedule client meeting',
        'Gather additional information',
        'Research applicable laws',
        'Prepare case strategy'
    ]
    
    # Determine risk level based on keywords
    risk_keywords = {
        'high': ['emergency', 'urgent', 'immediate', 'danger', 'harm', 'violence', 'threat', 'eviction', 'injunction'],
        'medium': ['dispute', 'conflict', 'issue', 'problem', 'concern', 'complaint'],
        'low': ['inquiry', 'question', 'general', 'information', 'advice']
    }
    
    risk_level = 'low'
    description_lower = description.lower()
    if any(word in description_lower for word in risk_keywords['high']):
        risk_level = 'high'
    elif any(word in description_lower for word in risk_keywords['medium']):
        risk_level = 'medium'
    
    # Generate summary based on category and key entities
    summary_parts = [f"Case classified as '{category.replace('_', ' ')}' with {int(confidence * 100)}% confidence."]
    
    if 'dates' in entities and entities['dates']:
        summary_parts.append(f"Key dates identified: {', '.join(entities['dates'][:2])}.")
    if 'amounts' in entities and entities['amounts']:
        summary_parts.append(f"Monetary amounts mentioned: {', '.join(entities['amounts'][:2])}.")
    
    summary = ' '.join(summary_parts)
    
    return {
        'category': category,
        'confidence': confidence,
        'entities': entities,
        'suggested_actions': suggested_actions.get(category, default_actions)[:5],
        'risk_level': risk_level,
        'summary': summary
    }

# ---------------- Scenario-focused Analyzer ---------------- #
RELATIVE_DATE_PATTERNS = [
    r"yesterday",
    r"last\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
    r"last\s+week",
    r"last\s+month",
    r"\b\d{1,2}\s*(?:am|pm)\b",
]

def extract_relative_dates(text):
    if not text:
        return []
    found = []
    for pat in RELATIVE_DATE_PATTERNS:
        matches = re.findall(pat, text, flags=re.IGNORECASE)
        if matches:
            found.extend(matches)
    return list(set(found))

def analyze_intake_text_scenarios(text):
    """Scenario analyzer for four core intake scenarios.
    Returns a structured dict with: category, urgency, department, priority, key_facts, dates, suggested_actions, checklists, case_type_key.
    """
    if not text:
        return {
            'category': 'other',
            'urgency': 'medium',
            'department': 'General',
            'priority': 'Medium',
            'key_facts': {},
            'dates': [],
            'suggested_actions': ['Review case details', 'Schedule client meeting'],
            'checklists': {}
        }

    t = text.lower()
    ents = extract_entities(text)
    rel_dates = extract_relative_dates(text)
    dates = list(set(ents.get('dates', []) + rel_dates))

    def result(category, department, priority, urgency, key_facts, suggested_actions, checklists, case_type_key=None):
        return {
            'category': category,
            'department': department,
            'priority': priority,
            'urgency': urgency,
            'key_facts': key_facts,
            'dates': dates,
            'suggested_actions': suggested_actions,
            'checklists': checklists,
            'case_type_key': case_type_key,
        }

    # Scenario 1: Slip and Fall at Walmart (Premises Liability)
    if any(k in t for k in ['walmart']) and any(k in t for k in ['slip', 'slipped']) and any(k in t for k in ['water', 'wet floor', 'produce']):
        key_facts = {
            'store': 'Walmart',
            'hazard': 'Wet floor/water',
            'injuries': 'Back/knee' if ('back' in t or 'knee' in t) else None,
            'medical_visit': 'Yes' if ('hospital' in t or 'er' in t or 'emergency' in t) else 'Unknown',
            'warning_sign': 'No' if ('no sign' in t or 'no warning' in t or 'no wet floor sign' in t) else 'Unknown',
        }
        suggested_actions = [
            'Send evidence preservation letter to Walmart within 1 hour',
            'Request staff list and cleaning logs for incident day',
            'Request security footage (produce, entrance, registers) 2h window',
            'Obtain medical records and generate HIPAA release',
            'Collect client details (shoes, photos, witnesses, incident report)'
        ]
        checklists = {
            'medical_records': ['ER records', 'Imaging', 'Doctor notes', 'Prescriptions', 'PT records', 'Follow-ups'],
            'client_questions': ['Shoes worn', 'Photos taken', 'Reported to employee', 'Incident report filed', 'Witnesses info', 'Nature/duration of spill']
        }
        return result(
            'Personal Injury - Premises Liability', 'Personal Injury', 'High', 'High', key_facts, suggested_actions, checklists, case_type_key='pi_slip_fall'
        )

    # Scenario 2: Car Accident
    if ('accident' in t or 'collision' in t or 'crash' in t) and any(k in t for k in ['highway', 'road', 'intersection']):
        insurer = None
        for name in ['statefarm', 'geico', 'progressive', 'allstate', 'farmers']:
            if name in t:
                insurer = name.title()
                break
        key_facts = {
            'location': 'Highway/Intersection',
            'other_driver': 'Red pickup' if 'red pickup' in t else 'Unknown',
            'violation': 'Ran red light' if 'ran a red light' in t or 'ran the red light' in t else 'Unknown',
            'injury': 'Neck' if 'neck' in t else ('Injured' if 'injur' in t else 'Unknown'),
            'vehicle_totaled': True if 'totaled' in t else False,
            'other_insurance': insurer,
        }
        suggested_actions = [
            'Request police accident report and preserve dash/911/witness/camera data',
            'Request DOT traffic/red-light camera footage 30m window',
            'Send letters of representation to client and adverse insurers',
            'Collect vehicle details (VIN, photos, estimates, KBB value)',
            'Schedule medical evaluation within 48 hours'
        ]
        checklists = {
            'vehicle_client': ['Make/Model/Year/VIN', 'Damage photos (all angles)', 'Repair estimates', 'Pre-accident valuation'],
            'medical': ['ER records', 'Ambulance report', 'Neck X-ray/CT', 'Doctor diagnosis', 'Track follow-ups'],
            'scene': ['Skid marks', 'Traffic signals', 'Signs', 'Road/weather', 'Surveillance cams']
        }
        return result('Car Accident / Auto Collision', 'Auto Accident', 'High', 'High', key_facts, suggested_actions, checklists, case_type_key='pi_motor_vehicle')

    # Scenario 3: Employment Law - Age Discrimination
    if ('discrimination' in t or 'harassment' in t or 'pushed out' in t) and any(k in t for k in ['age', 'older', 'retire']):
        key_facts = {
            'employer': 'TechCorp' if 'techcorp' in t else None,
            'age': '58' if '58' in t else None,
            'manager': 'New manager 6 months ago' if '6 months' in t and 'manager' in t else None,
            'performance_review': 'Recent negative review' if 'performance review' in t or 'bad review' in t else None,
        }
        suggested_actions = [
            'Send litigation hold to employer (HR & Legal)',
            'Collect job title, salary/benefits, manager & HR contacts, reviews, messages',
            'Request complete personnel file',
            'Prepare EEOC charge; set 180/300 day deadline',
            'Comparator analysis questionnaire'
        ]
        checklists = {
            'evidence_direct': ['Emails with age-related comments', 'Texts', 'Witness statements'],
            'evidence_circumstantial': ['Compare to younger employees', 'Duty changes', 'Review pattern shifts', 'Stat data'],
            'files': ['Personnel file', 'All reviews', 'Discipline actions', 'Promotions/raises', 'Job descriptions']
        }
        return result('Employment Law - Age Discrimination', 'Employment Law', 'Medium-High', 'Medium-High', key_facts, suggested_actions, checklists, case_type_key='employment_discrimination')

    # Scenario 4: Medical Malpractice
    if any(k in t for k in ['sponge', 'retained foreign', 'left inside']) and any(k in t for k in ['surgery', 'surgeon']):
        key_facts = {
            'procedure': 'Gallbladder removal' if 'gallbladder' in t else 'Surgery',
            'hospital': 'City Hospital' if 'city hospital' in t else None,
            'surgeon': 'Dr. Roberts' if 'dr. roberts' in t else None,
            'complication': 'Retained sponge',
            'second_surgery': True if 'second surgery' in t or 'another surgery' in t else None,
            'missed_work': True if 'missed work' in t else None,
        }
        suggested_actions = [
            'Immediate full medical records requests (both hospitals) with HIPAA',
            'Litigation hold to hospital (Risk & Legal)',
            'Identify full surgical team',
            'Retain expert witness (general surgeon) for merit review',
            'Set SOL & discovery-rule deadlines'
        ]
        checklists = {
            'records_city_hospital': ['Pre-op', 'Operative report', 'Anesthesia', 'Nursing notes', 'Post-op', 'Follow-ups', 'Imaging', 'Labs', 'ER records', 'Communications'],
            'records_other_hospital': ['Admission/ER', 'Sponge removal surgery report', 'Imaging proving sponge', 'Pathology'],
            'policies': ['Sponge count procedures', 'OR logs', 'Credentialing for surgeon', 'Incident/peer review (if applicable)']
        }
        return result('Medical Malpractice', 'Medical Malpractice', 'High', 'High', key_facts, suggested_actions, checklists, case_type_key='med_mal_general')

    # Fallback
    return {
        'category': 'other',
        'department': 'General',
        'priority': 'Medium',
        'urgency': 'Medium',
        'key_facts': {},
        'dates': dates,
        'suggested_actions': ['Review case details', 'Schedule client meeting'],
        'checklists': {},
        'case_type_key': None,
    }


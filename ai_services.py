import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import re
from collections import Counter
import json

# Try to import SpaCy, but don't fail if it's not available
try:
    import spacy
    from spacy.lang.en.stop_words import STOP_WORDS
    from spacy.matcher import PhraseMatcher, Matcher
    from spacy.tokens import Span
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("SpaCy is not available. Some AI features will be limited.")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Legal-specific configuration
LEGAL_ENTITIES = {
    'COURT': ['supreme court', 'district court', 'high court', 'magistrate court', 'family court'],
    'LEGAL_DOC': ['affidavit', 'summons', 'writ', 'motion', 'pleading', 'complaint', 'subpoena'],
    'LEGAL_ACTION': ['sue', 'suing', 'lawsuit', 'litigation', 'appeal', 'settlement', 'arbitration'],
    'LEGAL_TERM': ['negligence', 'liability', 'tort', 'breach', 'contract', 'damages', 'injunction']
}

CASE_TYPES = [
    'personal_injury', 'family_law', 'criminal_defense',
    'employment_law', 'real_estate', 'intellectual_property',
    'business_law', 'immigration', 'bankruptcy', 'other'
]

# Keywords for case type classification
CASE_TYPE_KEYWORDS = {
    'personal_injury': ['accident', 'injury', 'negligence', 'damages', 'medical malpractice', 'slip and fall'],
    'family_law': ['divorce', 'custody', 'child support', 'alimony', 'adoption', 'prenuptial'],
    'criminal_defense': ['arrest', 'charge', 'felony', 'misdemeanor', 'bail', 'sentencing', 'appeal'],
    'employment_law': ['discrimination', 'harassment', 'wrongful termination', 'wage', 'overtime', 'FMLA'],
    'real_estate': ['property', 'lease', 'landlord', 'tenant', 'title', 'zoning', 'foreclosure'],
    'intellectual_property': ['trademark', 'copyright', 'patent', 'infringement', 'trade secret'],
    'business_law': ['contract', 'merger', 'acquisition', 'incorporation', 'partnership', 'franchise'],
    'immigration': ['visa', 'green card', 'citizenship', 'deportation', 'asylum', 'work permit'],
    'bankruptcy': ['chapter 7', 'chapter 11', 'chapter 13', 'debt relief', 'creditors', 'discharge']
}

class AICaseAnalyzer:
    """Handles AI-powered analysis of case documents and text."""
    
    def __init__(self):
        self.nlp = None
        self.legal_matcher = None
        self.case_type_classifier = None
        self._initialize_nlp()
        self._initialize_legal_components()
    
    def _initialize_nlp(self):
        """Initialize the NLP model if available."""
        if not SPACY_AVAILABLE:
            logger.warning("SpaCy is not available. AI analysis will be limited.")
            return
            
        try:
            # First try to load the model normally
            self.nlp = spacy.load("en_core_web_lg")  # Using larger model for better accuracy
            logger.info("Loaded SpaCy English model")
        except OSError:
            # If the model isn't found, try to download it
            try:
                import subprocess
                import sys
                logger.info("Downloading SpaCy English model...")
                subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_lg"])
                self.nlp = spacy.load("en_core_web_lg")
                logger.info("Successfully downloaded and loaded SpaCy English model")
            except Exception as e:
                logger.error(f"Failed to load SpaCy model: {e}")
                logger.warning("AI features will be limited without SpaCy")
    
    def _initialize_legal_components(self):
        """Initialize legal-specific components."""
        if not self.nlp:
            return
            
        # Add custom entity ruler for legal entities
        if 'entity_ruler' not in self.nlp.pipe_names:
            ruler = self.nlp.add_pipe('entity_ruler', before='ner')
            patterns = []
            
            # Add patterns for legal entities
            for entity_type, terms in LEGAL_ENTITIES.items():
                for term in terms:
                    patterns.append({"label": entity_type, "pattern": term.lower()})
                    patterns.append({"label": entity_type, "pattern": [{"LOWER": term.lower()}]})
            
            ruler.add_patterns(patterns)
            
        # Initialize matcher for legal phrases
        self.legal_matcher = PhraseMatcher(self.nlp.vocab, attr='LOWER')
        for label, patterns in CASE_TYPE_KEYWORDS.items():
            self.legal_matcher.add(label, [self.nlp.make_doc(text) for text in patterns])
    
    def analyze_text(self, text: str, analyze_case_type: bool = True) -> Dict[str, Any]:
        """
        Analyze legal text and extract key information.
        
        Args:
            text: The text to analyze
            analyze_case_type: Whether to perform case type classification
            
        Returns:
            Dict containing analysis results
        """
        if not text or not isinstance(text, str):
            return {
                "error": "Invalid input text",
                "analyzed_at": datetime.utcnow().isoformat()
            }
        
        if not self.nlp:
            return self._fallback_analyze_text(text)
        
        try:
            doc = self.nlp(text.lower())
            
            # Extract entities with custom legal entities
            entities = []
            legal_entities = {}
            
            # Add default entities
            for ent in doc.ents:
                entity = {"text": ent.text, "label": ent.label_, "start": ent.start_char, "end": ent.end_char}
                entities.append(entity)
                
                # Group entities by label
                if ent.label_ not in legal_entities:
                    legal_entities[ent.label_] = []
                legal_entities[ent.label_].append(ent.text)
            
            # Extract key legal terms and phrases
            key_phrases = [chunk.text for chunk in doc.noun_chunks if len(chunk) > 1]
            
            # Enhanced sentiment analysis with legal context
            sentiment = self._get_legal_sentiment(doc)
            
            # Extract key information
            dates = legal_entities.get('DATE', [])
            money = legal_entities.get('MONEY', [])
            legal_parties = legal_entities.get('PERSON', []) + legal_entities.get('ORG', [])
            
            # Analyze case type if requested
            case_analysis = {}
            if analyze_case_type:
                case_analysis = self.analyze_case_type(doc)
            
            # Build comprehensive analysis result
            result = {
                "entities": entities,
                "legal_entities": legal_entities,
                "key_phrases": key_phrases,
                "sentiment": sentiment,
                "dates": dates,
                "money": money,
                "legal_parties": list(set(legal_parties)),
                "word_count": len(doc),
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
            # Add case type analysis if available
            if case_analysis:
                result["case_analysis"] = case_analysis
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return self._fallback_analyze_text(text)
    
    def _fallback_analyze_text(self, text: str) -> Dict[str, Any]:
        """Fallback text analysis when SpaCy is not available."""
        words = text.split()
        word_count = len(words)
        
        # Very simple fallback analysis
        return {
            "entities": [],
            "key_phrases": [],
            "sentiment": {
                "score": 0,
                "label": "neutral"
            },
            "dates": [],
            "money": [],
            "word_count": word_count,
            "analyzed_at": datetime.utcnow().isoformat(),
            "warning": "Basic analysis used - install SpaCy for more accurate results"
        }
    
    def _get_legal_sentiment(self, doc) -> Dict[str, Any]:
        """Enhanced sentiment analysis with legal context."""
        if not self.nlp:
            return {"score": 0.0, "label": "neutral", "confidence": 0.0}
        
        # Legal-specific sentiment indicators
        positive_indicators = [
            'favorable', 'win', 'won', 'success', 'successful', 'awarded',
            'granted', 'approved', 'dismissed with prejudice'
        ]
        
        negative_indicators = [
            'denied', 'rejected', 'dismissed', 'loss', 'lost', 'liable',
            'guilty', 'breach', 'violation', 'damages', 'injunction'
        ]
        
        # Count indicators in text
        text = doc.text.lower()
        pos_count = sum(text.count(indicator) for indicator in positive_indicators)
        neg_count = sum(text.count(indicator) for indicator in negative_indicators)
        
        # Calculate confidence (0.0 to 1.0)
        total = pos_count + neg_count
        confidence = min(total / 10.0, 1.0)  # Cap confidence at 1.0
        
        # Determine sentiment
        if pos_count > neg_count:
            score = min(0.5 + (pos_count * 0.1), 1.0)
            return {
                "score": score,
                "label": "positive",
                "confidence": confidence,
                "indicators": {"positive": pos_count, "negative": neg_count}
            }
        elif neg_count > pos_count:
            score = max(-0.5 - (neg_count * 0.1), -1.0)
            return {
                "score": score,
                "label": "negative",
                "confidence": confidence,
                "indicators": {"positive": pos_count, "negative": neg_count}
            }
        
        return {
            "score": 0.0,
            "label": "neutral",
            "confidence": confidence,
            "indicators": {"positive": pos_count, "negative": neg_count}
        }
    
    def analyze_case_type(self, doc) -> Dict[str, Any]:
        """
        Analyze text to determine the most likely case type.
        
        Returns:
            Dict with case type, confidence, and supporting evidence
        """
        if not self.nlp or not hasattr(self, 'legal_matcher'):
            return {
                "case_type": "unknown",
                "confidence": 0.0,
                "evidence": [],
                "possible_types": []
            }
        
        # Get matches and count occurrences
        matches = self.legal_matcher(doc)
        type_counts = {}
        
        for match_id, start, end in matches:
            label = self.nlp.vocab.strings[match_id]
            type_counts[label] = type_counts.get(label, 0) + 1
        
        # Calculate confidence
        total_matches = sum(type_counts.values())
        if total_matches == 0:
            return {
                "case_type": "other",
                "confidence": 0.0,
                "evidence": [],
                "possible_types": []
            }
        
        # Get top case type
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        top_type, top_count = sorted_types[0]
        confidence = min(top_count / (total_matches * 0.8), 1.0)  # Scale confidence
        
        # Get supporting evidence
        evidence = []
        for match_id, start, end in matches:
            if self.nlp.vocab.strings[match_id] == top_type:
                evidence.append(doc[start:end].text)
        
        # Get other possible types with scores
        possible_types = [
            {"type": t, "score": c/total_matches, "count": c}
            for t, c in sorted_types[:3]  # Top 3 possible types
        ]
        
        return {
            "case_type": top_type,
            "confidence": round(confidence, 2),
            "evidence": evidence[:5],  # Return up to 5 pieces of evidence
            "possible_types": possible_types
        }
    
    def extract_case_details(self, text: str) -> Dict[str, Any]:
        """Extract structured case details from text."""
        if not self.nlp:
            return self._fallback_extract_case_details(text)
            
        try:
            doc = self.nlp(text)
            
            # Initialize case details
            details = {
                "potential_categories": [],
                "key_parties": [],
                "potential_issues": [],
                "urgency_level": self._determine_urgency(doc)
            }
            
            # Extract potential case categories based on entities and keywords
            legal_terms = {
                "PERSON": "Individual",
                "ORG": "Organization",
                "GPE": "Geopolitical Entity",
                "LAW": "Legal Matter",
                "MONEY": "Financial"
            }
            
            # Add entities to potential categories
            for ent in doc.ents:
                if ent.label_ in legal_terms:
                    details["potential_categories"].append(legal_terms[ent.label_])
                    
                    if ent.label_ in ["PERSON", "ORG"]:
                        details["key_parties"].append({
                            "name": ent.text,
                            "type": legal_terms[ent.label_],
                            "role": "Party"  # This could be enhanced with more context
                        })
            
            # Extract potential legal issues
            legal_issue_keywords = {
                "breach": "Contract Breach",
                "injury": "Personal Injury",
                "discrimination": "Employment Law",
                "termination": "Employment Law",
                "copyright": "Intellectual Property",
                "trademark": "Intellectual Property",
                "patent": "Intellectual Property",
                "eviction": "Housing Law",
                "landlord": "Housing Law",
                "tenant": "Housing Law"
            }
            
            for token in doc:
                if token.lemma_.lower() in legal_issue_keywords:
                    issue = legal_issue_keywords[token.lemma_.lower()]
                    if issue not in details["potential_issues"]:
                        details["potential_issues"].append(issue)
            
            # Remove duplicates
            details["potential_categories"] = list(set(details["potential_categories"]))
            
            return details
            
        except Exception as e:
            logger.error(f"Error extracting case details: {e}")
            return self._fallback_extract_case_details(text)
    
    def _fallback_extract_case_details(self, text: str) -> Dict[str, Any]:
        """Fallback case details extraction when SpaCy is not available."""
        return {
            "potential_categories": [],
            "key_parties": [],
            "potential_issues": [],
            "urgency_level": "medium",
            "warning": "Basic analysis used - install SpaCy for more accurate results"
        }
    
    def _determine_urgency(self, doc) -> str:
        """Determine urgency level based on text content."""
        if not hasattr(doc, '__iter__'):
            return "medium"
            
        urgent_indicators = {"urgent", "immediate", "asap", "emergency", "deadline", "court date"}
        
        for token in doc:
            if token.text.lower() in urgent_indicators:
                return "high"
                
        # Check for dates in the near future (next 7 days)
        today = datetime.now()
        for ent in (e for e in doc.ents if hasattr(e, 'label_')):
            if ent.label_ == "DATE":
                try:
                    # This is a simplified example - in production, you'd want a more robust date parser
                    if "tomorrow" in ent.text.lower() or "today" in ent.text.lower():
                        return "high"
                except:
                    continue
                    
        return "medium"  # Default to medium urgency
    
    def extract_case_details(self, text: str) -> Dict:
        """Extract structured case details from text."""
        doc = self.nlp(text)
        
        # Initialize case details
        details = {
            "potential_categories": [],
            "key_parties": [],
            "potential_issues": [],
            "urgency_level": self._determine_urgency(doc)
        }
        
        # Extract potential case categories based on entities and keywords
        legal_terms = {
            "PERSON": "Individual",
            "ORG": "Organization",
            "GPE": "Geopolitical Entity",
            "LAW": "Legal Matter",
            "MONEY": "Financial"
        }
        
        # Add entities to potential categories
        for ent in doc.ents:
            if ent.label_ in legal_terms:
                details["potential_categories"].append(legal_terms[ent.label_])
                
                if ent.label_ in ["PERSON", "ORG"]:
                    details["key_parties"].append({
                        "name": ent.text,
                        "type": legal_terms[ent.label_],
                        "role": "Party"  # This could be enhanced with more context
                    })
        
        # Extract potential legal issues
        legal_issue_keywords = {
            "breach": "Contract Breach",
            "injury": "Personal Injury",
            "discrimination": "Employment Law",
            "termination": "Employment Law",
            "copyright": "Intellectual Property",
            "trademark": "Intellectual Property",
            "patent": "Intellectual Property",
            "eviction": "Housing Law",
            "landlord": "Housing Law",
            "tenant": "Housing Law"
        }
        
        for token in doc:
            if token.lemma_.lower() in legal_issue_keywords:
                issue = legal_issue_keywords[token.lemma_.lower()]
                if issue not in details["potential_issues"]:
                    details["potential_issues"].append(issue)
        
        # Remove duplicates
        details["potential_categories"] = list(set(details["potential_categories"]))
        
        return details
    
    def _determine_urgency(self, doc) -> str:
        """Determine urgency level based on text content."""
        urgent_indicators = {"urgent", "immediate", "asap", "emergency", "deadline", "court date"}
        
        for token in doc:
            if token.text.lower() in urgent_indicators:
                return "high"
                
        # Check for dates in the near future (next 7 days)
        today = datetime.now()
        for ent in doc.ents:
            if ent.label_ == "DATE":
                try:
                    # This is a simplified example - in production, you'd want a more robust date parser
                    if "tomorrow" in ent.text.lower() or "today" in ent.text.lower():
                        return "high"
                except:
                    continue
                    
        return "medium"  # Default to medium urgency

# Create a singleton instance
case_analyzer = AICaseAnalyzer()

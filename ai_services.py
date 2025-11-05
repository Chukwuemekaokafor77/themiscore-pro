import os
import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AICaseAnalyzer:
    """Handles AI-powered analysis of case documents and text using AssemblyAI API."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('ASSEMBLYAI_API_KEY')
        self.base_url = "https://api.assemblyai.com/v2"
        self.headers = {
            'authorization': self.api_key,
            'content-type': 'application/json'
        }
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze text using AssemblyAI's API.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict containing analysis results
        """
        if not text:
            return {"error": "No text provided", "analyzed_at": datetime.utcnow().isoformat()}
            
        try:
            # First, submit the text for analysis
            response = requests.post(
                f"{self.base_url}/analysis",
                headers=self.headers,
                json={
                    "text": text,
                    "analysis": {
                        "sentiment": True,
                        "entity_detection": True,
                        "auto_highlights": True,
                        "iab_categories": True
                    }
                }
            )
            response.raise_for_status()
            analysis_data = response.json()
            
            # Process the analysis results
            return self._process_analysis(analysis_data)
            
        except Exception as e:
            logger.error(f"Error analyzing text: {str(e)}")
            return {"error": str(e), "analyzed_at": datetime.utcnow().isoformat()}
    
    def analyze_audio_transcript(self, transcript_id: str) -> Dict[str, Any]:
        """
        Get analysis for an existing transcript.
        
        Args:
            transcript_id: AssemblyAI transcript ID
            
        Returns:
            Dict containing analysis results
        """
        try:
            response = requests.get(
                f"{self.base_url}/transcript/{transcript_id}",
                headers=self.headers,
                params={"sentiment_analysis": True, "entity_detection": True}
            )
            response.raise_for_status()
            return self._process_transcript_analysis(response.json())
            
        except Exception as e:
            logger.error(f"Error getting transcript analysis: {str(e)}")
            return {"error": str(e), "analyzed_at": datetime.utcnow().isoformat()}
    
    def _process_transcript_analysis(self, transcript_data: Dict) -> Dict[str, Any]:
        """Process transcript analysis results."""
        if not transcript_data:
            return {"error": "No transcript data", "analyzed_at": datetime.utcnow().isoformat()}
            
        # Get case type analysis from IAB categories
        iab_categories = transcript_data.get("iab_categories_result", {})
        case_type = self._determine_case_type(iab_categories)
        
        # Get sentiment analysis
        sentiment = transcript_data.get("sentiment_analysis_results", {})
        
        # Process entities
        entities = transcript_data.get("entities", [])
        legal_entities = {}
        legal_parties = []
        
        for entity in entities:
            entity_type = entity.get("entity_type", "")
            if entity_type not in legal_entities:
                legal_entities[entity_type] = []
            legal_entities[entity_type].append(entity.get("text", ""))
            
            # Identify potential legal parties
            if entity_type in ["PERSON", "ORG"]:
                legal_parties.append({
                    "name": entity.get("text", ""),
                    "type": entity_type,
                    "role": "Party"
                })
        
        # Process highlights
        highlights = transcript_data.get("auto_highlights_result", {}).get("results", [])
        
        return {
            "text": transcript_data.get("text", ""),
            "case_analysis": {
                "case_type": case_type.get("type", "other"),
                "confidence": case_type.get("confidence", 0.5),
                "evidence": case_type.get("categories", [])
            },
            "sentiment": {
                "score": sentiment.get("score", 0),
                "label": sentiment.get("label", "neutral"),
                "confidence": sentiment.get("confidence", 0.5)
            },
            "entities": entities,
            "legal_entities": legal_entities,
            "legal_parties": legal_parties,
            "highlights": [h.get("text", "") for h in highlights],
            "categories": iab_categories.get("results", []),
            "word_count": len(transcript_data.get("text", "").split()),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def _process_analysis(self, analysis_data: Dict) -> Dict[str, Any]:
        """Process analysis results into a consistent format."""
        if not analysis_data:
            return {"error": "No analysis data", "analyzed_at": datetime.utcnow().isoformat()}
            
        # Extract key information
        sentiment = analysis_data.get("sentiment", {})
        entities = analysis_data.get("entities", [])
        
        # Determine case type based on IAB categories
        case_type = self._determine_case_type(analysis_data.get("iab_categories", {}))
        
        # Process entities
        legal_entities = {}
        legal_parties = []
        
        for entity in entities:
            entity_type = entity.get("entity_type", "")
            if entity_type not in legal_entities:
                legal_entities[entity_type] = []
            legal_entities[entity_type].append(entity.get("text", ""))
            
            # Identify potential legal parties
            if entity_type in ["PERSON", "ORG"]:
                legal_parties.append({
                    "name": entity.get("text", ""),
                    "type": entity_type,
                    "role": "Party"
                })
        
        # Process highlights
        highlights = analysis_data.get("auto_highlights", {}).get("results", [])
        
        return {
            "case_analysis": {
                "case_type": case_type.get("type", "other"),
                "confidence": case_type.get("confidence", 0.5),
                "evidence": case_type.get("categories", [])
            },
            "sentiment": {
                "score": sentiment.get("score", 0),
                "label": sentiment.get("label", "neutral"),
                "confidence": sentiment.get("confidence", 0.5)
            },
            "entities": entities,
            "legal_entities": legal_entities,
            "legal_parties": legal_parties,
            "highlights": [h.get("text", "") for h in highlights],
            "categories": analysis_data.get("iab_categories", {}).get("results", []),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def _determine_case_type(self, iab_results: Dict) -> Dict:
        """Determine case type based on IAB categories."""
        if not iab_results or "results" not in iab_results:
            return {"type": "other", "confidence": 0.5, "categories": []}
            
        results = iab_results["results"]
        if not results:
            return {"type": "other", "confidence": 0.5, "categories": []}
            
        # Get top category
        top_category = max(results, key=lambda x: x.get("confidence", 0))
        
        # Map IAB categories to case types
        case_type_map = {
            "law, govt and politics": "legal",
            "business and finance": "business_law",
            "family and relationships": "family_law",
            "real estate": "real_estate",
            "careers": "employment_law",
            "technology and computing": "intellectual_property",
            "health": "personal_injury",
            "crime": "criminal_defense",
            "immigration": "immigration",
            "banking": "bankruptcy"
        }
        
        # Find matching case type
        for label in top_category.get("labels", []):
            if label.lower() in case_type_map:
                return {
                    "type": case_type_map[label.lower()],
                    "confidence": top_category.get("confidence", 0.5),
                    "categories": [label]
                }
                
        return {
            "type": "other",
            "confidence": top_category.get("confidence", 0.5),
            "categories": [top_category.get("label", "unknown")]
        }
    
    def extract_case_details(self, text: str) -> Dict[str, Any]:
        """Extract structured case details from text."""
        try:
            # Analyze the text first
            analysis = self.analyze_text(text)
            
            if "error" in analysis:
                return self._fallback_extract_case_details(text)
            
            # Extract key parties (PERSON and ORG entities)
            key_parties = []
            for entity in analysis.get("entities", []):
                if entity.get("entity_type") in ["PERSON", "ORG"]:
                    key_parties.append({
                        "name": entity.get("text", ""),
                        "type": entity.get("entity_type", ""),
                        "role": "Party"
                    })
            
            # Map case types to potential issues
            case_type = analysis.get("case_analysis", {}).get("case_type", "other")
            issue_map = {
                "personal_injury": ["Personal Injury", "Medical Malpractice"],
                "family_law": ["Divorce", "Child Custody", "Adoption"],
                "criminal_defense": ["Criminal Charges", "DUI", "Theft"],
                "employment_law": ["Wrongful Termination", "Discrimination", "Harassment"],
                "real_estate": ["Property Dispute", "Lease Agreement", "Zoning"],
                "intellectual_property": ["Copyright Infringement", "Trademark Violation", "Patent Dispute"],
                "business_law": ["Contract Dispute", "Business Formation", "Partnership Dispute"],
                "immigration": ["Visa Application", "Deportation Defense", "Citizenship"],
                "bankruptcy": ["Chapter 7", "Chapter 11", "Debt Relief"]
            }
            
            potential_issues = issue_map.get(case_type, ["Legal Consultation Needed"])
            
            # Determine urgency based on sentiment and content
            sentiment_score = analysis.get("sentiment", {}).get("score", 0)
            urgency = "medium"
            
            # Check for urgent keywords in highlights
            urgent_terms = ["urgent", "immediate", "asap", "emergency", "deadline", "court date"]
            highlights = " ".join(analysis.get("highlights", [])).lower()
            
            if any(term in highlights for term in urgent_terms) or sentiment_score < -0.5:
                urgency = "high"
            elif sentiment_score > 0.5:
                urgency = "low"
            
            return {
                "potential_categories": [case_type.replace("_", " ").title()],
                "key_parties": key_parties,
                "potential_issues": potential_issues,
                "urgency_level": urgency,
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error extracting case details: {str(e)}")
            return self._fallback_extract_case_details(text)
    
    def _fallback_extract_case_details(self, text: str) -> Dict[str, Any]:
        """Fallback case details extraction when analysis fails."""
        return {
            "potential_categories": ["Legal Consultation Needed"],
            "key_parties": [],
            "potential_issues": ["Legal Consultation Needed"],
            "urgency_level": "medium",
            "warning": "Basic analysis used - full analysis unavailable",
            "analyzed_at": datetime.utcnow().isoformat()
        }

# Create a singleton instance
case_analyzer = AICaseAnalyzer()

# Create a singleton instance
case_analyzer = AICaseAnalyzer()

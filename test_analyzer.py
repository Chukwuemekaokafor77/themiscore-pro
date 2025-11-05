from ai_services import AICaseAnalyzer
import json

# Sample legal texts for testing
SAMPLE_TEXTS = [
    """
    My client, John Smith, was involved in a car accident on Main Street on March 15, 2023.
    The other driver ran a red light and caused significant damage to my client's vehicle.
    My client suffered whiplash and back injuries requiring medical treatment.
    We are seeking $50,000 in damages for medical bills and pain and suffering.
    """,
    
    """
    I am representing Sarah Johnson in her divorce proceedings against Michael Johnson.
    We need to address child custody for their two children, asset division, and spousal support.
    The marital home is valued at $450,000 and there are retirement accounts to be divided.
    """,
    
    """
    Our client, TechCorp Inc., is being sued for patent infringement by Innovate LLC.
    The lawsuit claims we violated their patent (US Patent No. 9,876,543) related to wireless charging technology.
    We believe their patent is invalid due to prior art from 2010.
    """
]

def test_analyzer():
    print("Initializing AICaseAnalyzer...")
    analyzer = AICaseAnalyzer()
    
    for i, text in enumerate(SAMPLE_TEXTS, 1):
        print(f"\n{'='*50}")
        print(f"SAMPLE {i}:")
        print("-" * 30)
        print(text.strip())
        print("-" * 30)
        
        # Analyze the text
        result = analyzer.analyze_text(text)
        
        # Extract and display key information
        print("\nANALYSIS:")
        print("-" * 30)
        
        # Case Type Analysis
        case_analysis = result.get('case_analysis', {})
        print(f"Case Type: {case_analysis.get('case_type', 'unknown').upper()}")
        print(f"Confidence: {case_analysis.get('confidence', 0):.2f}")
        print(f"Evidence: {', '.join(case_analysis.get('evidence', []))}")
        
        # Sentiment Analysis
        sentiment = result.get('sentiment', {})
        print(f"\nSentiment: {sentiment.get('label', 'neutral').upper()}")
        print(f"Score: {sentiment.get('score', 0):.2f}")
        print(f"Confidence: {sentiment.get('confidence', 0):.2f}")
        
        # Key Entities
        print("\nKey Entities:")
        legal_entities = result.get('legal_entities', {})
        for label, entities in legal_entities.items():
            if label in ['PERSON', 'ORG', 'MONEY', 'DATE', 'GPE']:
                print(f"- {label}: {', '.join(set(entities))}")
        
        # Money and Dates
        if result.get('money'):
            print(f"\nMonetary Amounts: {', '.join(set(result['money']))}")
        if result.get('dates'):
            print(f"Important Dates: {', '.join(set(result['dates']))}")

if __name__ == "__main__":
    test_analyzer()

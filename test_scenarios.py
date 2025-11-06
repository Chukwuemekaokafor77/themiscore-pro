"""
Test script for Law Firm Intake System
Tests all four scenarios with sample data
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
AUTH = ('demo', 'themiscore123')

# Test scenarios
SCENARIOS = {
    "slip_and_fall": {
        "text": """I was shopping at Walmart last Tuesday around 3pm and I slipped on some water 
        near the produce section. Nobody put up a wet floor sign. I hurt my back and knee really 
        bad and went to the hospital. The floor was really wet and I didn't see any warning signs 
        anywhere. There were other customers around who saw me fall.""",
        "title": "Walmart Slip and Fall - Produce Section",
        "client": {
            "first_name": "John",
            "last_name": "Smith",
            "email": "john.smith@test.com",
            "phone": "555-1234",
            "address": "123 Main St, Anytown, ST 12345"
        },
        "expected": {
            "category": "Personal Injury - Premises Liability",
            "priority": "High",
            "min_actions": 8,
            "min_documents": 4,
            "min_deadlines": 3
        }
    },
    "car_accident": {
        "text": """I was driving on Highway 95 yesterday morning around 8am during rush hour. 
        A red pickup truck ran a red light and hit the driver's side of my Honda Civic. 
        My neck hurts and my car is totaled. The other driver's insurance is StateFarm. 
        The police came and took a report. I went to the emergency room after the accident.""",
        "title": "Highway 95 Car Accident - Red Light Violation",
        "client": {
            "first_name": "Sarah",
            "last_name": "Johnson",
            "email": "sarah.johnson@test.com",
            "phone": "555-5678",
            "address": "456 Oak Ave, Anytown, ST 12345"
        },
        "expected": {
            "category": "Car Accident",
            "priority": "High",
            "min_actions": 7,
            "min_documents": 3,
            "min_deadlines": 4
        }
    },
    "employment_discrimination": {
        "text": """I've been working at TechCorp for 5 years as a software engineer. My new manager 
        started 6 months ago and ever since, he makes comments about my age - I'm 58. Last month 
        he gave me a bad performance review even though my work hasn't changed. Yesterday he told 
        me I should consider retiring. I think I'm being pushed out because of my age. I have 
        emails where he mentions my age and suggests I'm too old for the job.""",
        "title": "TechCorp Age Discrimination Case",
        "client": {
            "first_name": "Robert",
            "last_name": "Williams",
            "email": "robert.williams@test.com",
            "phone": "555-9876",
            "address": "789 Pine Rd, Anytown, ST 12345"
        },
        "expected": {
            "category": "Employment Law",
            "priority": "Medium-High",
            "min_actions": 6,
            "min_documents": 2,
            "min_deadlines": 3
        }
    },
    "medical_malpractice": {
        "text": """Three months ago I had surgery at City Hospital to remove my gallbladder. 
        The surgeon was Dr. Roberts. After the surgery I kept having pain and fever. I went back 
        twice and they said it was normal. Finally, I went to a different hospital last week and 
        they found the surgeon left a surgical sponge inside me. I had to have another surgery 
        to remove it. I was in so much pain for months and missed work.""",
        "title": "City Hospital Medical Malpractice - Retained Sponge",
        "client": {
            "first_name": "Maria",
            "last_name": "Garcia",
            "email": "maria.garcia@test.com",
            "phone": "555-4321",
            "address": "321 Elm St, Anytown, ST 12345"
        },
        "expected": {
            "category": "Medical Malpractice",
            "priority": "High",
            "min_actions": 8,
            "min_documents": 3,
            "min_deadlines": 5
        }
    }
}


def test_scenario(scenario_name, scenario_data):
    """Test a single scenario"""
    print(f"\n{'='*80}")
    print(f"Testing Scenario: {scenario_name.upper().replace('_', ' ')}")
    print(f"{'='*80}")
    
    # Prepare request
    payload = {
        "text": scenario_data["text"],
        "title": scenario_data["title"],
        "client": scenario_data["client"]
    }
    
    print(f"\n📝 Case Title: {scenario_data['title']}")
    print(f"👤 Client: {scenario_data['client']['first_name']} {scenario_data['client']['last_name']}")
    print(f"\n📄 Intake Text Preview:")
    print(f"   {scenario_data['text'][:150]}...")
    
    # Make request
    print(f"\n🚀 Sending request to {BASE_URL}/api/intake/auto...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/intake/auto",
            json=payload,
            auth=AUTH,
            timeout=30
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"\n✅ SUCCESS! Case created.")
            
            # Display results
            print(f"\n📊 Results:")
            print(f"   Case ID: {result['case_id']}")
            print(f"   Status: {result['status']}")
            
            analysis = result.get('analysis', {})
            print(f"\n🔍 AI Analysis:")
            print(f"   Category: {analysis.get('category', 'N/A')}")
            print(f"   Department: {analysis.get('department', 'N/A')}")
            print(f"   Priority: {analysis.get('priority', 'N/A')}")
            print(f"   Urgency: {analysis.get('urgency', 'N/A')}")
            
            # Key facts
            key_facts = analysis.get('key_facts', {})
            if key_facts:
                print(f"\n📋 Key Facts Extracted:")
                for key, value in key_facts.items():
                    if value:
                        print(f"   - {key.replace('_', ' ').title()}: {value}")
            
            # Actions
            actions_created = result.get('actions_created', [])
            print(f"\n✓ Actions Created: {len(actions_created)}")
            suggested_actions = analysis.get('suggested_actions', [])
            if suggested_actions:
                print(f"   Top Actions:")
                for i, action in enumerate(suggested_actions[:5], 1):
                    print(f"   {i}. {action}")
            
            # Documents
            documents_created = result.get('documents_created', [])
            print(f"\n📄 Documents Generated: {len(documents_created)}")
            
            # Deadlines (we need to query the case to get these)
            print(f"\n⏰ Deadlines: Created (check case page for details)")
            
            # Checklists
            checklists = analysis.get('checklists', {})
            if checklists:
                print(f"\n📝 Checklists Generated:")
                for checklist_name, items in checklists.items():
                    print(f"   {checklist_name.replace('_', ' ').title()}:")
                    for item in items[:3]:
                        print(f"     - {item}")
                    if len(items) > 3:
                        print(f"     ... and {len(items) - 3} more")
            
            # Validation
            expected = scenario_data['expected']
            print(f"\n✓ Validation:")
            
            # Check category
            if expected['category'] in analysis.get('category', ''):
                print(f"   ✅ Category matches: {analysis.get('category')}")
            else:
                print(f"   ❌ Category mismatch: Expected '{expected['category']}', got '{analysis.get('category')}'")
            
            # Check priority
            if expected['priority'].lower() in analysis.get('priority', '').lower():
                print(f"   ✅ Priority matches: {analysis.get('priority')}")
            else:
                print(f"   ⚠️  Priority: Expected '{expected['priority']}', got '{analysis.get('priority')}'")
            
            # Check counts
            if len(actions_created) >= expected['min_actions']:
                print(f"   ✅ Actions: {len(actions_created)} >= {expected['min_actions']} (minimum)")
            else:
                print(f"   ❌ Actions: {len(actions_created)} < {expected['min_actions']} (expected minimum)")
            
            if len(documents_created) >= expected['min_documents']:
                print(f"   ✅ Documents: {len(documents_created)} >= {expected['min_documents']} (minimum)")
            else:
                print(f"   ❌ Documents: {len(documents_created)} < {expected['min_documents']} (expected minimum)")
            
            print(f"\n🔗 View case at: {BASE_URL}/cases/{result['case_id']}")
            
            return True
            
        else:
            print(f"\n❌ FAILED! Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"\nMake sure the application is running at {BASE_URL}")
        return False


def run_all_tests():
    """Run all scenario tests"""
    print("\n" + "="*80)
    print("LAW FIRM INTAKE SYSTEM - SCENARIO TESTS")
    print("="*80)
    print(f"\nTesting against: {BASE_URL}")
    print(f"Authentication: {AUTH[0]} / {'*' * len(AUTH[1])}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    for scenario_name, scenario_data in SCENARIOS.items():
        success = test_scenario(scenario_name, scenario_data)
        results[scenario_name] = success
        
        # Wait between tests
        if scenario_name != list(SCENARIOS.keys())[-1]:
            print(f"\n⏳ Waiting 2 seconds before next test...")
            time.sleep(2)
    
    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for scenario_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {scenario_name.replace('_', ' ').title()}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
    
    return passed == total


if __name__ == "__main__":
    print("\n" + "🚀 Starting Law Firm Intake System Tests...")
    
    # Check if server is running
    try:
        response = requests.get(BASE_URL, auth=AUTH, timeout=5)
        print(f"✅ Server is running at {BASE_URL}")
    except requests.exceptions.RequestException:
        print(f"❌ ERROR: Cannot connect to {BASE_URL}")
        print(f"\nPlease start the application first:")
        print(f"   python app.py")
        exit(1)
    
    # Run tests
    success = run_all_tests()
    
    # Exit code
    exit(0 if success else 1)

# AI-Powered Features Documentation

## 1. AI Case Analysis

### Features
- **Text Analysis**: Extract entities, key phrases, and sentiment from case documents
- **Case Classification**: Automatically categorize cases based on content
- **Urgency Detection**: Identify urgent cases based on keywords and dates
- **Entity Recognition**: Extract people, organizations, locations, and legal terms

### How to Use

#### Analyze Text
```python
from ai_services import case_analyzer

# Analyze text
analysis = case_analyzer.analyze_text("""
    John Doe is suing ABC Corp for wrongful termination on March 15, 2023.
    He claims $50,000 in damages.
""")

print(analysis)
```

#### Extract Case Details
```python
case_details = case_analyzer.extract_case_details("""
    Our client was wrongfully terminated after reporting safety violations.
    The incident occurred on January 10, 2023, at their workplace in New York.
    We're seeking $100,000 in damages.
""")

print(case_details)
```

## 2. Document Management

### Features
- Secure file storage with case-based organization
- Document versioning
- Metadata tracking
- File type validation

### How to Use

#### Upload a Document
```python
from document_service import document_service

with open('legal_doc.pdf', 'rb') as f:
    metadata = document_service.save_document(
        file_stream=f,
        filename='legal_doc.pdf',
        case_id=123,
        user_id=1,
        metadata={
            'description': 'Initial complaint',
            'tags': ['complaint', 'urgent']
        }
    )
```

#### List Documents for a Case
```python
documents = document_service.list_case_documents(case_id=123)
for doc in documents:
    print(f"{doc['original_filename']} - {doc['file_size']} bytes")
```

## Setup Instructions

1. Install dependencies:
   ```
   python install_deps.py
   ```

2. Run the application:
   ```
   python app.py
   ```

3. Access the web interface at `http://localhost:5000`

## API Endpoints

### Analyze Document
```
POST /documents/<int:document_id>/analyze
```

### Upload Document
```
POST /documents/upload
```

## Troubleshooting

### SpaCy Model Not Found
If you see an error about the SpaCy model, run:
```
python -m spacy download en_core_web_sm
```

### File Upload Issues
- Ensure the uploads directory has write permissions
- Check file size limits in your Flask configuration
- Verify the file type is allowed (configured in `app.py`)

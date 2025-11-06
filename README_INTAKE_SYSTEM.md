# Law Firm Client Intake System - Complete Documentation

## Overview

This is a comprehensive AI-powered client intake system for law firms that automates the entire intake process from voice recording to case creation with automated document generation, deadline tracking, and smart routing.

## System Architecture

### Part 1: Voice to Text Converter
**What it does:** Records the client speaking and converts it into written text.

**Technology Stack:**
- **AssemblyAI API** - Primary speech-to-text service with advanced features
- **Browser MediaRecorder API** - For capturing audio from client's microphone
- **WebM/WAV Audio Format** - Supported audio formats

**Features:**
- Real-time audio recording with visual feedback
- Maximum recording time: 15 minutes (auto-save if exceeded)
- Automatic transcription with:
  - Speaker identification
  - Sentiment analysis
  - Entity detection
  - Auto-highlights
  - IAB category classification

**How it works:**
1. User clicks "Start Recording" button
2. Browser requests microphone permission
3. Audio is captured and stored temporarily
4. On stop, audio file is uploaded to server
5. Server sends audio to AssemblyAI for transcription
6. Transcription ID is returned and stored in database
7. Client polls for transcription status
8. When complete, text is displayed and stored

### Part 2: AI Text Analyzer
**What it does:** Reads the transcribed text and identifies the type of legal case.

**Supported Case Types:**
1. **Personal Injury - Premises Liability** (Slip and Fall)
2. **Car Accident / Auto Collision**
3. **Employment Law - Age Discrimination**
4. **Medical Malpractice**

**Analysis Features:**
- **Category Detection** - Identifies case type with high accuracy
- **Urgency Assessment** - Determines priority level (High/Medium/Low)
- **Key Facts Extraction** - Pulls out critical information
- **Date/Time Extraction** - Identifies incident dates and times
- **Entity Recognition** - Extracts names, locations, amounts, phone numbers
- **Suggested Actions** - Generates case-specific action items
- **Checklist Generation** - Creates scenario-specific checklists

### Part 3: Smart Routing System
**What it does:** Routes cases to appropriate departments and creates automated action items.

**Routing Logic:**
- Personal Injury → Personal Injury Department (High Priority)
- Car Accident → Auto Accident Department (High Priority)
- Employment Law → Employment Law Department (Medium-High Priority)
- Medical Malpractice → Medical Malpractice Department (High/Urgent Priority)

## Detailed Scenario Workflows

### Scenario 1: Slip and Fall at Walmart

**Trigger Keywords:** walmart, slip/slipped, water/wet floor/produce

**Automated Actions Created:**
1. ✅ Send evidence preservation letter to Walmart (within 1 hour)
2. ✅ Request staff list and cleaning logs
3. ✅ Request security footage (2-hour window)
4. ✅ Obtain medical records with HIPAA release
5. ✅ Collect client details questionnaire

**Documents Auto-Generated:**
- `preservation_walmart_[DATE].txt` - Evidence preservation letter
- `staff_request_[DATE].txt` - Staff information request
- `medical_checklist_[DATE].txt` - Medical records checklist
- `timeline_[DATE].txt` - Case timeline with deadlines

**Deadlines Automatically Created:**
- Security Footage Retention (60 days from incident)
- Medical Records Collection (14 days)
- Statute of Limitations (2 years from incident)

**Evidence Preservation Letter Includes:**
- Security camera footage (produce, entrance, registers)
- Incident reports
- Employee schedules and staff list
- Maintenance and cleaning logs
- Customer complaints
- Training records

**Medical Records Checklist:**
- Emergency room records
- Imaging (X-rays, CT, MRI)
- Doctor's notes and diagnosis
- Prescription records
- Physical therapy records
- Follow-up appointment notes

**Client Information to Collect:**
- What shoes were you wearing?
- Did you take photos?
- Did you report to store employee?
- Did you fill out incident report?
- Were there witnesses?
- What did the floor look like?
- How long was the hazard there?

### Scenario 2: Car Accident

**Trigger Keywords:** accident/collision/crash, highway/road/intersection

**Automated Actions Created:**
1. ✅ Request police accident report
2. ✅ Request DOT traffic/red-light camera footage
3. ✅ Send letters of representation to insurers
4. ✅ Collect vehicle details and damage photos
5. ✅ Schedule medical evaluation (within 48 hours)

**Documents Auto-Generated:**
- `police_report_request_[DATE].txt` - Police report request
- `dot_camera_request_[DATE].txt` - DOT camera footage request
- `letter_of_representation_[DATE].txt` - Letter to insurance companies

**Deadlines Automatically Created:**
- Police Report Request (7 days)
- Traffic Camera Footage (30 days)
- Medical Evaluation (2 days)
- Statute of Limitations (2 years from accident)

**Police Report Request Includes:**
- Traffic collision report
- Dash cam footage from police vehicles
- 911 call recordings
- Witness statements
- Traffic camera footage
- Citations issued

**Vehicle Information Needed:**
- Client's vehicle: Make, model, year, VIN
- Damage photos (all angles)
- Repair estimates
- Pre-accident valuation (KBB)
- Other driver's vehicle details
- License plate, insurance info

**Medical Documentation:**
- ER visit records
- Ambulance report
- Neck X-rays or CT scans
- Doctor's diagnosis
- Track all future appointments

### Scenario 3: Employment Law - Age Discrimination

**Trigger Keywords:** discrimination/harassment/pushed out, age/older/retire

**Automated Actions Created:**
1. ✅ Send litigation hold to employer (HR & Legal)
2. ✅ Collect employment details and documentation
3. ✅ Request complete personnel file
4. ✅ Prepare EEOC charge (with deadline tracking)
5. ✅ Comparator analysis questionnaire

**Documents Auto-Generated:**
- `employment_lit_hold_[DATE].txt` - Litigation hold letter
- `eeoc_preparation_[DATE].txt` - EEOC filing preparation guide

**Deadlines Automatically Created:**
- EEOC Filing Deadline (180 days federal, 300 days in deferral states) **CRITICAL**
- Send Litigation Hold Letter (7 days)
- Personnel File Request (14 days)

**Litigation Hold Letter Includes:**
- All emails to/from client
- All emails mentioning client
- Text messages on company devices
- Slack/Teams messages
- Performance reviews (last 5 years)
- Disciplinary actions
- Meeting notes mentioning client
- Video/audio recordings
- Policies and procedures

**Information to Collect:**
- Exact job title and salary
- Manager's full name
- HR representative contact
- Dates of specific incidents
- Emails/texts showing discrimination
- Performance reviews (current and previous)
- Names of similarly-situated employees
- Comparator treatment analysis

**EEOC Preparation Guide Includes:**
- Personal information required
- Employer information
- Employment details
- Discrimination specifics
- Adverse actions taken
- Comparator information
- Documentation to gather

### Scenario 4: Medical Malpractice

**Trigger Keywords:** sponge/retained foreign/left inside, surgery/surgeon

**Automated Actions Created:**
1. ✅ Immediate medical records request (both hospitals)
2. ✅ Litigation hold to hospital (Risk & Legal)
3. ✅ Identify full surgical team
4. ✅ Retain expert witness for merit review
5. ✅ Calculate statute of limitations deadlines

**Documents Auto-Generated:**
- `medical_records_request_[DATE].txt` - Medical records authorization
- `hospital_lit_hold_[DATE].txt` - Hospital litigation hold
- `expert_witness_checklist_[DATE].txt` - Expert witness requirements

**Deadlines Automatically Created:**
- Medical Records Request (7 days) **URGENT**
- Retain Medical Expert Witness (30 days)
- Certificate of Merit (60 days)
- Statute of Limitations (2 years from surgery)
- Discovery Rule Deadline (1 year from discovery)

**Medical Records Request Includes:**

**From Original Hospital:**
- Complete surgical records
- Pre-operative records
- Operative report (surgeon's notes)
- Anesthesia records
- Surgical count sheets (CRITICAL)
- Operating room logs
- Post-operative care records
- All imaging and lab results

**From Second Hospital:**
- Admission/ER records
- Sponge removal surgery report
- Imaging proving retained sponge
- Pathology report

**Litigation Hold Includes:**
- Complete medical chart
- Surgical count sheets
- OR logs and scheduling
- Equipment logs
- Personnel records for surgical team
- Credentialing files
- Incident reports
- Peer review documents
- Policies for surgical counts
- Video/audio recordings from OR

**Expert Witness Requirements:**
- Board certified in same specialty
- Currently practicing or recently retired
- Familiar with standard of care
- Strong credentials
- Available for deposition and trial

**Certificate of Merit:**
- Many states require expert certification before filing
- Must certify case has merit
- Usually required within 60-90 days of filing
- Failure to file may result in dismissal

## API Endpoints

### Voice to Text

#### Upload Audio for Transcription
```
POST /transcribe
Content-Type: multipart/form-data

Parameters:
- audio_file: Audio file (WebM, WAV, MP3)

Response:
{
  "status": "processing",
  "transcript_id": "abc123"
}
```

#### Check Transcription Status
```
GET /transcribe/status/<transcript_id>

Response (Processing):
{
  "status": "processing",
  "id": "abc123"
}

Response (Completed):
{
  "status": "completed",
  "id": "abc123",
  "text": "Transcribed text here...",
  "entities": [...],
  "sentiment_analysis": [...],
  "auto_highlights": [...],
  "iab_categories": [...]
}
```

### Automated Intake

#### Create Case with AI Analysis
```
POST /api/intake/auto
Content-Type: application/json

Body:
{
  "text": "Client intake text from transcription",
  "title": "Case Title",
  "client": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "555-1234",
    "address": "123 Main St"
  }
}

Response:
{
  "status": "success",
  "case_id": 123,
  "actions_created": [1, 2, 3, 4, 5],
  "documents_created": [10, 11, 12],
  "email_drafts_created": [20, 21],
  "analysis": {
    "category": "Personal Injury - Premises Liability",
    "urgency": "High",
    "department": "Personal Injury",
    "priority": "High",
    "key_facts": {...},
    "dates": [...],
    "suggested_actions": [...],
    "checklists": {...}
  }
}
```

## Database Models

### Core Models

**User** - Staff, attorneys, admins
- Authentication and authorization
- Role-based access control

**Client** - Client information
- Contact details
- Multiple cases per client

**Case** - Legal case
- Title, description, type
- Status, priority
- Assigned attorney
- AI category classification

**Action** - Task/action item
- Title, description, type
- Status, priority, due date
- Assigned user
- Many-to-many with cases

**Document** - File storage
- Name, path, type, size
- Associated with case
- Uploaded by user

**Transcript** - Voice transcriptions
- External ID (AssemblyAI)
- Status, text
- Associated with case/client

**Deadline** - Critical deadlines
- Name, due date, source
- Notes and reminders
- Associated with case

**EmailDraft** - Draft emails
- To, subject, body
- Attachments
- Status (draft/sent)

**AIInsight** - AI analysis results
- Category, confidence
- Insight text
- Metadata (entities, risk level)

## Environment Configuration

Create a `.env` file with:

```env
# Database
DATABASE_URL=sqlite:///legalintake.db

# Security
SECRET_KEY=your-secret-key-here

# AssemblyAI API
ASSEMBLYAI_API_KEY=your-assemblyai-api-key

# Law Firm Details
LAW_FIRM_NAME=Your Law Firm Name
LAW_FIRM_CONTACT=123 Main St | (555) 123-4567 | info@lawfirm.com

# Evidence Retention
EVIDENCE_RETENTION_DAYS=60

# File Upload
MAX_CONTENT_LENGTH=16777216
```

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation Steps

1. **Clone or navigate to project directory**
```bash
cd C:\Users\emekamichael\CascadeProjects\law_firm_intake
```

2. **Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
Create `.env` file with required configuration (see above)

5. **Initialize database**
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

6. **Run the application**
```bash
python app.py
```

7. **Access the application**
Open browser to: `http://localhost:5000`

**Default Login:**
- Username: `demo`
- Password: `themiscore123`

**Admin Account:**
- Email: `admin@lawfirm.com`
- Password: `admin123`

## Usage Workflow

### Complete Intake Process

1. **Navigate to Voice to Text page** (`/transcribe`)

2. **Record Client Intake**
   - Click "Start Recording" button
   - Allow microphone access
   - Client describes their situation
   - Click "Stop Recording" when done

3. **Wait for Transcription**
   - System uploads audio to AssemblyAI
   - Transcription processes (usually 30-60 seconds)
   - Text appears when complete

4. **Review Transcription**
   - Read through transcribed text
   - Edit if necessary
   - Review detected entities and sentiment

5. **Create Case Automatically**
   - Click "Create Case from Transcript"
   - System analyzes text and identifies case type
   - Enter client details if not already in system
   - Click "Submit"

6. **System Automatically Creates:**
   - ✅ New case with proper categorization
   - ✅ Client record (if new)
   - ✅ 5-10 action items specific to case type
   - ✅ 3-4 document templates (letters, checklists)
   - ✅ 3-6 critical deadlines with reminders
   - ✅ Email drafts for review
   - ✅ AI insights and analysis

7. **Review Generated Materials**
   - Navigate to case page
   - Review all actions
   - Download generated letters
   - Check deadlines
   - Assign tasks to team members

8. **Send Letters**
   - Review auto-generated letters
   - Customize as needed
   - Send to appropriate parties
   - Mark actions as complete

## Letter Templates

All letter templates are comprehensive and include:

### Evidence Preservation Letters
- Formal notice of litigation hold
- Specific evidence to preserve
- Legal consequences of spoliation
- Confirmation requirements

### Medical Records Requests
- HIPAA authorization language
- Specific records needed
- Rush request notation
- Contact information

### Timeline Documents
- Incident details
- Medical treatment dates
- Critical deadlines
- Next steps

### EEOC Preparation Guides
- Required information
- Deadline calculations
- Documentation checklists
- Filing instructions

### Expert Witness Checklists
- Qualification requirements
- Documents for review
- Report requirements
- Cost considerations

## Deadline Management

The system automatically calculates and tracks:

### Personal Injury Deadlines
- Security footage retention (60 days)
- Medical records collection (14 days)
- Statute of limitations (2 years)

### Car Accident Deadlines
- Police report request (7 days)
- Traffic camera footage (30 days)
- Medical evaluation (2 days)
- Statute of limitations (2 years)

### Employment Law Deadlines
- EEOC filing (180/300 days) **CRITICAL**
- Litigation hold letter (7 days)
- Personnel file request (14 days)

### Medical Malpractice Deadlines
- Medical records request (7 days) **URGENT**
- Expert witness retention (30 days)
- Certificate of Merit (60 days)
- Statute of limitations (2 years)
- Discovery rule deadline (1 year)

## Features Summary

✅ **Voice to Text** - AssemblyAI integration with advanced features
✅ **AI Case Analysis** - Scenario-based detection for 4 case types
✅ **Smart Routing** - Automatic department assignment
✅ **Action Generation** - 5-10 case-specific tasks created automatically
✅ **Document Generation** - 3-4 comprehensive letter templates per case
✅ **Deadline Tracking** - 3-6 critical deadlines with reminders
✅ **Email Drafts** - Review before sending
✅ **Client Management** - Automatic client creation/matching
✅ **Case Management** - Full case lifecycle tracking
✅ **User Management** - Role-based access control
✅ **Document Storage** - Secure file management
✅ **AI Insights** - Entity extraction, sentiment analysis

## Security Features

- Basic authentication for all routes
- Session management with expiration
- Password hashing (Werkzeug)
- Role-based access control
- Secure file uploads
- CSRF protection (Flask)
- SQL injection prevention (SQLAlchemy ORM)

## Troubleshooting

### AssemblyAI API Issues
- Verify API key in `.env` file
- Check API quota/limits
- Ensure audio file is valid format

### Database Issues
- Run `flask db upgrade` to apply migrations
- Check database file permissions
- Verify DATABASE_URL in `.env`

### File Upload Issues
- Check MAX_CONTENT_LENGTH setting
- Verify uploads directory exists and is writable
- Ensure file extension is allowed

### Transcription Not Processing
- Check AssemblyAI API status
- Verify audio file was uploaded successfully
- Check application logs for errors

## Future Enhancements

- [ ] Email integration (SendGrid/SMTP)
- [ ] SMS notifications for deadlines
- [ ] Calendar integration (Google Calendar, Outlook)
- [ ] Document e-signature (DocuSign)
- [ ] Client portal for document access
- [ ] Advanced analytics and reporting
- [ ] Multi-language support
- [ ] Mobile app
- [ ] Integration with practice management systems

## Support

For issues or questions:
1. Check this documentation
2. Review application logs
3. Check AssemblyAI API status
4. Verify environment configuration

## License

Proprietary - Law Firm Internal Use Only

---

**System Version:** 1.0.0  
**Last Updated:** November 2024  
**Developed for:** Law Firm Client Intake Automation

# Quick Start Guide - Law Firm Intake System

## Test the System in 5 Minutes

### Step 1: Start the Application

```bash
cd C:\Users\emekamichael\CascadeProjects\law_firm_intake
python app.py
```

The application will start on `http://localhost:5000`

### Step 2: Login

**Basic Auth Prompt:**
- Username: `demo`
- Password: `themiscore123`

**Then login to the app:**
- Email: `admin@lawfirm.com`
- Password: `admin123`

### Step 3: Test Each Scenario

Navigate to the Voice to Text page: `/transcribe`

#### Test Scenario 1: Slip and Fall (Walmart)

**Sample Text to Use:**
```
I was shopping at Walmart last Tuesday around 3pm and I slipped on some water near the produce section. Nobody put up a wet floor sign. I hurt my back and knee really bad and went to the hospital. My name is John Smith and my phone number is 555-1234.
```

**Expected Results:**
- ✅ Case Type: Personal Injury - Premises Liability
- ✅ Priority: High
- ✅ Department: Personal Injury
- ✅ 8-10 Actions Created
- ✅ 4 Documents Generated:
  - Evidence preservation letter to Walmart
  - Staff information request
  - Medical records checklist
  - Timeline document
- ✅ 3 Deadlines Created:
  - Security footage retention (60 days)
  - Medical records collection (14 days)
  - Statute of limitations (2 years)

#### Test Scenario 2: Car Accident

**Sample Text to Use:**
```
I was driving on Highway 95 yesterday morning around 8am during rush hour. A red pickup truck ran a red light and hit the driver's side of my Honda Civic. My neck hurts and my car is totaled. The other driver's insurance is StateFarm. My name is Sarah Johnson, email sarah@email.com.
```

**Expected Results:**
- ✅ Case Type: Car Accident / Auto Collision
- ✅ Priority: High
- ✅ Department: Auto Accident
- ✅ 7-9 Actions Created
- ✅ 3 Documents Generated:
  - Police report request
  - DOT camera footage request
  - Letter of representation to insurers
- ✅ 4 Deadlines Created:
  - Police report request (7 days)
  - Traffic camera footage (30 days)
  - Medical evaluation (2 days)
  - Statute of limitations (2 years)

#### Test Scenario 3: Employment Discrimination

**Sample Text to Use:**
```
I've been working at TechCorp for 5 years as a software engineer. My new manager started 6 months ago and ever since, he makes comments about my age - I'm 58. Last month he gave me a bad performance review even though my work hasn't changed. Yesterday he told me I should consider retiring. I think I'm being pushed out because of my age. My name is Robert Williams, phone 555-9876.
```

**Expected Results:**
- ✅ Case Type: Employment Law - Age Discrimination
- ✅ Priority: Medium-High
- ✅ Department: Employment Law
- ✅ 6-8 Actions Created
- ✅ 2 Documents Generated:
  - Employment litigation hold letter
  - EEOC preparation guide
- ✅ 3 Deadlines Created:
  - EEOC filing deadline (180 days) **CRITICAL**
  - Litigation hold letter (7 days)
  - Personnel file request (14 days)

#### Test Scenario 4: Medical Malpractice

**Sample Text to Use:**
```
Three months ago I had surgery at City Hospital to remove my gallbladder. The surgeon was Dr. Roberts. After the surgery I kept having pain and fever. I went back twice and they said it was normal. Finally, I went to a different hospital last week and they found the surgeon left a surgical sponge inside me. I had to have another surgery to remove it. I was in so much pain for months and missed work. My name is Maria Garcia, email maria@email.com, phone 555-4321.
```

**Expected Results:**
- ✅ Case Type: Medical Malpractice
- ✅ Priority: High/Urgent
- ✅ Department: Medical Malpractice
- ✅ 8-10 Actions Created
- ✅ 3 Documents Generated:
  - Medical records request (both hospitals)
  - Hospital litigation hold letter
  - Expert witness checklist
- ✅ 5 Deadlines Created:
  - Medical records request (7 days) **URGENT**
  - Expert witness retention (30 days)
  - Certificate of Merit (60 days)
  - Statute of limitations (2 years)
  - Discovery rule deadline (1 year)

### Step 4: Review Generated Materials

After creating a case, navigate to:

1. **Case Details Page** - `/cases/<case_id>`
   - View all case information
   - See assigned actions
   - Check deadlines

2. **Documents** - Click "Documents" tab
   - Download generated letters
   - Review checklists
   - View timeline

3. **Actions** - Click "Actions" tab
   - See all automated tasks
   - Assign to team members
   - Mark as complete

4. **Deadlines** - View deadline section
   - See all critical dates
   - Get reminders
   - Track compliance

### Step 5: Test API Directly (Optional)

#### Test Auto-Intake API

```bash
curl -X POST http://localhost:5000/api/intake/auto \
  -H "Content-Type: application/json" \
  -u demo:themiscore123 \
  -d '{
    "text": "I was shopping at Walmart last Tuesday around 3pm and I slipped on some water near the produce section. Nobody put up a wet floor sign. I hurt my back and knee really bad and went to the hospital.",
    "title": "Walmart Slip and Fall",
    "client": {
      "first_name": "John",
      "last_name": "Smith",
      "email": "john@test.com",
      "phone": "555-1234"
    }
  }'
```

**Expected Response:**
```json
{
  "status": "success",
  "case_id": 1,
  "actions_created": [1, 2, 3, 4, 5, 6, 7, 8],
  "documents_created": [1, 2, 3, 4],
  "email_drafts_created": [1, 2, 3, 4],
  "analysis": {
    "category": "Personal Injury - Premises Liability",
    "urgency": "High",
    "department": "Personal Injury",
    "priority": "High",
    "key_facts": {
      "store": "Walmart",
      "hazard": "Wet floor/water",
      "injuries": "Back/knee",
      "medical_visit": "Yes",
      "warning_sign": "No"
    },
    "dates": ["last Tuesday", "3pm"],
    "suggested_actions": [
      "Send evidence preservation letter to Walmart within 1 hour",
      "Request staff list and cleaning logs for incident day",
      "Request security footage (produce, entrance, registers) 2h window",
      "Obtain medical records and generate HIPAA release",
      "Collect client details (shoes, photos, witnesses, incident report)"
    ],
    "checklists": {
      "medical_records": [
        "ER records",
        "Imaging",
        "Doctor notes",
        "Prescriptions",
        "PT records",
        "Follow-ups"
      ],
      "client_questions": [
        "Shoes worn",
        "Photos taken",
        "Reported to employee",
        "Incident report filed",
        "Witnesses info",
        "Nature/duration of spill"
      ]
    }
  }
}
```

## Verification Checklist

After testing, verify:

- [ ] Case was created successfully
- [ ] Client record was created/matched
- [ ] Correct case type was identified
- [ ] Appropriate priority was assigned
- [ ] All actions were created (5-10 depending on scenario)
- [ ] All documents were generated (3-4 per scenario)
- [ ] All deadlines were created (3-6 per scenario)
- [ ] Email drafts were created
- [ ] AI insights were saved
- [ ] Case is assigned to correct department

## Common Issues & Solutions

### Issue: "AssemblyAI API Key not set"
**Solution:** Add `ASSEMBLYAI_API_KEY=your_key_here` to `.env` file

### Issue: "Database not found"
**Solution:** Run `flask db upgrade` to create database

### Issue: "Permission denied on uploads folder"
**Solution:** Ensure uploads directory exists and is writable

### Issue: "No actions created"
**Solution:** Check that text matches scenario keywords (see README)

### Issue: "Documents not generated"
**Solution:** Verify uploads folder exists and has write permissions

## Next Steps

1. **Customize Letter Templates**
   - Edit `services/letter_templates.py`
   - Update firm name and contact info in `.env`

2. **Adjust Deadlines**
   - Modify deadline calculations in `app.py`
   - Update `EVIDENCE_RETENTION_DAYS` in `.env`

3. **Add More Scenarios**
   - Edit `utils.py` - `analyze_intake_text_scenarios()`
   - Add new letter templates in `services/letter_templates.py`
   - Update deadline logic in `app.py`

4. **Configure Email Sending**
   - Add SMTP settings to `.env`
   - Implement email sending in email draft routes

5. **Customize UI**
   - Edit templates in `templates/` directory
   - Modify styles in `static/css/`

## Performance Tips

- AssemblyAI transcription typically takes 30-60 seconds
- Longer audio files take proportionally longer
- Database queries are optimized with eager loading
- File uploads are limited to 16MB by default

## Support

If you encounter issues:
1. Check application logs in console
2. Verify `.env` configuration
3. Review `README_INTAKE_SYSTEM.md` for detailed documentation
4. Check AssemblyAI API status

---

**Ready to go!** Start with Scenario 1 (Slip and Fall) to see the full automation in action.

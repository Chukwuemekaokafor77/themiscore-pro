"""
Letter Template Generation Service
Generates automated letters for different case scenarios
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

LAW_FIRM_NAME = os.getenv('LAW_FIRM_NAME', 'Your Law Firm Name')
LAW_FIRM_CONTACT = os.getenv('LAW_FIRM_CONTACT', 'Address | Phone | Email')
EVIDENCE_RETENTION_DAYS = int(os.getenv('EVIDENCE_RETENTION_DAYS', 60))


class LetterTemplateService:
    """Service for generating legal letter templates"""
    
    @staticmethod
    def _format_letter(header, body):
        """Format a letter with header, body, and firm signature"""
        return f"{header}\n\n{body}\n\n{LAW_FIRM_NAME}\n{LAW_FIRM_CONTACT}\n"
    
    # ==================== SLIP AND FALL TEMPLATES ====================
    
    @staticmethod
    def slip_fall_preservation_letter(client_name, incident_date, incident_time, location='Walmart', address='[ADDRESS]'):
        """Generate evidence preservation letter for slip and fall case"""
        header = f"To: {location} Legal Department / Store Manager\nSubject: Evidence Preservation Notice - Incident on {incident_date}"
        body = f"""Dear Sir/Madam,

Our client, {client_name}, was injured at your store location at {address} on {incident_date} at approximately {incident_time}.

This letter serves as formal notice to preserve all evidence including:

- Security camera footage from {incident_date} between 2 hours before and after {incident_time}
- All footage showing the produce section and surrounding areas
- All footage showing entrance, exit, and cash register areas
- Incident reports filed on {incident_date}
- Employee shift schedules and complete staff list on duty during {incident_time}
- Maintenance and cleaning logs for {incident_date}
- Any customer complaints about wet floors or hazards on {incident_date}
- Training records for employees on duty
- Store policies regarding floor maintenance and hazard warnings
- Any internal communications regarding the incident

Failure to preserve this evidence may result in legal sanctions including spoliation of evidence claims.

Please confirm receipt of this notice within 48 hours and provide a written confirmation that all evidence has been preserved.

This is a formal litigation hold. Do not destroy, delete, or alter any of the above-mentioned evidence."""
        
        return LetterTemplateService._format_letter(header, body)
    
    @staticmethod
    def slip_fall_staff_request(client_name, incident_date, incident_time):
        """Generate staff information request letter"""
        header = f"Subject: Staff Information Request - Incident on {incident_date}"
        body = f"""Dear Sir/Madam,

Regarding the incident involving our client {client_name} on {incident_date} at approximately {incident_time}, we request the following information:

1. Complete list of all employees working on {incident_date} during the hours of {incident_time}
2. Names and contact information for:
   - Manager on duty
   - Assistant managers on duty
   - Maintenance/cleaning staff on duty
   - Security personnel on duty
   - Any employees who witnessed or responded to the incident

3. Employee responsibilities:
   - Who was responsible for cleaning/mopping the area where the incident occurred
   - Who was responsible for floor inspections during that shift
   - Who was responsible for placing warning signs

4. Incident response:
   - Names of employees who assisted our client
   - Names of employees who completed any incident reports
   - Names of employees who may have witnessed the hazardous condition before the incident

Please provide this information within 7 business days."""
        
        return LetterTemplateService._format_letter(header, body)
    
    @staticmethod
    def slip_fall_medical_checklist(client_name):
        """Generate medical records checklist"""
        header = f"Subject: Medical Records Checklist - {client_name}"
        body = f"""Medical Records Required for {client_name}:

EMERGENCY ROOM RECORDS:
- Emergency room admission records from incident date
- Triage notes and vital signs
- Physician examination notes
- Nursing notes and observations
- Emergency department discharge summary

IMAGING AND DIAGNOSTIC TESTS:
- X-rays (all views and angles)
- CT scans or MRI reports
- Ultrasound reports (if applicable)
- Radiology interpretation reports

TREATMENT RECORDS:
- Doctor's notes and diagnosis
- Treatment plans and recommendations
- Prescription records (all medications prescribed)
- Pain management records
- Injection or procedure notes

FOLLOW-UP CARE:
- All follow-up appointment notes
- Physical therapy records and progress notes
- Occupational therapy records (if applicable)
- Specialist consultation reports
- Orthopedic or pain management specialist notes

ONGOING CARE:
- Current treatment plans
- Prognosis and long-term care recommendations
- Work restrictions or disability assessments
- Future medical needs assessments

BILLING RECORDS:
- All medical bills and invoices
- Insurance claims and explanations of benefits (EOB)
- Out-of-pocket expenses documentation

Please ensure all records are complete and include dates of service."""
        
        return LetterTemplateService._format_letter(header, body)
    
    @staticmethod
    def slip_fall_timeline(client_name, incident_date, incident_time, analysis_summary=''):
        """Generate timeline document for slip and fall case"""
        now_str = datetime.utcnow().strftime('%Y-%m-%d')
        # Calculate statute of limitations (typically 2-3 years, using 2 years as default)
        try:
            incident_dt = datetime.strptime(incident_date, '%Y-%m-%d')
            statute_deadline = incident_dt + timedelta(days=730)  # 2 years
            statute_str = statute_deadline.strftime('%Y-%m-%d')
        except:
            statute_str = '[CALCULATE BASED ON STATE LAW]'
        
        lines = [
            f"CASE TIMELINE - {client_name}",
            "=" * 60,
            f"Generated: {now_str}",
            "",
            "INCIDENT DETAILS:",
            f"  Incident Date: {incident_date}",
            f"  Incident Time: {incident_time}",
            f"  Location: [STORE ADDRESS]",
            "",
            "MEDICAL TREATMENT:",
            "  Initial Hospital Visit: [DATE/TIME]",
            "  Follow-up Appointments: [DATES]",
            "  Physical Therapy Started: [DATE]",
            "  Current Treatment Status: [ONGOING/COMPLETED]",
            "",
            "CRITICAL DEADLINES:",
            f"  Evidence Preservation Deadline: {now_str} (IMMEDIATE)",
            f"  Security Footage Retention: Typically 30-90 days (URGENT)",
            f"  Statute of Limitations: {statute_str}",
            "  Demand Letter: [TO BE DETERMINED]",
            "  Filing Deadline: [TO BE DETERMINED]",
            "",
            "CASE NOTES:",
            analysis_summary or 'N/A',
            "",
            "NEXT STEPS:",
            "  1. Send evidence preservation letter (IMMEDIATE)",
            "  2. Obtain security footage (within 7 days)",
            "  3. Collect medical records (within 14 days)",
            "  4. Interview witnesses (within 30 days)",
            "  5. Retain expert witnesses if needed (within 60 days)",
        ]
        return "\n".join(lines)
    
    # ==================== CAR ACCIDENT TEMPLATES ====================
    
    @staticmethod
    def car_accident_police_report_request(client_name, accident_date, location):
        """Generate police report request letter"""
        header = f"Subject: Request for Accident Report - {accident_date} at {location}"
        body = f"""Dear [Police Department],

We represent {client_name} who was involved in a traffic collision on {accident_date} at approximately [TIME] at {location}.

We respectfully request a copy of the traffic collision report for this incident.

Additionally, please preserve the following evidence:
- All dash cam footage from police vehicles in the area during the time of the accident
- 911 call recordings related to this incident
- Any witness statements collected at the scene
- Traffic camera footage from nearby intersections
- Any citations issued related to this accident
- Body camera footage from responding officers

Report Details (if known):
- Report Number: [NUMBER]
- Responding Officer(s): [NAME(S)]
- Our Client: {client_name}

Please send the report and confirmation of evidence preservation to:
Email: [EMAIL]
Fax: [FAX]
Mail: {LAW_FIRM_CONTACT}

If there are any fees associated with obtaining this report, please contact us at the above information."""
        
        return LetterTemplateService._format_letter(header, body)
    
    @staticmethod
    def car_accident_dot_camera_request(accident_date, location):
        """Generate DOT traffic camera footage request"""
        header = f"Subject: Traffic Camera Footage Request - {accident_date}"
        body = f"""To: Department of Transportation

We are investigating a traffic collision that occurred on {accident_date} at {location}.

We request all traffic camera and red-light camera footage from the following:

LOCATION DETAILS:
- Intersection/Location: {location}
- Date: {accident_date}
- Time Window: 30 minutes before and after [INCIDENT TIME]

SPECIFIC REQUESTS:
- All traffic cameras at or near the intersection
- Red-light camera footage (if equipped)
- Any speed enforcement camera footage
- Highway surveillance cameras in the vicinity

CAMERA ANGLES NEEDED:
- All available angles showing the intersection
- Cameras showing approach lanes
- Cameras showing traffic signal status
- Any cameras showing the vehicles involved

Please preserve this footage immediately as it may be automatically deleted after a retention period.

We understand there may be fees associated with this request. Please contact us with the total cost and payment instructions."""
        
        return LetterTemplateService._format_letter(header, body)
    
    @staticmethod
    def car_accident_letter_of_representation(client_name, insurance_company):
        """Generate letter of representation to insurance companies"""
        header = f"Subject: Letter of Representation - {client_name}"
        body = f"""To: {insurance_company}

Please be advised that our firm has been retained to represent {client_name} in connection with a motor vehicle accident that occurred on [DATE].

IMPORTANT NOTICE:
All future communication regarding this matter must be directed to our office. Do not contact our client directly.

Our client is represented by counsel and all settlement negotiations, requests for information, and other communications must go through this firm.

PRESERVATION OF EVIDENCE:
You are hereby directed to preserve all documents, electronic records, and physical evidence related to this claim, including but not limited to:
- All claim files and notes
- All photographs and videos
- All recorded statements
- All correspondence
- All damage estimates and repair records
- All medical records and bills
- All communications with your insured
- All communications with witnesses
- All internal evaluations and assessments

CLAIM INFORMATION:
- Our Client: {client_name}
- Date of Loss: [DATE]
- Claim Number: [IF KNOWN]
- Policy Number: [IF KNOWN]

Please direct all future correspondence to:
{LAW_FIRM_NAME}
{LAW_FIRM_CONTACT}

We will be in contact regarding this matter shortly."""
        
        return LetterTemplateService._format_letter(header, body)
    
    # ==================== EMPLOYMENT LAW TEMPLATES ====================
    
    @staticmethod
    def employment_litigation_hold(client_name, employer_name):
        """Generate employment litigation hold letter"""
        header = "Subject: Evidence Preservation Notice - Employment Matter"
        body = f"""To: {employer_name} Human Resources Department
To: {employer_name} Legal Department

Our client, {client_name}, has retained our firm regarding potential employment-related claims.

LITIGATION HOLD - IMMEDIATE ACTION REQUIRED

You must immediately preserve all documents and electronic records, including but not limited to:

ELECTRONIC COMMUNICATIONS:
- All emails to/from {client_name} from [DATE] to present
- All emails mentioning {client_name} between management, HR, and other employees
- All text messages on company devices
- All Slack, Microsoft Teams, or other internal messaging platform communications
- All voicemail messages

PERSONNEL RECORDS:
- Complete personnel file for {client_name}
- All performance reviews for {client_name} (last 5 years minimum)
- All performance reviews for similarly-situated employees
- All disciplinary actions or warnings
- All promotions, raises, and bonus records
- All job descriptions for {client_name}'s positions
- All training records

EMPLOYMENT DECISIONS:
- Any complaints filed by or about {client_name}
- Any internal investigations involving {client_name}
- Meeting notes or minutes mentioning {client_name}
- Any discussions about termination, retirement, or position elimination
- Any discussions about performance improvement plans
- Any discussions about restructuring affecting {client_name}'s position

WORKPLACE RECORDS:
- Video/audio recordings from security cameras in workplace
- Building access logs
- Time and attendance records
- Payroll records

POLICIES AND PROCEDURES:
- All employee handbooks in effect during {client_name}'s employment
- All anti-discrimination and anti-harassment policies
- All complaint procedures

This is a formal litigation hold pursuant to your legal obligations. Failure to preserve evidence may result in:
- Sanctions from the court
- Adverse inference instructions to a jury
- Monetary penalties
- Other legal consequences

Please confirm receipt of this notice within 48 hours and provide written confirmation that all evidence has been preserved and that a litigation hold has been implemented."""
        
        return LetterTemplateService._format_letter(header, body)
    
    @staticmethod
    def employment_eeoc_preparation_guide(client_name, employer_name):
        """Generate EEOC filing preparation guide"""
        header = f"Subject: EEOC Charge Preparation - {client_name}"
        body = f"""EEOC CHARGE OF DISCRIMINATION - PREPARATION GUIDE

Client: {client_name}
Employer: {employer_name}

CRITICAL DEADLINES:
- Federal Deadline: 180 days from last discriminatory act
- State Deadline: 300 days (in deferral states)
- MUST FILE BEFORE DEADLINE OR LOSE RIGHT TO SUE

INFORMATION NEEDED FOR EEOC CHARGE:

PERSONAL INFORMATION:
- Full legal name
- Current address and phone number
- Email address
- Date of birth
- Race/ethnicity (if applicable to claim)
- Gender (if applicable to claim)
- Religion (if applicable to claim)
- Disability status (if applicable to claim)

EMPLOYER INFORMATION:
- Complete legal name of employer
- Employer address
- Number of employees
- Type of business
- Supervisor/manager names

EMPLOYMENT DETAILS:
- Dates of employment (start and end if terminated)
- Job title(s)
- Department
- Salary/wage information
- Employment status (full-time, part-time, etc.)

DISCRIMINATION DETAILS:
- Type of discrimination (age, race, gender, disability, etc.)
- Dates of discriminatory acts (be specific)
- Names of individuals who discriminated
- Specific examples of discrimination
- Witnesses to discrimination
- How you were treated differently than others

ADVERSE ACTIONS:
- Termination (date and circumstances)
- Demotion (date and details)
- Denial of promotion (date and details)
- Reduction in pay or hours
- Hostile work environment details
- Retaliation for complaints

COMPARATOR INFORMATION:
- Names of similarly-situated employees treated differently
- Their protected class status
- How they were treated better
- Evidence of disparate treatment

DOCUMENTATION TO GATHER:
- Employment contract or offer letter
- All performance reviews
- All emails related to discrimination
- Text messages or other communications
- Witness contact information
- Any complaints you filed internally
- Company's response to your complaints
- Any relevant company policies

NEXT STEPS:
1. Schedule in-person meeting to complete EEOC intake questionnaire
2. Gather all documentation listed above
3. Prepare detailed timeline of events
4. Identify all witnesses
5. Draft charge of discrimination
6. File with EEOC before deadline
7. Obtain right-to-sue letter (after EEOC investigation or 180 days)"""
        
        return LetterTemplateService._format_letter(header, body)
    
    # ==================== MEDICAL MALPRACTICE TEMPLATES ====================
    
    @staticmethod
    def medical_malpractice_records_request(client_name, hospital_name, procedure_date):
        """Generate medical records request with HIPAA authorization"""
        header = "Subject: Authorization to Release Medical Records - URGENT"
        body = f"""To: {hospital_name} Medical Records Department

Our client, {client_name}, authorizes the release of ALL medical records related to treatment at your facility.

PATIENT INFORMATION:
- Patient Name: {client_name}
- Date of Birth: [DOB]
- Medical Record Number: [IF KNOWN]

RECORDS REQUESTED FROM {hospital_name}:

SURGICAL RECORDS (Procedure Date: {procedure_date}):
- Complete surgical records
- Pre-operative records and assessments
- Operative report (surgeon's detailed notes)
- Anesthesia records
- Surgical count sheets (sponge and instrument counts)
- Operating room logs
- Post-anesthesia care unit (PACU) records

POST-OPERATIVE CARE:
- All post-operative nursing notes
- All physician progress notes
- All follow-up visit records
- All telephone communications with patient
- All patient complaints or concerns documented

DIAGNOSTIC IMAGING:
- All X-rays (with radiologist interpretations)
- All CT scans (with radiologist interpretations)
- All ultrasounds (with radiologist interpretations)
- All MRI scans (with radiologist interpretations)
- All other imaging studies

LABORATORY RESULTS:
- All pre-operative lab work
- All post-operative lab work
- All pathology reports
- All blood work results

EMERGENCY ROOM RECORDS (if applicable):
- ER admission records
- Triage notes
- Physician and nursing notes
- Discharge instructions

ADDITIONAL RECORDS:
- All consultation reports
- All medication administration records
- All vital signs flow sheets
- All incident reports (if any)
- All quality assurance reviews (if any)
- Copies of all consent forms signed

RUSH REQUEST - LEGAL MATTER
This is a legal matter requiring immediate attention. Please provide these records within 7 business days.

Please send records to:
{LAW_FIRM_NAME}
{LAW_FIRM_CONTACT}

Enclosed: Signed HIPAA Authorization Form

If there are any fees associated with copying these records, please contact us at the above information."""
        
        return LetterTemplateService._format_letter(header, body)
    
    @staticmethod
    def medical_malpractice_hospital_litigation_hold(client_name, hospital_name, procedure_date, surgeon_name):
        """Generate hospital litigation hold letter"""
        header = "LITIGATION HOLD - Evidence Preservation Required"
        body = f"""To: {hospital_name} Risk Management Department
To: {hospital_name} Legal Department

URGENT - LITIGATION HOLD NOTICE

Our client, {client_name}, experienced a serious surgical complication at your facility on {procedure_date}.

You must immediately preserve ALL records and materials related to this matter.

PATIENT INFORMATION:
- Patient: {client_name}
- Procedure Date: {procedure_date}
- Surgeon: {surgeon_name}
- Procedure: [PROCEDURE TYPE]

EVIDENCE TO BE PRESERVED:

MEDICAL RECORDS:
- Complete medical chart for {client_name}
- All versions of medical records (including any amendments or corrections)
- All electronic health record entries with audit trails

SURGICAL DOCUMENTATION:
- Surgical count sheets (sponge, instrument, and needle counts)
- Operating room logs for {procedure_date}
- OR scheduling records
- Equipment logs and maintenance records
- Sterilization records for instruments used

PERSONNEL RECORDS:
- Names and contact information for all surgical team members present
- Credentialing files for {surgeon_name}
- Credentialing files for all surgical team members
- Training records for surgical count procedures
- Performance reviews for surgical team members
- Any disciplinary records related to surgical team members

INCIDENT DOCUMENTATION:
- Any incident reports filed related to this case
- Any unusual occurrence reports
- Any peer review documents or discussions
- Any quality assurance reviews
- Any risk management assessments
- Any internal communications about this incident

POLICIES AND PROCEDURES:
- All policies and procedures for surgical counts in effect on {procedure_date}
- All policies for retained foreign objects
- All policies for incident reporting
- Training materials for surgical count procedures

VIDEO/AUDIO RECORDINGS:
- All video recordings from operating room cameras
- All audio recordings from the OR
- All security camera footage showing OR area

COMMUNICATIONS:
- All internal emails, memos, or communications about this case
- All communications with patient or patient's family
- All communications with insurance carriers
- All communications with legal counsel

DO NOT DESTROY, ALTER, OR DELETE ANY RECORDS

This is a formal litigation hold. Failure to preserve evidence may result in:
- Sanctions from the court
- Adverse inference instructions
- Monetary penalties
- Criminal charges for obstruction of justice

Please confirm receipt of this notice within 24 hours and provide written confirmation that:
1. A litigation hold has been implemented
2. All relevant personnel have been notified
3. All automatic deletion processes have been suspended
4. All evidence has been secured

Time is of the essence. Some evidence may be subject to automatic deletion or destruction if not immediately preserved."""
        
        return LetterTemplateService._format_letter(header, body)
    
    @staticmethod
    def medical_malpractice_expert_witness_checklist(client_name, procedure_type):
        """Generate expert witness requirements checklist"""
        header = f"Subject: Medical Expert Witness Requirements - {client_name}"
        body = f"""MEDICAL EXPERT WITNESS CHECKLIST

Case: {client_name}
Procedure: {procedure_type}

EXPERT WITNESS REQUIREMENTS:

QUALIFICATIONS NEEDED:
- Board certified in same specialty as defendant physician
- Currently practicing or recently retired (within 5 years)
- Familiar with standard of care for {procedure_type}
- Licensed in same or similar jurisdiction
- No history of malpractice claims or disciplinary actions
- Strong credentials and reputation

EXPERT'S ROLE:
- Review all medical records
- Provide opinion on standard of care
- Identify deviations from standard of care
- Establish causation between breach and injury
- Assess damages and future medical needs
- Provide written report
- Available for deposition
- Available for trial testimony

DOCUMENTS FOR EXPERT REVIEW:

MEDICAL RECORDS:
- All records from treating facility
- All records from subsequent treatment
- All imaging studies (actual images, not just reports)
- All pathology slides and reports
- All laboratory results

CASE MATERIALS:
- Chronology of events
- Summary of allegations
- Relevant medical literature
- Applicable standards of care
- Hospital policies and procedures

EXPERT REPORT MUST ADDRESS:
1. Expert's qualifications and experience
2. Standard of care for {procedure_type}
3. How defendant deviated from standard of care
4. Specific acts of negligence
5. How negligence caused patient's injuries
6. Extent of injuries and damages
7. Future medical needs and prognosis
8. Economic damages calculation
9. Basis for opinions (medical literature, guidelines, etc.)

TIMELINE:
- Retain expert: Within 30 days
- Provide records to expert: Within 45 days
- Expert preliminary opinion: Within 60 days
- Certificate of Merit (if required): Within 60-90 days of filing
- Expert report: Per court deadlines
- Expert deposition: Per court schedule
- Trial preparation: 30 days before trial

CERTIFICATE OF MERIT REQUIREMENTS:
Many states require a Certificate of Merit before filing medical malpractice lawsuit:
- Expert must review case
- Expert must certify case has merit
- Must be filed within 60-90 days of complaint
- Failure to file may result in dismissal

COST CONSIDERATIONS:
- Initial case review: $[AMOUNT]
- Written report: $[AMOUNT]
- Deposition: $[AMOUNT] per hour
- Trial testimony: $[AMOUNT] per day
- Travel expenses
- Record review time

NEXT STEPS:
1. Identify potential expert witnesses
2. Send case summary and key records for preliminary review
3. Obtain expert's preliminary opinion
4. Retain expert if opinion is favorable
5. Provide complete records to expert
6. Obtain written report
7. File Certificate of Merit (if required)
8. Prepare expert for deposition
9. Prepare expert for trial"""
        
        return LetterTemplateService._format_letter(header, body)
    
    # ==================== UTILITY METHODS ====================
    
    @staticmethod
    def generate_all_letters_for_scenario(scenario_type, **kwargs):
        """
        Generate all relevant letters for a given scenario
        
        Args:
            scenario_type: 'slip_fall', 'car_accident', 'employment', 'medical_malpractice'
            **kwargs: Scenario-specific parameters
            
        Returns:
            List of tuples: [(filename, content), ...]
        """
        letters = []
        now_str = datetime.utcnow().strftime('%Y-%m-%d')
        
        if scenario_type == 'slip_fall':
            client_name = kwargs.get('client_name', '[CLIENT NAME]')
            incident_date = kwargs.get('incident_date', now_str)
            incident_time = kwargs.get('incident_time', '[TIME]')
            
            letters.append((
                f"preservation_walmart_{now_str}.txt",
                LetterTemplateService.slip_fall_preservation_letter(
                    client_name, incident_date, incident_time
                )
            ))
            letters.append((
                f"staff_request_{now_str}.txt",
                LetterTemplateService.slip_fall_staff_request(
                    client_name, incident_date, incident_time
                )
            ))
            letters.append((
                f"medical_checklist_{now_str}.txt",
                LetterTemplateService.slip_fall_medical_checklist(client_name)
            ))
            letters.append((
                f"timeline_{now_str}.txt",
                LetterTemplateService.slip_fall_timeline(
                    client_name, incident_date, incident_time,
                    kwargs.get('analysis_summary', '')
                )
            ))
            
        elif scenario_type == 'car_accident':
            client_name = kwargs.get('client_name', '[CLIENT NAME]')
            accident_date = kwargs.get('accident_date', now_str)
            location = kwargs.get('location', '[LOCATION]')
            insurance = kwargs.get('insurance_company', '[INSURANCE COMPANY]')
            
            letters.append((
                f"police_report_request_{now_str}.txt",
                LetterTemplateService.car_accident_police_report_request(
                    client_name, accident_date, location
                )
            ))
            letters.append((
                f"dot_camera_request_{now_str}.txt",
                LetterTemplateService.car_accident_dot_camera_request(
                    accident_date, location
                )
            ))
            letters.append((
                f"letter_of_representation_{now_str}.txt",
                LetterTemplateService.car_accident_letter_of_representation(
                    client_name, insurance
                )
            ))
            
        elif scenario_type == 'employment':
            client_name = kwargs.get('client_name', '[CLIENT NAME]')
            employer_name = kwargs.get('employer_name', '[EMPLOYER NAME]')
            
            letters.append((
                f"employment_lit_hold_{now_str}.txt",
                LetterTemplateService.employment_litigation_hold(
                    client_name, employer_name
                )
            ))
            letters.append((
                f"eeoc_preparation_{now_str}.txt",
                LetterTemplateService.employment_eeoc_preparation_guide(
                    client_name, employer_name
                )
            ))
            
        elif scenario_type == 'medical_malpractice':
            client_name = kwargs.get('client_name', '[CLIENT NAME]')
            hospital_name = kwargs.get('hospital_name', '[HOSPITAL NAME]')
            procedure_date = kwargs.get('procedure_date', now_str)
            surgeon_name = kwargs.get('surgeon_name', '[SURGEON NAME]')
            procedure_type = kwargs.get('procedure_type', '[PROCEDURE TYPE]')
            
            letters.append((
                f"medical_records_request_{now_str}.txt",
                LetterTemplateService.medical_malpractice_records_request(
                    client_name, hospital_name, procedure_date
                )
            ))
            letters.append((
                f"hospital_lit_hold_{now_str}.txt",
                LetterTemplateService.medical_malpractice_hospital_litigation_hold(
                    client_name, hospital_name, procedure_date, surgeon_name
                )
            ))
            letters.append((
                f"expert_witness_checklist_{now_str}.txt",
                LetterTemplateService.medical_malpractice_expert_witness_checklist(
                    client_name, procedure_type
                )
            ))
        
        return letters

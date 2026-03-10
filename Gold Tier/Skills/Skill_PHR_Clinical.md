# ⚕️ PHR-012: Clinical Decision Support Skill

> **Extension of SK-012 for Personal Health Record Clinical Support**

## 📋 **Skill Identity**

- **Skill ID**: PHR-012
- **Name**: PHR Clinical Decision Support
- **Type**: Clinical Decision Support Skill (Extension of SK-012)
- **Agent**: PHR-AGENT-003
- **Version**: 1.0
- **Constitutional Authority**: Company_Handbook.md + PHR_Compliance_Protocol.md

---

## 🎯 **Skill Purpose**

The PHR-012 skill provides clinical decision support within appropriate boundaries while maintaining clear separation from medical practice. This skill focuses on clinical data analysis, pattern recognition, safety flagging, and decision support while ensuring all operations remain within healthcare safety boundaries.

---

## 🔄 **Execution Steps (7-Step Protocol)**

### **Step 1: Clinical Data Reception and Validation** (PHR-012.1)
- **INPUT**: De-identified clinical data from privacy agent
- **PROCESS**: Receive and validate clinical data format and quality
- **OUTPUT**: Validated clinical data ready for analysis
- **VALIDATION**: Ensure data is de-identified and clinically relevant
- **BOUNDARY**: Verify within appropriate clinical support scope

### **Step 2: Clinical Pattern Recognition** (PHR-012.2)
- **INPUT**: Validated clinical data
- **PROCESS**: Identify clinical patterns and trends
- **OUTPUT**: Pattern recognition report with confidence levels
- **VALIDATION**: Cross-reference patterns with clinical knowledge
- **BOUNDARY**: Focus on support, not diagnosis

### **Step 3: Clinical Safety Flagging** (PHR-012.3)
- **INPUT**: Clinical data and identified patterns
- **PROCESS**: Flag potential clinical safety concerns
- **OUTPUT**: Safety flag report with severity and action recommendations
- **VALIDATION**: Verify flags against clinical safety standards
- **BOUNDARY**: Flag for human review, do not make decisions

### **Step 4: Clinical Information Validation** (PHR-012.4)
- **INPUT**: Clinical information requiring verification
- **PROCESS**: Cross-reference with trusted clinical knowledge bases
- **OUTPUT**: Validated information with source attribution
- **VALIDATION**: Confirm accuracy from credible sources
- **BOUNDARY**: Provide information, not medical advice

### **Step 5: Clinical Decision Support Generation** (PHR-012.5)
- **INPUT**: Validated clinical information and safety flags
- **PROCESS**: Generate decision support with clear limitations
- **OUTPUT**: Decision support information with appropriate disclaimers
- **VALIDATION**: Ensure support is non-binding and appropriately limited
- **BOUNDARY**: Maintain clear boundary between support and practice

### **Step 6: Clinical Information Integration** (PHR-012.6)
- **INPUT**: Clinical decision support output
- **PROCESS**: Integrate with care plans and health records
- **OUTPUT**: Integrated clinical information with context
- **VALIDATION**: Preserve clinical data integrity
- **BOUNDARY**: Maintain appropriate clinical support level

### **Step 7: Clinical Reporting and Documentation** (PHR-012.7)
- **INPUT**: Processed clinical information
- **PROCESS**: Generate clinical reports with appropriate disclaimers
- **OUTPUT**: Clinical reports for appropriate consumption
- **VALIDATION**: Ensure all reports include proper limitations
- **BOUNDARY**: Document scope limitations clearly

---

## 🏥 **Clinical Domain Expertise**

### **Vital Signs Analysis**
- **BLOOD PRESSURE**: Hypertension/hypotension recognition
  - Normal: <120/80 mmHg
  - Elevated: 120-129/<80 mmHg
  - Hypertension Stage 1: 130-139/80-89 mmHg
  - Hypertension Stage 2: ≥140/90 mmHg
  - Hypertensive Crisis: ≥180/120 mmHg (flag immediately)

- **HEART RATE**: Bradycardia/tachycardia identification
  - Normal: 60-100 bpm
  - Bradycardia: <60 bpm (in adults)
  - Tachycardia: >100 bpm (in adults)

- **TEMPERATURE**: Fever/hypothermia detection
  - Normal: 97.7-99.5°F (36.5-37.5°C)
  - Fever: >100.4°F (38°C)
  - Hypothermia: <95°F (35°C)

- **OXYGEN SATURATION**: Hypoxia identification
  - Normal: ≥95%
  - Concerning: 90-94%
  - Critical: <90%

- **RESPIRATION**: Abnormal breathing pattern recognition
  - Normal: 12-20 breaths per minute
  - Bradypnea: <12 breaths per minute
  - Tachypnea: >20 breaths per minute

### **Medication Management Support**
- **INTERACTION CHECKING**: Potential drug-drug interactions
- **ALLERGY CROSS-REFERENCE**: Medication allergy compatibility
- **DOSING GUIDELINES**: Age and condition-appropriate dosing
- **ADHERENCE TRACKING**: Medication schedule compliance monitoring
- **THERAPEUTIC DUPLICATION**: Identification of duplicate therapies

### **Condition Monitoring**
- **CHRONIC DISEASES**: Diabetes, hypertension, heart disease tracking
- **ACUTE CONDITIONS**: Symptom pattern recognition
- **COMORBIDITY ANALYSIS**: Condition interaction assessment
- **DISEASE PROGRESSION**: Trend identification for chronic conditions
- **COMPLICATION RISK**: Potential complication risk assessment

### **Care Plan Support**
- **GOAL TRACKING**: Treatment goal progress monitoring
- **INTERVENTION SUGGESTIONS**: Evidence-based intervention suggestions
- **OUTCOME PROJECTIONS**: Expected outcome trend projections
- **FOLLOW-UP SCHEDULING**: Appropriate follow-up timing recommendations
- **ADHERENCE MONITORING**: Care plan adherence tracking

---

## ⚠️ **Clinical Boundary Management**

### **PERMITTED Operations** (Appropriate Support Scope)
- ✅ Clinical data aggregation and trend analysis
- ✅ Pattern recognition and anomaly detection
- ✅ Safety flagging for potential clinical concerns
- ✅ Evidence-based information provision
- ✅ Decision support with clear disclaimers
- ✅ Care plan organization and tracking
- ✅ Medication schedule support
- ✅ Wellness goal tracking

### **PROHIBITED Operations** (Require Human Clinical Judgment)
- ❌ Medical diagnosis or diagnostic interpretation
- ❌ Treatment recommendations or prescriptions
- ❌ Medical advice or therapeutic guidance
- ❌ Clinical decision making without human oversight
- ❌ Emergency medical instructions
- ❌ Medication dose changes
- ❌ Clinical procedure recommendations
- ❌ Interpretation of diagnostic tests

---

## 🧠 **Clinical Knowledge Integration**

### **Medical Terminology Standards**
- **SNOMED CT**: Clinical terminology and concept representation
- **LOINC**: Laboratory and clinical observation identifiers
- **ICD-10**: Diagnostic coding standards
- **RxNorm**: Clinical drug information standard
- **UMLS**: Unified Medical Language System integration

### **Clinical Guidelines Integration**
- **EVIDENCE-BASED**: Integration with evidence-based clinical guidelines
- **REGULAR UPDATES**: Maintained current with latest guidelines
- **TRUSTED SOURCES**: Use only authoritative medical sources
- **CONTEXTUAL APPLICATION**: Appropriate application based on patient context

### **Safety Standards**
- **FDA GUIDELINES**: Software as Medical Device considerations
- **CLINICAL DECISION SUPPORT**: Evidence-based support standards
- **PATIENT SAFETY**: Safety protocol integration
- **QUALITY MEASURES**: Clinical quality indicator tracking

---

## 🚨 **Clinical Safety Protocols**

### **Safety Flag Categories**
- **CRITICAL SAFETY FLAGS** (Immediate human review required):
  - Vital signs in critical ranges
  - Potential drug interactions requiring immediate attention
  - Signs of acute clinical deterioration
  - Potential medical emergencies

- **HIGH RISK FLAGS** (Urgent review needed):
  - Abnormal lab values requiring attention
  - Medication concerns
  - Disease progression indicators
  - Potential adverse events

- **MODERATE RISK FLAGS** (Standard review):
  - Trend changes requiring follow-up
  - Care plan adjustments needed
  - Wellness concerns
  - Monitoring recommendations

- **MONITORING FLAGS** (Ongoing observation):
  - Subtle trend changes
  - Preventive care opportunities
  - Health maintenance needs
  - Educational opportunities

### **Emergency Recognition**
- **VITAL SIGN CRISIS**: Critical values requiring immediate attention
- **ADVERSE EVENT DETECTION**: Potential medication or treatment reactions
- **SYMPTOM CLUSTER RECOGNITION**: Combinations suggesting serious conditions
- **INTERACTION ALERTS**: Dangerous drug or treatment interactions

---

## 📊 **Clinical Quality Metrics**

### **Support Quality Indicators**
- **ACCURACY RATE**: Percentage of correct clinical information identification
- **SAFETY FLAG APPROPRIATENESS**: Percentage of safety flags requiring action
- **FALSE POSITIVE RATE**: Percentage of non-threatening situations flagged
- **CLINICAL UTILITY**: Value of information provided to care teams

### **Safety Metrics**
- **SAFETY INCIDENT IDENTIFICATION**: Clinical safety issues that weren't flagged
- **ESCALATION APPROPRIATENESS**: Percentage of boundary violations escalated
- **HUMAN REVIEW REQUIREMENT**: Percentage of operations requiring human oversight
- **POTENTIAL OUTCOME CORRELATION**: Relationship between support and outcomes

### **Performance Metrics**
- **RESPONSE TIME**: Time to provide clinical support
- **ACCURACY CONSISTENCY**: Consistency of clinical information accuracy
- **USER SATISFACTION**: Satisfaction with clinical support provided
- **CLINICAL WORKFLOW IMPACT**: Effect on clinical workflow efficiency

---

## 🔄 **Integration Points**

### **Input Sources**
- **PHR-AGENT-001**: Clinical data from ingestion agent
- **PHR-AGENT-002**: Privacy-cleared health data from privacy agent
- **PHR-AGENT-004**: Clinical data from integration agent
- **PHR-AGENT-005**: Clinical insights from analytics agent

### **Output Destinations**
- **PHR-AGENT-004**: Clinical information for EHR integration
- **PHR-AGENT-005**: Clinical insights for analytics
- **Care Teams**: Clinical decision support for healthcare providers
- **Patients**: Appropriate clinical information for patients

### **External Systems**
- **EHR Systems**: Electronic Health Record integration
- **Clinical Decision Support Systems**: Evidence-based guidelines
- **Laboratory Systems**: Lab result integration
- **Pharmacy Systems**: Medication information
- **Monitoring Devices**: Physiological data input
- **Clinical Guidelines**: Evidence-based protocol integration

---

## 🛡️ **Clinical Compliance**

### **Regulatory Standards**
- **FDA SOFTWARE AS MEDICAL DEVICE**: Guidelines for clinical CDS software
- **ONC HEALTH IT CERTIFICATION**: Health IT certification requirements
- **JOINT COMMISSION**: Healthcare organization standards
- **STATE MEDICAL BOARDS**: Telehealth and clinical support guidelines

### **Documentation Requirements**
- **CLINICAL DECISION LOG**: All clinical decisions and data points used
- **BOUNDARY VIOLATION LOG**: All instances requiring human escalation
- **SAFETY EVENT LOG**: All safety flags and outcomes
- **QUALITY ASSURANCE**: Regular clinical accuracy assessments

---

## 🚨 **Escalation Protocols**

### **Immediate Escalation Required**
- Potential life-threatening conditions identified
- Safety flags requiring urgent clinical attention
- Apparent clinical errors or contradictions
- Uncertainty about clinical information accuracy
- Situations outside appropriate support boundaries

### **Standard Escalation Process**
```
RECOGNITION → ASSESSMENT → DOCUMENTATION → ESCALATION → VERIFICATION → FOLLOW-UP
```

### **Clinical Review Requirements**
- **CRITICAL ISSUES**: Immediate physician review
- **HIGH RISK**: Prompt clinical review
- **MODERATE RISK**: Standard clinical review
- **MONITORING**: Scheduled clinical review

---

## 📋 **Quality Assurance**

### **Regular Validation**
- **CLINICAL ACCURACY**: Regular assessment of information accuracy
- **SAFETY PROTOCOL**: Validation of safety flagging effectiveness
- **BOUNDARY COMPLIANCE**: Verification of scope limitations adherence
- **USER FEEDBACK**: Incorporation of user experience feedback

---

<div align="center">

> **"Support clinical decision-making, never replace clinical judgment."**
> The boundary between assistance and medical practice is both critical and sacred.

</div>
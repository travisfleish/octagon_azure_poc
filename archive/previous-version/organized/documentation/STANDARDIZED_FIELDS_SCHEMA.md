# Standardized Fields Schema for SOW Analysis

## 🎯 **Purpose**
This document defines the standardized fields that AI extracts from heterogeneous SOW documents to create homogeneous, structured data.

## 📋 **Core Standardized Fields**

### **1. Basic Project Information**
- **`company`** (string, required)
  - The client company name
  - Example: "Company 2", "International Incorporated"
  
- **`project_title`** (string, required)
  - The project or campaign title
  - Example: "2025 Company 2 Global Olympics Platform Support"
  
- **`duration_weeks`** (integer, required)
  - Project duration in weeks
  - Example: 52, 35, 9

### **2. Organizational Structure**
- **`departments_involved`** (array of strings, required)
  - Octagon departments involved in the project
  - **MUST ONLY use these 4 standardized department names:**
    - `client_services` (for account management, client relationship, account services)
    - `strategy` (for strategic planning, insights, research, analytics)
    - `planning_creative` (for creative development, brand work, campaign planning, creative strategy)
    - `integrated_production_experiences` (for events, hospitality, activations, production, experiences)

### **3. Deliverables & Scope**
- **`deliverables`** (array of strings, required)
  - Specific deliverables or outputs from the project
  - Examples:
    - "Lead partnership planning cycle & support strategic program development"
    - "Act as project manager for integrated planning process"
    - "Manage day-to-day relationships with stakeholders"
    - "Develop partnership toolkits and regular share-outs"
    - "Build and maintain global asset tracker"

- **`scope_description`** (string, required)
  - Brief description of the project scope
  - Provides context for the overall project objectives

### **4. Staffing Information**
- **`roles_mentioned`** (array of strings, required)
  - Staffing roles mentioned in the SOW
  - Examples:
    - Project Manager
    - Global PMO (PMO team / lead)
    - Core onsite management team
    - Hospitality-specific workstream owner
    - Subject Matter Expert
    - Account Director
    - Strategy Director
    - Creative Director
    - Account Manager
    - Agency staff
    - Octagon personnel

### **5. Financial Information**
- **`budget_info`** (object, optional)
  - Budget and financial information
  - Sub-fields:
    - `total_budget` (number): Total project budget
    - `budget_currency` (string): Currency (e.g., "USD", "EUR")
    - `budget_breakdown` (array of strings): Budget line items

### **6. Quality & Metadata**
- **`confidence_score`** (number, 0.0-1.0)
  - AI confidence in the extraction accuracy
  - Example: 0.9 (high confidence), 0.7 (good confidence)
  
- **`file_name`** (string)
  - Original SOW file name
  - Example: "company_2_sow_1.pdf"
  
- **`extraction_timestamp`** (datetime)
  - When the extraction was performed
  - ISO format: "2025-09-20T10:02:01.823795"

## 📊 **Extraction Results Summary**

From the 9 SOW files analyzed:

| Field | Count | Examples |
|-------|-------|----------|
| **Companies** | 6 | Company 2, International Incorporated, Company 1, Company 3, Company 4 |
| **Departments** | 4 | client_services, strategy, planning_creative, integrated_production_experiences |
| **Deliverables** | 151 | Partnership planning, PMO management, stakeholder relationships, etc. |
| **Roles** | 63 | Project Manager, Account Director, Creative Director, etc. |
| **Duration Range** | 1-52 weeks | Average: 27.8 weeks, Median: 35 weeks |

## 🔄 **Data Flow**

```
Heterogeneous SOWs → AI Analysis → Standardized JSON → Structured Database
     (9 files)      (Azure OpenAI)    (This Schema)    (Ready for staffing plans)
```

## ✅ **Benefits of Standardization**

1. **Consistency**: All SOWs processed into identical field structure
2. **Queryability**: Standardized fields enable database queries and analysis
3. **Automation**: Consistent data enables automated staffing plan generation
4. **Reporting**: Standardized fields enable cross-project reporting
5. **Integration**: Structured data integrates with downstream systems

## 🎯 **Next Steps**

This standardized schema enables:
- **Staffing Plan Generation**: Using roles and departments to create staffing plans
- **Resource Allocation**: Using deliverables and duration to estimate resource needs
- **Budget Planning**: Using budget info and duration for financial planning
- **Department Coordination**: Using departments_involved for cross-team coordination
- **Timeline Management**: Using duration_weeks for project scheduling

The homogeneous extraction from heterogeneous sources is now complete and ready for downstream processing!

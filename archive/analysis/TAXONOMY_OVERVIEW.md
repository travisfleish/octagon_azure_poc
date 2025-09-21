# SOW Extraction Taxonomy Overview

## 🎯 **Purpose**
This taxonomy provides comprehensive keyword dictionaries and regex patterns for extracting structured data from SOW documents. It serves as a fallback and validation layer for LLM extraction.

## 📋 **Extracted Fields**

### 1. **Client Name**
- **Contract indicators**: "between", "agreement between", "services for"
- **Label indicators**: "client:", "company:", "customer:"
- **Signature indicators**: "authorized by", "on behalf of", "representing"
- **Exclusion patterns**: "octagon", "contractor", "vendor"
- **Corporate suffixes**: "inc.", "incorporated", "corp.", "llc", "ltd."

### 2. **Project Title**
- **Title indicators**: "project title:", "work title:", "engagement title:"
- **Section headers**: "project overview", "project description", "scope of work"
- **Exclusion patterns**: "confidential", "proprietary", "internal use"

### 3. **Start Date**
- **Primary indicators**: "start date", "service start date", "commencement date"
- **Context patterns**: "services start date:", "work begins:", "effective as of:"
- **Date formats**: Multiple regex patterns for various date formats
- **Example**: "September 1, 2025" from "Services Start Date: September 1, 2025"

### 4. **End Date**
- **Primary indicators**: "end date", "service end date", "completion date"
- **Context patterns**: "services end date:", "work ends:", "through:"
- **Duration indicators**: "through", "until", "ending", "concluding"
- **Date formats**: Same comprehensive patterns as start date
- **Example**: "January 31, 2026" from "Services End Date: January 31, 2026"

### 5. **Project Length**
- **Duration indicators**: "project length", "duration", "term", "timeline"
- **Time units**: "months", "weeks", "days", "years"
- **Duration patterns**: Regex for various duration formats
- **Approximate indicators**: "approximately", "about", "estimated"

### 6. **Scope Summary**
- **Section headers**: "scope of work", "project scope", "overview"
- **Introductory phrases**: "the purpose of this", "this project involves"
- **Exclusion patterns**: "confidential", "proprietary", "internal"

### 7. **Deliverables**
- **Section headers**: "deliverables", "work product", "outputs"
- **List indicators**: "•", "▪", "1.", "2.", "a.", "b."
- **Action verbs**: "provide", "deliver", "create", "develop"
- **Deliverable indicators**: "deliverable", "output", "report", "analysis"

### 8. **Exclusions**
- **Section headers**: "exclusions", "not included", "out of scope"
- **Exclusion indicators**: "excludes", "not include", "not covered"
- **List indicators**: Same as deliverables

### 9. **Staffing Plan**
- **Section headers**: "staffing plan", "personnel", "team", "resources"
- **Table indicators**: "title discipline hours", "name", "role", "allocation"
- **Role patterns**: Regex for "EVP", "SVP", "VP", "Director", "Manager"
- **Allocation patterns**: Regex for percentages, hours, FTE
- **Location indicators**: "US", "UK", "New York", "Los Angeles"

## 🔧 **Technical Features**

### **Compiled Regex Patterns**
- Pre-compiled patterns for efficient matching
- Case-insensitive matching
- Multiple format support

### **Field Priorities**
1. client_name (highest priority)
2. project_title
3. start_date
4. end_date
5. project_length
6. scope_summary
7. deliverables
8. exclusions
9. staffing_plan (lowest priority)

### **Confidence Thresholds**
- **High**: 0.8+ (use keyword result)
- **Medium**: 0.6-0.8 (compare with LLM)
- **Low**: 0.4-0.6 (use LLM result)
- **Very Low**: <0.4 (flag for review)

### **Validation Rules**
- **Date validation**: End date must be after start date
- **Staffing validation**: Require role and allocation, max 50 team members
- **Deliverables validation**: Minimum 1 deliverable, max 500 chars each

## 🚀 **Usage Example**

```python
from sow_extraction_taxonomy import SOWExtractionTaxonomy, get_field_keywords

# Get keywords for a specific field
client_keywords = get_field_keywords("client_name")
print(client_keywords["contract_indicators"])

# Get compiled patterns
patterns = SOWExtractionTaxonomy.get_compiled_patterns()
start_date_patterns = patterns["start_date_formats"]

# Check field priority
priority = SOWExtractionTaxonomy.FIELD_PRIORITIES["client_name"]
```

## 📊 **Statistics**
- **Total fields**: 9
- **Total keyword categories**: 45
- **Total regex patterns**: 28
- **Total validation rules**: 3 categories

## 🎯 **Next Steps**
1. Integrate with existing LLM extraction pipeline
2. Add confidence scoring algorithm
3. Implement validation and correction logic
4. Test with real SOW documents
5. Refine patterns based on extraction results

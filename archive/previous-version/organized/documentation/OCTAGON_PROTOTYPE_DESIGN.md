# Octagon Staffing Plan Generator Prototype - Design Document

## Executive Summary

This document outlines the design for Octagon's Staffing Plan Generator Prototype (Phase 1 - "Crawl"). The prototype demonstrates how AI can read heterogeneous SOW documents and normalize details into structured staffing plans using semantic intelligence and rules-based processing.

## Problem Statement

**Current Challenge**: Octagon manually builds staffing plans by interpreting client SOWs (Scope of Work documents). Every SOW is different — some specify % FTE, some hours, some rates, some use vague language. Converting this into a structured staffing plan requires significant time and institutional knowledge.

**Prototype Goal**: Show that AI can reliably extract and normalize SOW details into structured data that maps to staffing plans, handling the variability inherent in client documents.

## Solution Architecture

### Core Components

1. **Octagon-Specific Schema** (`octagon_staffing_schema.py`)
   - Maps to Octagon's organizational structure
   - Handles FTE % ↔ hours normalization
   - Tracks billability vs non-billable time
   - Maintains traceability between raw text and structured fields

2. **Enhanced Document Intelligence** (`octagon_document_intelligence.py`)
   - Processes mixed SOW formats (PDF, DOCX)
   - Uses Octagon-specific extraction patterns
   - Integrates heuristics with LLM processing
   - Provides fallback mechanisms for reliability

3. **Taxonomy-Based Processing**
   - Octagon service lines and departments
   - Role mapping and seniority classification
   - Allocation type normalization
   - Financial structure extraction

## Octagon Organizational Taxonomy

### Service Lines (10 Categories)
- **Creative**: Brand design, content creation, creative direction
- **Client Services**: Account management, client relations
- **Strategy**: Strategic planning, brand strategy, market research
- **Sponsorship**: Sponsorship activation, rights management
- **Experience**: Event management, hospitality, fan engagement
- **Business Development**: New business, partnerships
- **Analytics**: Measurement, ROI analysis, performance tracking
- **Production**: Content production, video, photography
- **Media**: Media planning, digital marketing, social media
- **Partnerships**: Partnership management, rights acquisition

### Departments (25+ Specific Roles)
- **Account Management**: Account Directors, Managers, Executives, Coordinators
- **Creative**: Creative Directors, Art Directors, Copywriters, Designers
- **Strategy**: Strategy Directors, Managers, Strategists, Planners
- **Sponsorship**: Sponsorship Directors, Managers, Partnership Managers
- **Experience**: Event Directors, Event Managers, Hospitality Managers
- **Analytics**: Analytics Directors, Data Analysts, Measurement Specialists
- **Business Development**: BD Directors, BD Managers, New Business Managers

### Seniority Levels
- **Junior**: AE, Coordinator, Specialist
- **Mid-Level**: Manager, SAE
- **Senior**: Senior Manager, Senior Director
- **Director**: Director, VP
- **Executive**: SVP, EVP, C-Level

## Schema Design Principles

### 1. **Flexibility for Variation**
```python
class AllocationType(str, Enum):
    FTE_PERCENTAGE = "fte_percentage"  # % of full-time equivalent
    HOURS = "hours"  # Specific hour allocations
    RATE_BASED = "rate_based"  # Hourly/daily rates
    RETAINER = "retainer"  # Fixed monthly retainer
    PROJECT_BASED = "project_based"  # Fixed project fee
```

### 2. **Normalization Capabilities**
```python
@computed_field
@property
def normalized_hours(self) -> Optional[float]:
    """Convert allocation to normalized hours (assuming 40hr/week for FTE)"""
    if self.allocation_type == AllocationType.HOURS:
        return self.allocation_value
    elif self.allocation_type == AllocationType.FTE_PERCENTAGE:
        if self.project_duration_weeks:
            return (self.allocation_value / 100.0) * 40.0 * self.project_duration_weeks
    return None
```

### 3. **Traceability**
```python
class ExtractedField(BaseModel):
    field_name: str
    raw_text: str  # Original text from SOW
    structured_value: Any  # Normalized value
    confidence_score: float
    source_section: Optional[str]
    extraction_method: Literal["regex", "llm", "heuristic", "manual"]
```

### 4. **Billability Tracking**
```python
class BillabilityType(str, Enum):
    BILLABLE = "billable"  # Direct client billable time
    NON_BILLABLE = "non_billable"  # Internal, overhead time
    PASS_THROUGH = "pass_through"  # Pass-through costs (vendors, etc.)
    UNKNOWN = "unknown"  # Not specified in SOW
```

## Output Schema

### Normalized Staffing Plan Structure
```python
class OctagonStaffingPlan(BaseModel):
    project_info: ProjectInfo  # Client, project name, duration, etc.
    roles: List[StaffingRole]  # Normalized role allocations
    financial_structure: Optional[FinancialStructure]  # Budget, rates, payment terms
    total_billable_hours: Optional[float]
    total_non_billable_hours: Optional[float]
    total_fte_percentage: Optional[float]
    service_line_allocation: Dict[OctagonServiceLine, float]  # FTE by service line
    extraction_confidence: float  # Overall confidence score
    completeness_score: float  # Data completeness score
    source_sow_file: str  # Original file reference
    raw_extraction_data: Optional[Dict[str, Any]]  # Full LLM extraction
```

### Key Output Fields
- **Project Name / Client**: Normalized project identification
- **Service Lines / Departments**: Mapped to Octagon structure
- **Roles & Seniority**: Standardized role titles and levels
- **Hours or FTE**: Normalized allocation (both formats available)
- **Duration**: Project timeline and resource allocation periods
- **Billability**: Classification of time types
- **Notes / Special Instructions**: Context and requirements

## Processing Workflow

### 1. **Document Ingestion**
- Accept mixed formats (PDF, DOCX)
- Extract text using optimized parsers
- Validate document structure

### 2. **Heuristic Extraction**
- Extract basic project information
- Identify staffing plan sections
- Parse role and allocation patterns

### 3. **LLM-Enhanced Extraction**
- Use Octagon-specific prompts
- Extract structured data with confidence scores
- Handle ambiguous or incomplete information

### 4. **Normalization & Validation**
- Map roles to Octagon departments
- Normalize allocations (FTE ↔ hours)
- Calculate summary metrics
- Validate completeness

### 5. **Output Generation**
- Create structured staffing plan
- Include traceability information
- Provide quality metrics

## Quality Assurance

### Confidence Scoring
- **Extraction Confidence**: Based on LLM certainty and pattern matching
- **Completeness Score**: Percentage of expected fields populated
- **Role Mapping Success**: How well roles map to Octagon structure

### Validation Mechanisms
- **Cross-reference validation**: Verify consistency across sections
- **Pattern validation**: Check against known SOW structures
- **Completeness checks**: Identify missing critical information
- **Fallback processing**: Use heuristics when LLM fails

### Error Handling
- **Graceful degradation**: Continue processing with partial data
- **Error logging**: Track extraction failures and patterns
- **Manual review flags**: Highlight low-confidence extractions

## Example Output

### Company 1 SOW Processing Result
```json
{
  "project_info": {
    "project_name": "Company 1 Americas 2024-2025 Sponsorship Hospitality Programs",
    "client_name": "Company 1",
    "duration_weeks": 52,
    "project_type": "Sponsorship Hospitality"
  },
  "roles": [
    {
      "role_title": "Account Director",
      "octagon_department": "account_directors",
      "service_line": "client_services",
      "allocation_type": "fte_percentage",
      "allocation_value": 25.0,
      "normalized_hours": 520.0,
      "billability": "billable"
    }
  ],
  "total_fte_percentage": 100.0,
  "service_line_allocation": {
    "client_services": 100.0
  },
  "extraction_confidence": 0.85,
  "completeness_score": 0.90
}
```

## Implementation Status

### ✅ Completed
- **Taxonomy Analysis**: Analyzed 9 sample SOWs for patterns
- **Schema Design**: Created comprehensive Octagon-specific schema
- **Document Intelligence**: Built enhanced processing service
- **Normalization Logic**: Implemented FTE/hours conversion
- **Traceability**: Added raw text to structured field mapping

### 🔄 In Progress
- **Integration Testing**: Testing with sample SOWs
- **Confidence Calibration**: Tuning extraction confidence scores
- **Error Handling**: Refining fallback mechanisms

### 📋 Next Steps
- **API Integration**: Connect to existing FastAPI endpoints
- **UI Integration**: Update Streamlit interface
- **Performance Optimization**: Optimize for production use
- **User Testing**: Validate with Octagon team

## Technical Specifications

### Dependencies
- **PyPDF2**: PDF text extraction
- **zipfile**: DOCX processing
- **Azure OpenAI**: LLM-powered extraction
- **Pydantic**: Schema validation
- **FastAPI**: API integration

### Performance Targets
- **Processing Time**: < 30 seconds per SOW
- **Accuracy**: > 85% for role identification
- **Completeness**: > 80% for critical fields
- **Reliability**: 95% successful processing rate

### Scalability Considerations
- **Batch Processing**: Handle multiple SOWs
- **Caching**: Store extraction results
- **Monitoring**: Track processing metrics
- **Error Recovery**: Handle processing failures

## Success Metrics

### Phase 1 ("Crawl") Success Criteria
1. **Extraction Accuracy**: Successfully extract roles and allocations from 90%+ of sample SOWs
2. **Normalization Quality**: Correctly convert between FTE % and hours in 95%+ of cases
3. **Role Mapping**: Successfully map 85%+ of roles to Octagon departments
4. **Traceability**: Maintain clear links between raw text and structured data
5. **Processing Speed**: Process typical SOW in under 30 seconds

### Future Phase Considerations
- **Phase 2**: Predictive modeling for resource planning
- **Phase 3**: Automated staffing plan generation
- **Phase 4**: Integration with project management systems

## Files Created

1. **`octagon_staffing_schema.py`** - Complete schema with Octagon taxonomy
2. **`octagon_document_intelligence.py`** - Enhanced processing service
3. **`sow_taxonomy_analyzer.py`** - Analysis tool for pattern discovery
4. **`OCTAGON_PROTOTYPE_DESIGN.md`** - This design document

## Conclusion

The Octagon Staffing Plan Generator Prototype provides a robust foundation for Phase 1 ("Crawl") requirements. The schema handles the variability in SOW formats while maintaining consistency in output structure. The traceability features ensure transparency, and the normalization capabilities provide the flexibility needed for future phases.

The design balances current prototype needs with extensibility for future automation and predictive modeling capabilities.

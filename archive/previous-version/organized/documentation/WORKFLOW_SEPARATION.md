# Octagon Staffing Plan Generator - Workflow Separation

## Overview

The system now clearly distinguishes between two distinct workflows for processing SOW documents:

## 🔄 Workflow 1: Historical SOW Upload
**Purpose**: Build the knowledge database with existing SOWs that already have staffing plans

### When to Use:
- ✅ Completed projects with known staffing outcomes
- ✅ Past SOWs with existing staffing plans
- ✅ Training data for improving AI recommendations
- ✅ Building the similarity search database

### What Happens:
1. **Document Processing**: SOW is uploaded and processed (text extraction, LLM parsing)
2. **Staffing Plan Extraction**: Existing staffing plan is extracted from the document
3. **Database Storage**: Document and staffing plan are stored for future reference
4. **Vector Indexing**: Document is indexed for semantic similarity search
5. **Knowledge Building**: Adds to the database used for future recommendations

### API Endpoints:
- `POST /upload-historical-sow` - Upload historical SOW
- `GET /sows/historical` - List historical SOWs
- `GET /staffing-plan/{sow_id}` - View extracted staffing plan

### Streamlit Interface:
- **Tab**: "📚 Historical SOWs"
- **Purpose**: Upload completed SOWs to build the knowledge base

---

## 🆕 Workflow 2: New Staffing Plan Generation
**Purpose**: Generate AI-powered directional staffing plans for new SOWs

### When to Use:
- ✅ New project proposals requiring staffing plans
- ✅ RFPs that need resource allocation
- ✅ Planning new engagements
- ✅ Getting directional staffing recommendations

### What Happens:
1. **Document Processing**: SOW is uploaded and processed (text extraction, LLM parsing)
2. **Role Detection**: Roles and requirements are identified using AI
3. **Heuristics Application**: Baseline allocation rules are applied
4. **Staffing Plan Generation**: AI generates directional staffing plan
5. **Similar Project Matching**: Finds similar historical projects for reference
6. **Draft Output**: Creates editable staffing plan marked as "AI DRAFT"

### API Endpoints:
- `POST /upload-new-sow` - Upload new SOW for staffing plan generation
- `GET /sows/new-staffing` - List new SOWs being processed
- `GET /staffing-plan/{sow_id}` - View generated staffing plan

### Streamlit Interface:
- **Tab**: "🆕 New Staffing Plans"
- **Purpose**: Generate staffing plans for new projects

---

## 🔧 Technical Implementation

### Data Models:
```python
class SOWProcessingType(str, Enum):
    HISTORICAL = "historical"      # Existing SOW with staffing plan
    NEW_STAFFING = "new_staffing"  # New SOW needing staffing plan

class SOWDocument(BaseModel):
    # ... existing fields ...
    processing_type: SOWProcessingType
```

### Processing Logic:
```python
if processing_type == SOWProcessingType.HISTORICAL:
    # Extract existing staffing plan from document
    # Store for database/reference
elif processing_type == SOWProcessingType.NEW_STAFFING:
    # Generate new staffing plan using heuristics
    # Apply AI-powered allocation rules
```

### Status Tracking:
- `completed_historical` - Historical SOW processed and stored
- `completed_new_staffing` - New SOW with generated staffing plan

---

## 📊 User Interface

### Streamlit App Structure:
1. **📚 Historical SOWs** - Upload completed projects to build database
2. **🆕 New Staffing Plans** - Generate staffing plans for new projects  
3. **🔍 Vector Search** - Search similar projects (works with both workflows)
4. **📊 Index Management** - Manage the search database

### Clear Workflow Selection:
- Each tab clearly explains its purpose
- Visual indicators show which workflow to use
- Separate upload interfaces for each workflow
- Distinct processing status messages

---

## 🎯 Benefits of This Separation

### For Users:
- **Clear Purpose**: No confusion about which workflow to use
- **Focused Interface**: Each workflow has its own dedicated space
- **Better UX**: Streamlined process for each use case

### For the System:
- **Optimized Processing**: Different logic for different purposes
- **Better Data Management**: Historical vs. generated data clearly separated
- **Improved AI**: Better training data from historical SOWs improves new recommendations

### For Business:
- **Knowledge Building**: Systematic way to build institutional knowledge
- **Staffing Efficiency**: Quick generation of directional staffing plans
- **Quality Control**: Clear distinction between historical facts and AI recommendations

---

## 🚀 Next Steps

1. **Test Both Workflows**: Verify each workflow works independently
2. **Refine Heuristics**: Improve allocation logic for new staffing plans
3. **Enhance Extraction**: Better extraction of existing staffing plans from historical SOWs
4. **Add Excel Export**: Generate Excel templates for both workflows
5. **Vector Search Integration**: Connect historical SOWs to new staffing plan generation

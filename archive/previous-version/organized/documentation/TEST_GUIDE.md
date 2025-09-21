# 🧪 Streamlit App Testing Guide

## Test Files Created

### 📚 Historical SOW Test File
**File**: `test_files/historical_sow_sample.pdf`
**Content**: Nike Air Max Launch Campaign (Completed Project)

**Key Features for Testing**:
- ✅ **Complete Staffing Plan**: 9 team members with specific roles and percentages
- ✅ **Realistic Roles**: EVP, SVP, VP, Group Director, Managers across departments
- ✅ **Department Mix**: Client Services, Strategy, Creative, Production
- ✅ **Proven Outcomes**: Success metrics and budget allocation
- ✅ **Historical Context**: Marked as "completed project with established staffing plan"

### 🆕 New Staffing SOW Test File  
**File**: `test_files/new_staffing_sow_sample.pdf`
**Content**: Adidas Global Sports Technology Innovation Hub (New Project)

**Key Features for Testing**:
- ✅ **Complex Scope**: 11.5-month global project requiring multiple departments
- ✅ **Technology Focus**: AI, VR/AR, mobile apps, digital platforms
- ✅ **No Staffing Plan**: Requires AI-generated staffing recommendations
- ✅ **Multiple Expertise Areas**: Sports marketing, technology, global coordination
- ✅ **High Complexity**: Cross-cultural, multi-platform, rapid prototyping

---

## 🎯 Testing Instructions

### Test 1: Historical SOW Workflow
1. **Go to Streamlit App**: http://localhost:8501
2. **Navigate to "📚 Historical SOWs" tab**
3. **Upload**: `test_files/historical_sow_sample.pdf`
4. **Click**: "🚀 Process & Index Documents"
5. **Expected Results**:
   - Should extract existing staffing plan (9 team members)
   - Should show "completed_historical" status
   - Should index document for search
   - Should preserve historical staffing data

### Test 2: New Staffing Plan Workflow
1. **Navigate to "🆕 New Staffing Plans" tab**
2. **Upload**: `test_files/new_staffing_sow_sample.pdf`
3. **Click**: "🚀 Generate Staffing Plan"
4. **Expected Results**:
   - Should detect roles: Project Manager, Creative Director, Strategy roles, etc.
   - Should generate AI staffing plan with heuristics
   - Should show department allocations (Client Services, Strategy, Creative, etc.)
   - Should display "AI DRAFT" annotations
   - Should show confidence scores

### Test 3: Vector Search
1. **Navigate to "🔍 Vector Search" tab**
2. **Search Query**: "sports technology innovation"
3. **Expected Results**:
   - Should find the Adidas project
   - Should show relevant staffing information
   - Should display project summary

---

## 🔍 What to Look For

### Historical SOW Processing:
- **Staffing Plan Extraction**: Should identify 9 team members
- **Role Detection**: EVP, SVP, VP, Group Director, Managers
- **Department Assignment**: Client Services, Strategy, Creative, Production
- **Percentage Allocation**: 2%, 15%, 25%, 40%, etc.
- **Status**: "completed_historical"

### New Staffing Plan Generation:
- **Role Detection**: Project Manager, Creative Director, Strategy roles
- **Department Allocation**: Based on heuristics engine rules
- **FTE Percentages**: Client Services 75-100%, Strategy 5-25%, Creative 5-25%
- **Special Rules**: Creative Director 5%, L7/L8 oversight 5%
- **AI Annotations**: Clear "AI DRAFT" labeling
- **Status**: "completed_new_staffing"

### Vector Search Results:
- **Semantic Matching**: Find similar projects by meaning
- **Staffing Information**: Display relevant staffing plans
- **Project Details**: Company, SOW ID, summary information

---

## 🚨 Troubleshooting

### If Upload Fails:
- Check file format (should be PDF)
- Verify file permissions
- Check browser console for errors

### If Processing Fails:
- Check terminal for error messages
- Verify Azure credentials are configured
- Check network connectivity

### If Search Returns No Results:
- Ensure documents were processed first
- Check if vector index was created
- Verify search terms are relevant

---

## 📊 Success Criteria

### ✅ Historical SOW Test Passes If:
- File uploads successfully
- Extracts existing staffing plan (9 team members)
- Shows "completed_historical" status
- Preserves historical data accurately

### ✅ New Staffing Plan Test Passes If:
- File uploads successfully  
- Generates AI staffing plan using heuristics
- Shows department allocations
- Displays "AI DRAFT" annotations
- Shows "completed_new_staffing" status

### ✅ Vector Search Test Passes If:
- Returns relevant search results
- Shows project summaries and staffing info
- Displays similarity scores
- Filters work correctly

---

## 🎉 Expected Outcomes

After successful testing, you should see:

1. **Clear Workflow Separation**: Each tab serves its distinct purpose
2. **Historical Data Preservation**: Existing staffing plans are extracted and stored
3. **AI Staffing Generation**: New projects get intelligent staffing recommendations
4. **Semantic Search**: Find similar projects based on meaning, not just keywords
5. **User-Friendly Interface**: Clear guidance and intuitive workflow

The system should demonstrate the core value proposition: building institutional knowledge from historical SOWs while generating intelligent staffing recommendations for new projects.

# Streamlit Testing Guide - Enhanced Octagon Staffing Generator

## 🚀 Quick Start

### Option 1: Automated Test (Recommended)
```bash
python3 test_streamlit_app.py
```

This will:
- ✅ Start the FastAPI server automatically
- ✅ Start the Streamlit app automatically  
- ✅ Open your browser to http://localhost:8501
- ✅ Run automated tests

### Option 2: Manual Setup

#### Step 1: Start FastAPI Server
```bash
cd octagon-staffing-app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Step 2: Start Streamlit App (New Terminal)
```bash
streamlit run octagon_staffing_app_streamlit.py --server.port 8501
```

#### Step 3: Open Browser
Navigate to: http://localhost:8501

## 🧪 Testing the Enhanced Features

### 1. 📤 Upload SOW Tab

**What to Test:**
- Upload a PDF or DOCX SOW file
- Watch real-time processing status
- See AI-powered analysis in action

**Expected Results:**
- ✅ File uploads successfully
- ✅ Processing status updates in real-time
- ✅ "Processing completed" message appears
- ✅ File ID is generated and stored

### 2. 📊 View Results Tab

**What to Test:**
- View generated staffing plan
- Check business rules compliance
- See AI-enhanced analysis
- Export results as CSV/JSON

**Expected Enhanced Features:**
- 🤖 **AI-Enhanced Analysis**: Project type, complexity, requirements
- 📋 **Business Rules Applied**: All 7 Octagon rules checked
- 👥 **Smart Role Mapping**: Roles mapped to Octagon departments/levels
- 📊 **Confidence Scoring**: Quality metrics for each recommendation
- 🏢 **Department Allocation**: Proper FTE distribution across departments

### 3. 🧪 Test Examples Tab

**What to Test:**
- Review sample SOW content
- Understand expected business rules
- See what the AI should generate

**Expected Business Rules:**
1. ✅ Creative Director always pre-allocated at 5%
2. ✅ L7/L8 leaders allocated for oversight at 5% (Complex/Enterprise)
3. ✅ Sponsorship always ≤ 25% FTE per client (≤ 50% per person)
4. ✅ Client Services 75–100% FTE
5. ✅ Experiences/Hospitality usually near 100% FTE per client
6. ✅ Creative usually 5–25% FTE across multiple clients
7. ✅ Minimum pod size of four employees

## 📊 What You Should See

### Enhanced Staffing Plan Output
```
🤖 AI-ENHANCED Staffing Plan for Company 1
Project: Company 1 Americas 2024-2025 Sponsorship Hospitality Programs
Duration: 48 weeks
Contract: SOW-001

📊 ALLOCATION SUMMARY:
Total FTE: 160.0%
Total Roles: 6 positions

🏢 DEPARTMENT BREAKDOWN:
  • Planning Creative: 5.0% FTE
  • Client Services: 135.0% FTE
  • Strategy: 20.0% FTE

⚙️ BUSINESS RULES:
Octagon Rules Applied: ✅ Yes
Confidence Score: 0.85
Completeness: 0.95

🎯 ROLE BREAKDOWN:
  • Creative Director: 5.0% FTE (Planning Creative, Level 6) [Confidence: 1.00]
  • Account Director: 75.0% FTE (Client Services, Level 5) [Confidence: 0.90]
  • Strategy Director: 20.0% FTE (Strategy, Level 5) [Confidence: 0.90]
  • Account Manager: 25.0% FTE (Client Services, Level 3) [Confidence: 0.80]
  • Senior Account Executive: 20.0% FTE (Client Services, Level 2) [Confidence: 0.80]
  • Account Executive: 15.0% FTE (Client Services, Level 1) [Confidence: 0.80]
```

### Business Rules Validation
- ✅ **Creative Director (5% rule)**: Applied
- ✅ **Minimum Pod Size (4 employees)**: Met (6 roles)
- ✅ **Client Services FTE (75-100%)**: Within range
- ✅ **Department Mapping**: Proper Octagon structure
- ✅ **Confidence Scoring**: High quality metrics

## 🔍 Key Features to Validate

### 1. AI-Powered Analysis
- **Project Type Classification**: Should identify "Sponsorship Activation"
- **Complexity Assessment**: Should classify as "Moderate" or "Simple"
- **Requirement Extraction**: Should extract duration, events, deliverables

### 2. Business Rules Engine
- **Automatic Role Creation**: Should add missing roles to meet minimum pod size
- **FTE Normalization**: Should convert between hours and FTE percentages
- **Department Allocation**: Should ensure proper distribution across Octagon departments
- **Compliance Checking**: Should validate against all 7 business rules

### 3. Quality Assurance
- **Confidence Scoring**: Each role should have a confidence score (0.0-1.0)
- **Audit Trail**: Should show which business rules were applied
- **Traceability**: Should track from raw SOW text to final recommendations

### 4. Enhanced UI Features
- **Real-time Processing**: Status updates during SOW processing
- **Business Rules Display**: Visual indicators of rule compliance
- **Export Options**: CSV and JSON download functionality
- **Technical Details**: Expandable sections for debugging

## 🐛 Troubleshooting

### API Connection Issues
```
❌ API Connection Failed - Please ensure the FastAPI server is running
```
**Solution**: Make sure the FastAPI server is running on port 8000

### File Upload Issues
```
❌ Upload failed: 400 - Invalid processing type
```
**Solution**: The API expects "new_staffing" as the processing type (handled automatically)

### Processing Timeout
```
⏰ Processing timeout - please check the results tab
```
**Solution**: The SOW processing takes time. Check the results tab for updates.

### Business Rules Not Applied
```
⚠️ Business Rules Not Applied
```
**Solution**: This might indicate an issue with the enhanced service. Check the API logs.

## 📈 Success Criteria

### ✅ Test Passed If:
- SOW uploads successfully
- Processing completes without errors
- Staffing plan shows 4+ roles (minimum pod size)
- Creative Director appears at 5% FTE
- Business rules show "Applied: Yes"
- Confidence scores are > 0.7
- Department allocation is reasonable
- Export functions work correctly

### ❌ Test Failed If:
- Upload fails
- Processing errors occur
- Less than 4 roles generated
- Business rules show "Not Applied"
- Confidence scores are < 0.5
- Department allocation is unreasonable
- Export functions don't work

## 🎯 Expected Performance

- **Upload Time**: < 5 seconds
- **Processing Time**: 10-30 seconds (depending on SOW complexity)
- **Total FTE**: 100-200% (realistic for most projects)
- **Role Count**: 4-8 roles (meets minimum pod size)
- **Confidence**: > 0.8 for well-structured SOWs
- **Business Rules**: All 7 rules should be checked and applied as appropriate

## 🚀 Next Steps After Testing

1. **Upload Real SOWs**: Test with actual Octagon SOW documents
2. **Validate Outputs**: Review generated staffing plans for accuracy
3. **Refine Rules**: Adjust business rules based on real-world feedback
4. **Scale Testing**: Test with multiple concurrent uploads
5. **Production Deployment**: Deploy to production environment

**Your enhanced Octagon staffing plan generator is ready for testing! 🎉**

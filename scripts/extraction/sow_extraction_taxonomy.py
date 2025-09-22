#!/usr/bin/env python3
"""
SOW Extraction Taxonomy
======================

Comprehensive keyword dictionaries and patterns for extracting structured data
from SOW documents. This serves as a fallback and validation layer for LLM extraction.
"""

import re
from typing import Dict, List, Pattern

class SOWExtractionTaxonomy:
    """Comprehensive taxonomy for SOW data extraction"""
    
    # ============================================================================
    # CLIENT NAME EXTRACTION
    # ============================================================================
    
    CLIENT_NAME_KEYWORDS = {
        "contract_indicators": [
            "between",
            "agreement between", 
            "contract between",
            "services for",
            "work for",
            "engagement with",
            "retainer with"
        ],
        "label_indicators": [
            "client:",
            "company:",
            "customer:",
            "contractor:",
            "client name:",
            "company name:",
            "customer name:"
        ],
        "signature_indicators": [
            "client signature",
            "company signature", 
            "authorized by",
            "on behalf of",
            "representing",
            "signed by"
        ],
        "exclusion_patterns": [
            "octagon",
            "contractor", 
            "vendor",
            "service provider",
            "consultant",
            "agency"
        ],
        "corporate_suffixes": [
            "inc.", "incorporated", "corp.", "corporation", "llc", "ltd.", "limited",
            "co.", "company", "group", "holdings", "partners", "associates"
        ]
    }
    
    # ============================================================================
    # PROJECT TITLE EXTRACTION
    # ============================================================================
    
    PROJECT_TITLE_KEYWORDS = {
        "title_indicators": [
            "project title:",
            "project name:",
            "work title:",
            "engagement title:",
            "scope title:",
            "statement of work for",
            "services for"
        ],
        "section_headers": [
            "project overview",
            "project description", 
            "scope of work",
            "work statement",
            "project scope"
        ],
        "exclusion_patterns": [
            "confidential",
            "proprietary",
            "internal use",
            "draft",
            "template"
        ]
    }
    
    # ============================================================================
    # START DATE EXTRACTION
    # ============================================================================
    
    START_DATE_KEYWORDS = {
        "primary_indicators": [
            "start date",
            "service start date",
            "project start",
            "commencement date",
            "effective date",
            "begin date",
            "initiation date",
            "work start"
        ],
        "secondary_indicators": [
            "start:",
            "beginning:",
            "effective:",
            "commencement:",
            "initiation:"
        ],
        "context_patterns": [
            "services start date:",
            "project start date:",
            "contract start:",
            "work begins:",
            "engagement starts:",
            "retainer begins:",
            "effective as of:"
        ],
        "date_formats": [
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b\d{1,2}\s+(?:of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b"
        ]
    }
    
    # ============================================================================
    # END DATE EXTRACTION
    # ============================================================================
    
    END_DATE_KEYWORDS = {
        "primary_indicators": [
            "end date",
            "service end date",
            "project end",
            "completion date",
            "termination date",
            "expiration date",
            "finish date",
            "work end"
        ],
        "secondary_indicators": [
            "end:",
            "completion:",
            "termination:",
            "expiration:",
            "finish:",
            "conclusion:"
        ],
        "context_patterns": [
            "services end date:",
            "project end date:",
            "contract end:",
            "work ends:",
            "engagement ends:",
            "retainer ends:",
            "through:",
            "until:"
        ],
        "duration_indicators": [
            "through",
            "until", 
            "ending",
            "concluding",
            "expires",
            "terminates"
        ],
        "date_formats": [
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b\d{1,2}\s+(?:of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b"
        ]
    }
    
    # ============================================================================
    # PROJECT LENGTH EXTRACTION
    # ============================================================================
    
    PROJECT_LENGTH_KEYWORDS = {
        "duration_indicators": [
            "project length",
            "duration",
            "term",
            "period",
            "timeline",
            "project timeline",
            "engagement period"
        ],
        "time_units": [
            "months", "month", "mo", "m",
            "weeks", "week", "wk", "w", 
            "days", "day", "d",
            "years", "year", "yr", "y"
        ],
        "duration_patterns": [
            r"\d+\s*(?:months?|mo\.?|m)",
            r"\d+\s*(?:weeks?|wk\.?|w)",
            r"\d+\s*(?:days?|d)",
            r"\d+\s*(?:years?|yr\.?|y)",
            r"\d+\s*-\s*\d+\s*(?:months?|weeks?|days?)",
            r"\d+\s*to\s*\d+\s*(?:months?|weeks?|days?)"
        ],
        "approximate_indicators": [
            "approximately",
            "approx",
            "about",
            "around",
            "roughly",
            "estimated",
            "expected"
        ]
    }
    
    # ============================================================================
    # SCOPE SUMMARY EXTRACTION
    # ============================================================================
    
    SCOPE_SUMMARY_KEYWORDS = {
        "section_headers": [
            "scope of work",
            "project scope",
            "work statement",
            "project description",
            "overview",
            "summary",
            "background",
            "objectives"
        ],
        "introductory_phrases": [
            "the purpose of this",
            "this project involves",
            "the scope includes",
            "work will include",
            "services will consist of",
            "the engagement will"
        ],
        "exclusion_patterns": [
            "confidential",
            "proprietary",
            "internal",
            "draft",
            "template"
        ]
    }
    
    # ============================================================================
    # DELIVERABLES EXTRACTION
    # ============================================================================
    
    DELIVERABLES_KEYWORDS = {
        "section_headers": [
            "deliverables",
            "scope of work",
            "work product",
            "outputs",
            "deliverable items",
            "project deliverables",
            "key deliverables",
            "work products"
        ],
        "list_indicators": [
            "•", "▪", "○", "◦", "‣", "⁃",
            "-", "–", "—",
            "1.", "2.", "3.", "4.", "5.",
            "a.", "b.", "c.", "d.", "e.",
            "i.", "ii.", "iii.", "iv.", "v."
        ],
        "action_verbs": [
            "provide", "deliver", "create", "develop", "produce", "generate",
            "submit", "present", "complete", "implement", "execute",
            "design", "build", "establish", "maintain", "support"
        ],
        "deliverable_indicators": [
            "deliverable",
            "output",
            "product",
            "report",
            "document",
            "analysis",
            "strategy",
            "plan",
            "recommendation"
        ]
    }
    
    # ============================================================================
    # EXCLUSIONS EXTRACTION
    # ============================================================================
    
    EXCLUSIONS_KEYWORDS = {
        "section_headers": [
            "exclusions",
            "not included",
            "out of scope",
            "excluded",
            "not covered",
            "outside scope",
            "limitations"
        ],
        "exclusion_indicators": [
            "excludes",
            "not include",
            "out of scope",
            "not covered",
            "not responsible for",
            "beyond scope",
            "not part of"
        ],
        "list_indicators": [
            "•", "▪", "○", "◦", "‣", "⁃",
            "-", "–", "—",
            "1.", "2.", "3.", "4.", "5.",
            "a.", "b.", "c.", "d.", "e."
        ]
    }
    
    # ============================================================================
    # STAFFING PLAN EXTRACTION
    # ============================================================================
    
    STAFFING_PLAN_KEYWORDS = {
        "section_headers": [
            "staffing plan",
            "staff plan",
            "personnel",
            "team",
            "resources",
            "fees",
            "project team",
            "key personnel",
            "staffing table",
            "resource allocation"
        ],
        "table_indicators": [
            "title discipline hours",
            "name", "role", "allocation", "fte",
            "hours", "percentage", "time", "position", "level",
            "title", "discipline", "allocation"
        ],
        "role_patterns": [
            r"\b(?:EVP|SVP|VP|Director|Manager|Executive|Analyst|Coordinator|Lead|Specialist)\b",
            r"\b(?:Account|Project|Program|Client|Senior|Junior|Associate|Principal)\s+(?:Director|Manager|Executive|Analyst|Coordinator|Lead)\b",
            r"\b(?:Vice\s+)?President\b",
            r"\b(?:Senior\s+)?(?:Account|Project|Program|Client)\s+(?:Executive|Manager|Director)\b"
        ],
        "allocation_patterns": [
            r"\d+(?:\.\d+)?\s*%",
            r"\d+\s*hrs?",
            r"\d+\s*hours?",
            r"\d+(?:\.\d+)?\s*fte",
            r"\d+\s*-\s*\d+\s*hrs?",
            r"\d+\s*to\s*\d+\s*hrs?"
        ],
        "location_indicators": [
            r"\b(?:US|UK|USA|United States|United Kingdom|Canada|Mexico)\b",
            r"\b(?:New York|Los Angeles|Chicago|Houston|Phoenix|Philadelphia|San Antonio|San Diego|Dallas|San Jose)\b"
        ]
    }
    
    # ============================================================================
    # COMPILED REGEX PATTERNS
    # ============================================================================
    
    @classmethod
    def get_compiled_patterns(cls) -> Dict[str, List[Pattern]]:
        """Get compiled regex patterns for efficient matching"""
        return {
            "start_date_formats": [re.compile(pattern, re.IGNORECASE) for pattern in cls.START_DATE_KEYWORDS["date_formats"]],
            "end_date_formats": [re.compile(pattern, re.IGNORECASE) for pattern in cls.END_DATE_KEYWORDS["date_formats"]],
            "duration_patterns": [re.compile(pattern, re.IGNORECASE) for pattern in cls.PROJECT_LENGTH_KEYWORDS["duration_patterns"]],
            "role_patterns": [re.compile(pattern, re.IGNORECASE) for pattern in cls.STAFFING_PLAN_KEYWORDS["role_patterns"]],
            "allocation_patterns": [re.compile(pattern, re.IGNORECASE) for pattern in cls.STAFFING_PLAN_KEYWORDS["allocation_patterns"]],
            "location_patterns": [re.compile(pattern, re.IGNORECASE) for pattern in cls.STAFFING_PLAN_KEYWORDS["location_indicators"]]
        }
    
    # ============================================================================
    # FIELD PRIORITY AND CONFIDENCE SCORING
    # ============================================================================
    
    FIELD_PRIORITIES = {
        "client_name": 1,
        "project_title": 2,
        "start_date": 3,
        "end_date": 4,
        "project_length": 5,
        "scope_summary": 6,
        "deliverables": 7,
        "exclusions": 8,
        "staffing_plan": 9
    }
    
    CONFIDENCE_THRESHOLDS = {
        "high": 0.8,
        "medium": 0.6,
        "low": 0.4
    }
    
    # ============================================================================
    # VALIDATION RULES
    # ============================================================================
    
    VALIDATION_RULES = {
        "date_validation": {
            "end_after_start": True,
            "valid_date_formats": ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"],
            "future_dates_allowed": True
        },
        "staffing_validation": {
            "require_role": True,
            "require_allocation": True,
            "max_team_size": 50
        },
        "deliverables_validation": {
            "min_deliverables": 1,
            "max_deliverable_length": 500
        }
    }

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_field_keywords(field_name: str) -> Dict[str, List[str]]:
    """Get keywords for a specific field"""
    field_mapping = {
        "client_name": SOWExtractionTaxonomy.CLIENT_NAME_KEYWORDS,
        "project_title": SOWExtractionTaxonomy.PROJECT_TITLE_KEYWORDS,
        "start_date": SOWExtractionTaxonomy.START_DATE_KEYWORDS,
        "end_date": SOWExtractionTaxonomy.END_DATE_KEYWORDS,
        "project_length": SOWExtractionTaxonomy.PROJECT_LENGTH_KEYWORDS,
        "scope_summary": SOWExtractionTaxonomy.SCOPE_SUMMARY_KEYWORDS,
        "deliverables": SOWExtractionTaxonomy.DELIVERABLES_KEYWORDS,
        "exclusions": SOWExtractionTaxonomy.EXCLUSIONS_KEYWORDS,
        "staffing_plan": SOWExtractionTaxonomy.STAFFING_PLAN_KEYWORDS
    }
    return field_mapping.get(field_name, {})

def get_compiled_patterns_for_field(field_name: str) -> List[Pattern]:
    """Get compiled regex patterns for a specific field"""
    all_patterns = SOWExtractionTaxonomy.get_compiled_patterns()
    
    pattern_mapping = {
        "start_date": all_patterns["start_date_formats"],
        "end_date": all_patterns["end_date_formats"],
        "project_length": all_patterns["duration_patterns"],
        "staffing_plan": all_patterns["role_patterns"] + all_patterns["allocation_patterns"]
    }
    
    return pattern_mapping.get(field_name, [])

if __name__ == "__main__":
    # Test the taxonomy
    print("🔍 SOW Extraction Taxonomy")
    print("=" * 50)
    
    # Show available fields
    fields = list(SOWExtractionTaxonomy.FIELD_PRIORITIES.keys())
    print(f"📋 Available fields: {', '.join(fields)}")
    
    # Show pattern counts
    patterns = SOWExtractionTaxonomy.get_compiled_patterns()
    for pattern_name, pattern_list in patterns.items():
        print(f"🔧 {pattern_name}: {len(pattern_list)} patterns")
    
    # Test field keywords
    print(f"\n📝 Client Name Keywords:")
    client_keywords = get_field_keywords("client_name")
    for category, keywords in client_keywords.items():
        print(f"   {category}: {len(keywords)} keywords")
    
    print(f"\n✅ Taxonomy loaded successfully!")

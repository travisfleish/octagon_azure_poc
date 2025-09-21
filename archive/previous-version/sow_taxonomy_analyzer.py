#!/usr/bin/env python3
"""
SOW Taxonomy Analyzer - Sandbox script to analyze sample SOWs and identify key terms

This script analyzes all SOWs in the /sows directory to:
1. Extract text content from PDFs and DOCX files
2. Identify common patterns, sections, and terminology
3. Generate a taxonomy of key terms for schema design
4. Create structured output for further analysis
"""

import os
import re
import json
import zipfile
import io
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict

try:
    from PyPDF2 import PdfReader
except ImportError:
    print("Installing PyPDF2...")
    os.system("pip install PyPDF2")
    from PyPDF2 import PdfReader


@dataclass
class SOWAnalysis:
    """Results of analyzing a single SOW"""
    filename: str
    file_type: str
    text_length: int
    sections_found: List[str]
    key_phrases: List[str]
    roles_mentioned: List[str]
    deliverables: List[str]
    timeline_indicators: List[str]
    budget_indicators: List[str]
    client_info: Dict[str, str]
    raw_text_sample: str  # First 500 chars for context


class SOWTaxonomyAnalyzer:
    """Analyzes SOWs to identify patterns and create taxonomy"""
    
    def __init__(self, sows_directory: str = "sows"):
        self.sows_directory = Path(sows_directory)
        self.analyses: List[SOWAnalysis] = []
        
        # Patterns to identify
        self.section_patterns = [
            r"^(\d+\.?\s*)?(Scope of Work|Scope|Project Scope)",
            r"^(\d+\.?\s*)?(Deliverables?|Deliverables)",
            r"^(\d+\.?\s*)?(Timeline|Schedule|Duration|Project Timeline)",
            r"^(\d+\.?\s*)?(Budget|Cost|Pricing|Fees|Rates)",
            r"^(\d+\.?\s*)?(Roles?|Staffing|Team|Personnel)",
            r"^(\d+\.?\s*)?(Responsibilities?|Duties)",
            r"^(\d+\.?\s*)?(Assumptions?|Constraints|Limitations)",
            r"^(\d+\.?\s*)?(Success Criteria|Metrics|KPIs)",
            r"^(\d+\.?\s*)?(Risk|Risks|Risk Management)",
            r"^(\d+\.?\s*)?(Communication|Reporting|Updates)",
        ]
        
        self.role_patterns = [
            r"\b(Account Manager|Account Director)\b",
            r"\b(Creative Director|Art Director)\b", 
            r"\b(Project Manager|Program Manager)\b",
            r"\b(Strategy Director|Strategy Manager|Strategist)\b",
            r"\b(Analyst|Business Analyst|Data Analyst)\b",
            r"\b(Designer|Graphic Designer|UI/UX Designer)\b",
            r"\b(Developer|Engineer|Software Engineer)\b",
            r"\b(Coordinator|Project Coordinator)\b",
            r"\b(Producer|Content Producer)\b",
            r"\b(Consultant|Senior Consultant)\b",
            r"\b(Director|Senior Director|VP|Vice President)\b",
        ]
        
        self.timeline_patterns = [
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b(weeks?|months?|years?)\b",
            r"\b(Q[1-4]|Quarter [1-4])\b",
        ]
        
        self.budget_patterns = [
            r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b",
            r"\b\d{1,6}\s*(?:USD|dollars?)\b",
            r"\b(rate|fee|cost|budget|pricing)\b",
            r"\b(per hour|hourly|daily|monthly)\b",
            r"\b(FTE|full.?time|part.?time)\b",
        ]

    def extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                text = ""
                for page in reader.pages[:10]:  # Limit to first 10 pages
                    text += page.extract_text() or ""
                return text
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            return ""

    def extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX file"""
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                xml_content = zip_file.read('word/document.xml')
                # Simple XML text extraction
                text = re.sub(r'<[^>]+>', ' ', xml_content.decode('utf-8', errors='ignore'))
                text = re.sub(r'\s+', ' ', text)
                return text.strip()
        except Exception as e:
            print(f"Error reading DOCX {file_path}: {e}")
            return ""

    def analyze_sow(self, file_path: Path) -> SOWAnalysis:
        """Analyze a single SOW file"""
        print(f"Analyzing: {file_path.name}")
        
        # Determine file type and extract text
        if file_path.suffix.lower() == '.pdf':
            text = self.extract_pdf_text(file_path)
            file_type = "PDF"
        elif file_path.suffix.lower() in ['.docx', '.doc']:
            text = self.extract_docx_text(file_path)
            file_type = "DOCX"
        else:
            print(f"Skipping unsupported file: {file_path}")
            return None
        
        if not text.strip():
            print(f"No text extracted from {file_path.name}")
            return None
        
        # Find sections
        sections_found = []
        for pattern in self.section_patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            if matches:
                sections_found.extend([match[1] if isinstance(match, tuple) else match for match in matches])
        
        # Find roles
        roles_mentioned = []
        for pattern in self.role_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            roles_mentioned.extend(matches)
        
        # Find deliverables (simple pattern matching)
        deliverable_patterns = [
            r"(?:deliver|provide|submit|create|develop)\s+([^.!?]*(?:report|document|plan|strategy|analysis|design|campaign|materials)[^.!?]*)",
            r"deliverables?[:\-]\s*([^.!?]*)",
        ]
        deliverables = []
        for pattern in deliverable_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            deliverables.extend([match.strip() for match in matches])
        
        # Find timeline indicators
        timeline_indicators = []
        for pattern in self.timeline_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            timeline_indicators.extend(matches)
        
        # Find budget indicators
        budget_indicators = []
        for pattern in self.budget_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            budget_indicators.extend(matches)
        
        # Extract client info (simple patterns)
        client_patterns = [
            r"(?:client|company|organization):\s*([A-Za-z0-9\s&.,-]+)",
            r"(?:between|with)\s+([A-Z][A-Za-z0-9\s&.,-]+)\s+(?:and|&)",
        ]
        client_info = {}
        for pattern in client_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                client_info[f"client_{len(client_info)}"] = matches[0].strip()
        
        # Extract key phrases (sentences with important keywords)
        key_phrases = []
        important_keywords = ['scope', 'deliverable', 'timeline', 'budget', 'role', 'responsibility', 'milestone']
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences[:50]:  # Limit to first 50 sentences
            sentence = sentence.strip()
            if any(keyword in sentence.lower() for keyword in important_keywords) and len(sentence) > 20:
                key_phrases.append(sentence[:100])  # Truncate long sentences
        
        return SOWAnalysis(
            filename=file_path.name,
            file_type=file_type,
            text_length=len(text),
            sections_found=list(set(sections_found)),
            key_phrases=key_phrases[:10],  # Top 10 phrases
            roles_mentioned=list(set(roles_mentioned)),
            deliverables=deliverables[:10],  # Top 10 deliverables
            timeline_indicators=list(set(timeline_indicators)),
            budget_indicators=list(set(budget_indicators)),
            client_info=client_info,
            raw_text_sample=text[:500]  # First 500 characters
        )

    def analyze_all_sows(self) -> Dict[str, Any]:
        """Analyze all SOWs in the directory"""
        if not self.sows_directory.exists():
            print(f"SOWs directory not found: {self.sows_directory}")
            return {}
        
        print(f"Found SOWs directory: {self.sows_directory}")
        
        # Find all SOW files
        sow_files = []
        for ext in ['*.pdf', '*.docx', '*.doc']:
            sow_files.extend(self.sows_directory.glob(ext))
        
        print(f"Found {len(sow_files)} SOW files to analyze")
        
        # Analyze each SOW
        for file_path in sorted(sow_files):
            analysis = self.analyze_sow(file_path)
            if analysis:
                self.analyses.append(analysis)
        
        return self.generate_taxonomy_report()

    def generate_taxonomy_report(self) -> Dict[str, Any]:
        """Generate comprehensive taxonomy report from all analyses"""
        
        # Aggregate data across all SOWs
        all_sections = []
        all_roles = []
        all_deliverables = []
        all_timeline_terms = []
        all_budget_terms = []
        all_key_phrases = []
        
        for analysis in self.analyses:
            all_sections.extend(analysis.sections_found)
            all_roles.extend(analysis.roles_mentioned)
            all_deliverables.extend(analysis.deliverables)
            all_timeline_terms.extend(analysis.timeline_indicators)
            all_budget_terms.extend(analysis.budget_indicators)
            all_key_phrases.extend(analysis.key_phrases)
        
        # Count frequencies
        section_freq = Counter(all_sections)
        role_freq = Counter(all_roles)
        deliverable_freq = Counter(all_deliverables)
        timeline_freq = Counter(all_timeline_terms)
        budget_freq = Counter(all_budget_terms)
        
        # Identify common patterns
        common_sections = [section for section, count in section_freq.most_common(10) if count > 1]
        common_roles = [role for role, count in role_freq.most_common(15) if count > 0]
        common_deliverables = [deliverable for deliverable, count in deliverable_freq.most_common(10) if count > 1]
        
        # Create taxonomy structure
        taxonomy = {
            "metadata": {
                "total_sows_analyzed": len(self.analyses),
                "file_types": list(set(analysis.file_type for analysis in self.analyses)),
                "total_text_length": sum(analysis.text_length for analysis in self.analyses)
            },
            "section_taxonomy": {
                "common_sections": common_sections,
                "all_sections_found": dict(section_freq.most_common()),
                "section_patterns": self.section_patterns
            },
            "role_taxonomy": {
                "common_roles": common_roles,
                "all_roles_found": dict(role_freq.most_common()),
                "role_categories": self._categorize_roles(common_roles)
            },
            "deliverable_taxonomy": {
                "common_deliverables": common_deliverables,
                "all_deliverables_found": dict(deliverable_freq.most_common()),
                "deliverable_types": self._categorize_deliverables(common_deliverables)
            },
            "temporal_taxonomy": {
                "common_timeline_terms": dict(timeline_freq.most_common(20)),
                "timeline_patterns": self.timeline_patterns
            },
            "financial_taxonomy": {
                "common_budget_terms": dict(budget_freq.most_common(20)),
                "budget_patterns": self.budget_patterns
            },
            "individual_analyses": [asdict(analysis) for analysis in self.analyses]
        }
        
        return taxonomy

    def _categorize_roles(self, roles: List[str]) -> Dict[str, List[str]]:
        """Categorize roles by department/function"""
        categories = {
            "Account Management": [],
            "Creative": [],
            "Strategy": [],
            "Project Management": [],
            "Technical": [],
            "Analytics": [],
            "Other": []
        }
        
        for role in roles:
            role_lower = role.lower()
            if any(keyword in role_lower for keyword in ['account', 'client', 'relationship']):
                categories["Account Management"].append(role)
            elif any(keyword in role_lower for keyword in ['creative', 'design', 'art', 'copy', 'content']):
                categories["Creative"].append(role)
            elif any(keyword in role_lower for keyword in ['strategy', 'strategist', 'planning']):
                categories["Strategy"].append(role)
            elif any(keyword in role_lower for keyword in ['project', 'program', 'manager', 'coordinator']):
                categories["Project Management"].append(role)
            elif any(keyword in role_lower for keyword in ['developer', 'engineer', 'technical', 'tech']):
                categories["Technical"].append(role)
            elif any(keyword in role_lower for keyword in ['analyst', 'data', 'research']):
                categories["Analytics"].append(role)
            else:
                categories["Other"].append(role)
        
        return {k: v for k, v in categories.items() if v}  # Remove empty categories

    def _categorize_deliverables(self, deliverables: List[str]) -> Dict[str, List[str]]:
        """Categorize deliverables by type"""
        categories = {
            "Reports & Analysis": [],
            "Creative Assets": [],
            "Strategic Documents": [],
            "Technical Deliverables": [],
            "Other": []
        }
        
        for deliverable in deliverables:
            deliverable_lower = deliverable.lower()
            if any(keyword in deliverable_lower for keyword in ['report', 'analysis', 'study', 'audit']):
                categories["Reports & Analysis"].append(deliverable)
            elif any(keyword in deliverable_lower for keyword in ['creative', 'design', 'brand', 'campaign', 'materials']):
                categories["Creative Assets"].append(deliverable)
            elif any(keyword in deliverable_lower for keyword in ['strategy', 'plan', 'roadmap', 'framework']):
                categories["Strategic Documents"].append(deliverable)
            elif any(keyword in deliverable_lower for keyword in ['system', 'platform', 'tool', 'software']):
                categories["Technical Deliverables"].append(deliverable)
            else:
                categories["Other"].append(deliverable)
        
        return {k: v for k, v in categories.items() if v}  # Remove empty categories

    def save_results(self, output_file: str = "sow_taxonomy_analysis.json"):
        """Save analysis results to JSON file"""
        if not self.analyses:
            print("No analyses to save. Run analyze_all_sows() first.")
            return
        
        taxonomy = self.generate_taxonomy_report()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(taxonomy, f, indent=2, ensure_ascii=False)
        
        print(f"Analysis results saved to: {output_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("SOW TAXONOMY ANALYSIS SUMMARY")
        print("="*60)
        print(f"Total SOWs analyzed: {taxonomy['metadata']['total_sows_analyzed']}")
        print(f"File types: {', '.join(taxonomy['metadata']['file_types'])}")
        print(f"Total text length: {taxonomy['metadata']['total_text_length']:,} characters")
        
        print(f"\nCommon sections found:")
        for section in taxonomy['section_taxonomy']['common_sections'][:5]:
            print(f"  - {section}")
        
        print(f"\nCommon roles found:")
        for role in taxonomy['role_taxonomy']['common_roles'][:8]:
            print(f"  - {role}")
        
        print(f"\nRole categories:")
        for category, roles in taxonomy['role_taxonomy']['role_categories'].items():
            print(f"  {category}: {len(roles)} roles")
        
        print(f"\nDeliverable categories:")
        for category, deliverables in taxonomy['deliverable_taxonomy']['deliverable_types'].items():
            print(f"  {category}: {len(deliverables)} types")


def main():
    """Main function to run the SOW taxonomy analysis"""
    analyzer = SOWTaxonomyAnalyzer()
    
    print("Starting SOW Taxonomy Analysis...")
    print("This will analyze all SOWs in the 'sows' directory")
    
    results = analyzer.analyze_all_sows()
    
    if results:
        analyzer.save_results()
        
        # Also create a simplified summary for quick review
        summary_file = "sow_taxonomy_summary.txt"
        with open(summary_file, 'w') as f:
            f.write("SOW TAXONOMY ANALYSIS - QUICK SUMMARY\n")
            f.write("="*50 + "\n\n")
            
            f.write(f"Files analyzed: {results['metadata']['total_sows_analyzed']}\n")
            f.write(f"Total text: {results['metadata']['total_text_length']:,} chars\n\n")
            
            f.write("TOP SECTIONS:\n")
            for section, count in list(results['section_taxonomy']['all_sections_found'].items())[:10]:
                f.write(f"  {section}: {count} occurrences\n")
            
            f.write("\nTOP ROLES:\n")
            for role, count in list(results['role_taxonomy']['all_roles_found'].items())[:15]:
                f.write(f"  {role}: {count} occurrences\n")
            
            f.write("\nROLE CATEGORIES:\n")
            for category, roles in results['role_taxonomy']['role_categories'].items():
                f.write(f"  {category}:\n")
                for role in roles[:3]:  # Top 3 per category
                    f.write(f"    - {role}\n")
        
        print(f"Quick summary saved to: {summary_file}")
    else:
        print("No SOWs found or analysis failed.")


if __name__ == "__main__":
    main()

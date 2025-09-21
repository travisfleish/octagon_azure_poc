#!/usr/bin/env python3
"""
Show Comparison Summary
======================

Quick script to show the summary of the extraction comparison results.
"""

import pandas as pd
import glob

def show_comparison_summary():
    """Show summary of comparison results"""
    
    # Find the most recent detailed comparison CSV
    csv_files = glob.glob("detailed_comparison_*.csv")
    if not csv_files:
        print("❌ No comparison CSV files found")
        return
    
    latest_csv = max(csv_files)
    print(f"📊 Analyzing: {latest_csv}")
    
    # Load the data
    df = pd.read_csv(latest_csv)
    
    print(f"\n📈 EXTRACTION METHODS COMPARISON SUMMARY")
    print("=" * 60)
    
    # Overall statistics
    total_comparisons = len(df)
    matches = len(df[df['Status'] == 'Match'])
    llm_only = len(df[df['Status'] == 'LLM Only'])
    taxonomy_only = len(df[df['Status'] == 'Taxonomy Only'])
    different = len(df[df['Status'] == 'Different'])
    
    print(f"📊 Overall Statistics:")
    print(f"   Total field comparisons: {total_comparisons}")
    print(f"   Matches: {matches} ({matches/total_comparisons*100:.1f}%)")
    print(f"   LLM Only: {llm_only} ({llm_only/total_comparisons*100:.1f}%)")
    print(f"   Taxonomy Only: {taxonomy_only} ({taxonomy_only/total_comparisons*100:.1f}%)")
    print(f"   Different: {different} ({different/total_comparisons*100:.1f}%)")
    
    # Field-level statistics
    print(f"\n🔍 Field-Level Analysis:")
    field_stats = df.groupby('Field')['Status'].value_counts().unstack(fill_value=0)
    
    for field in field_stats.index:
        total = field_stats.loc[field].sum()
        match_count = field_stats.loc[field].get('Match', 0)
        match_rate = (match_count / total * 100) if total > 0 else 0
        
        print(f"   {field}:")
        print(f"      Match Rate: {match_rate:.1f}% ({match_count}/{total})")
        print(f"      LLM Only: {field_stats.loc[field].get('LLM Only', 0)}")
        print(f"      Taxonomy Only: {field_stats.loc[field].get('Taxonomy Only', 0)}")
        print(f"      Different: {field_stats.loc[field].get('Different', 0)}")
    
    # File-level statistics
    print(f"\n📄 File-Level Analysis:")
    file_stats = df.groupby('File Name')['Status'].value_counts().unstack(fill_value=0)
    
    for file_name in file_stats.index:
        total = file_stats.loc[file_name].sum()
        match_count = file_stats.loc[file_name].get('Match', 0)
        match_rate = (match_count / total * 100) if total > 0 else 0
        
        print(f"   {file_name}: {match_rate:.1f}% match rate ({match_count}/{total})")
    
    # Show some examples of differences
    print(f"\n🔍 Examples of Differences:")
    different_cases = df[df['Status'] == 'Different'].head(5)
    
    for _, row in different_cases.iterrows():
        print(f"\n   File: {row['File Name']}")
        print(f"   Field: {row['Field']}")
        print(f"   LLM: {row['LLM Value'][:100]}...")
        print(f"   Taxonomy: {row['Taxonomy Value'][:100]}...")
    
    # Show LLM-only cases
    print(f"\n🤖 LLM-Only Extractions (where taxonomy missed):")
    llm_only_cases = df[df['Status'] == 'LLM Only'].head(5)
    
    for _, row in llm_only_cases.iterrows():
        print(f"\n   File: {row['File Name']}")
        print(f"   Field: {row['Field']}")
        print(f"   LLM found: {row['LLM Value'][:100]}...")
    
    # Show taxonomy-only cases
    print(f"\n🔧 Taxonomy-Only Extractions (where LLM missed):")
    taxonomy_only_cases = df[df['Status'] == 'Taxonomy Only'].head(5)
    
    for _, row in taxonomy_only_cases.iterrows():
        print(f"\n   File: {row['File Name']}")
        print(f"   Field: {row['Field']}")
        print(f"   Taxonomy found: {row['Taxonomy Value'][:100]}...")
    
    print(f"\n✅ Analysis complete!")
    print(f"📊 Chart: extraction_comparison_*.png")
    print(f"📋 Detailed CSV: {latest_csv}")

if __name__ == "__main__":
    show_comparison_summary()

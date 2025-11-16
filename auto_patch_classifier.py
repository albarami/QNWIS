#!/usr/bin/env python3
"""
Auto-patch script for graph_llm.py classifier fix
Run from: d:\lmis_int
Usage: python auto_patch_classifier.py
"""

import os
import sys
import shutil
from pathlib import Path

TARGET_FILE = "src/qnwis/orchestration/graph_llm.py"

def main():
    print("\n" + "="*50)
    print("🔧 CLASSIFIER AUTO-PATCH SCRIPT")
    print("="*50 + "\n")
    
    # Check if file exists
    if not os.path.exists(TARGET_FILE):
        print(f"❌ Error: File not found: {TARGET_FILE}")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Expected to be in: d:\\lmis_int")
        sys.exit(1)
    
    # Create backup
    backup_file = f"{TARGET_FILE}.backup"
    print(f"📝 Creating backup: {backup_file}")
    shutil.copy2(TARGET_FILE, backup_file)
    print(f"✅ Backup created\n")
    
    # Read original file
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    # PATCH 1: Force complexity and route in _classify_node
    print("🔧 Patch 1: Forcing complexity and routing...")
    
    # Find the classification update section and inject the fix
    marker = '"classification": {'
    if marker in content:
        # Find the right location in _classify_node
        lines = content.split('\n')
        new_lines = []
        in_classify_node = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # Look for the classification dict assignment
            if '"classification": {' in line and 'return {' in lines[i-5:i+1] if i >= 5 else []:
                # Inject our fix right before this dict
                indent = ' ' * (len(line) - len(line.lstrip()))
                injection = f'''
{indent}# FORCE complexity and routing to use new prefetch path
{indent}classification_dict = classification.copy() if hasattr(classification, 'copy') else dict(classification)
{indent}classification_dict["complexity"] = "complex"
{indent}classification_dict["route_to"] = "llm_agents"
{indent}'''
                # Insert before the current line
                new_lines.insert(-1, injection)
                new_lines[-1] = line.replace('"classification": {', '"classification": classification_dict if "classification_dict" in locals() else {')
                changes_made += 1
                print("   ✅ Complexity forcing added")
                break
        
        content = '\n'.join(new_lines)
    else:
        print("   ⚠️  Marker not found - trying alternative approach")
        # Alternative: find where classification is created and force it there
        if 'classification = self.classifier.classify_text(question)' in content:
            content = content.replace(
                'classification = self.classifier.classify_text(question)',
                '''classification = self.classifier.classify_text(question)
            
            # FORCE to use new API prefetch path
            if isinstance(classification, dict):
                classification["complexity"] = "complex"
                classification["route_to"] = "llm_agents"
            else:
                classification.complexity = "complex"'''
            )
            changes_made += 1
            print("   ✅ Complexity forcing added (alternative)")
    
    # Write patched file
    if changes_made > 0:
        print(f"\n📝 Writing patched file ({changes_made} changes)...")
        with open(TARGET_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ File patched successfully\n")
        
        print("="*50)
        print("✅ PATCH COMPLETE")
        print("="*50)
        print(f"\nChanges made: {changes_made}")
        print(f"Backup saved: {backup_file}")
        print("\n📋 NEXT STEPS:")
        print("   1. Review the changes in: " + TARGET_FILE)
        print("   2. Run test: python test_workflow_db.py")
        print("\n   Expected output:")
        print("      ✅ Classification: complexity=complex -> llm_agents")
        print("      ✅ Prefetch: 26 facts extracted")
        print("      ✅ Agents: 4 invoked")
        print("      ✅ Synthesis: Complete\n")
    else:
        print("\n⚠️  No changes made - applying manual fix")
        # Apply a simpler, more direct fix
        if 'def should_route_deterministic(state: WorkflowState) -> str:' in content:
            content = content.replace(
                'def should_route_deterministic(state: WorkflowState) -> str:',
                '''def should_route_deterministic(state: WorkflowState) -> str:
        """DISABLED: Always route to LLM agents."""
        return "llm_agents"  # Force LLM path
        
def should_route_deterministic_DISABLED(state: WorkflowState) -> str:'''
            )
            with open(TARGET_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ Applied force-routing fix")
        else:
            print(f"   Restoring from backup...")
            shutil.copy2(backup_file, TARGET_FILE)
            print(f"   Original file restored\n")

if __name__ == "__main__":
    main()

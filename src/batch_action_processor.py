#!/usr/bin/env python3
"""
Batch Action Processor

This script processes multiple GOTO URL actions from a file or list,
extracting selectors for each URL and maintaining comprehensive tracking.
"""

import os
import json
import time
from typing import List, Dict
from action_handler import ActionHandler


def process_actions_from_file(file_path: str) -> List[Dict]:
    """
    Process GOTO URL actions from a text file.
    
    Args:
        file_path (str): Path to file containing actions (one per line)
        
    Returns:
        List[Dict]: Results of processing each action
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return []
    
    results = []
    handler = ActionHandler()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"📁 Processing {len(lines)} actions from {file_path}")
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):  # Skip empty lines and comments
                continue
            
            print(f"\n🔄 Processing action {i}/{len(lines)}")
            result = handler.process_goto_action(line)
            results.append(result)
            
            # Add small delay between requests to be respectful
            time.sleep(1)
        
        return results
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        return results


def process_actions_from_list(actions: List[str]) -> List[Dict]:
    """
    Process GOTO URL actions from a list.
    
    Args:
        actions (List[str]): List of action strings
        
    Returns:
        List[Dict]: Results of processing each action
    """
    results = []
    handler = ActionHandler()
    
    print(f"📋 Processing {len(actions)} actions from list")
    
    for i, action in enumerate(actions, 1):
        print(f"\n🔄 Processing action {i}/{len(actions)}")
        result = handler.process_goto_action(action)
        results.append(result)
        
        # Add small delay between requests
        time.sleep(1)
    
    return results


def create_batch_summary(results: List[Dict]) -> Dict:
    """
    Create a summary of batch processing results.
    
    Args:
        results (List[Dict]): List of action processing results
        
    Returns:
        Dict: Summary statistics
    """
    successful = [r for r in results if r.get("success", False)]
    failed = [r for r in results if not r.get("success", False)]
    
    total_selectors = 0
    for result in successful:
        if "selectors_count" in result:
            total_selectors += sum(result["selectors_count"].values())
    
    summary = {
        "total_actions": len(results),
        "successful_actions": len(successful),
        "failed_actions": len(failed),
        "success_rate": len(successful) / len(results) * 100 if results else 0,
        "total_selectors_extracted": total_selectors,
        "successful_urls": [r["url"] for r in successful],
        "failed_urls": [r["url"] for r in failed if "url" in r],
        "errors": [{"url": r.get("url", "unknown"), "error": r["error"]} for r in failed]
    }
    
    return summary


def print_batch_summary(summary: Dict, results: List[Dict]):
    """
    Print a detailed summary of batch processing.
    
    Args:
        summary (Dict): Summary statistics
        results (List[Dict]): Individual results
    """
    print(f"\n" + "="*70)
    print(f"📊 BATCH PROCESSING SUMMARY")
    print(f"="*70)
    print(f"Total Actions: {summary['total_actions']}")
    print(f"Successful: {summary['successful_actions']}")
    print(f"Failed: {summary['failed_actions']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Total Selectors Extracted: {summary['total_selectors_extracted']}")
    
    if summary['successful_actions'] > 0:
        print(f"\n✅ SUCCESSFUL ACTIONS:")
        successful_results = [r for r in results if r.get("success", False)]
        for i, result in enumerate(successful_results, 1):
            selectors_count = sum(result.get("selectors_count", {}).values())
            print(f"{i:2d}. {result['url']}")
            print(f"     File: {result.get('relative_path', 'N/A')}")
            print(f"     Selectors: {selectors_count}")
    
    if summary['failed_actions'] > 0:
        print(f"\n❌ FAILED ACTIONS:")
        for i, error in enumerate(summary['errors'], 1):
            print(f"{i:2d}. {error['url']}")
            print(f"     Error: {error['error']}")
    
    print(f"="*70)


def save_batch_results(results: List[Dict], summary: Dict, output_file: str = None):
    """
    Save batch processing results to a JSON file.
    
    Args:
        results (List[Dict]): Individual results
        summary (Dict): Summary statistics
        output_file (str): Output file path (optional)
    """
    if not output_file:
        timestamp = int(time.time())
        output_file = f"../extracted_data/batch_results_{timestamp}.json"
    
    batch_data = {
        "summary": summary,
        "timestamp": time.time(),
        "results": results
    }
    
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(batch_data, f, indent=4, ensure_ascii=False)
        print(f"💾 Batch results saved to: {output_file}")
    except Exception as e:
        print(f"❌ Error saving batch results: {e}")


def main():
    """
    Main function to demonstrate batch processing.
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python batch_action_processor.py <actions_file>")
        print("  python batch_action_processor.py --demo")
        print("\nExample actions file format:")
        print("  GOTO URL : https://example.com")
        print("  GO TO URL : https://httpbin.org/html")
        print("  https://www.google.com")
        print("  # This is a comment and will be skipped")
        sys.exit(1)
    
    if sys.argv[1] == "--demo":
        # Demo with predefined actions
        demo_actions = [
            "GOTO URL : https://example.com",
            "GO TO URL : https://httpbin.org/status/200",
            "https://www.w3.org"
        ]
        
        print("🎯 Running demo with sample actions...")
        results = process_actions_from_list(demo_actions)
        
    else:
        # Process from file
        actions_file = sys.argv[1]
        results = process_actions_from_file(actions_file)
    
    if not results:
        print("❌ No actions were processed")
        sys.exit(1)
    
    # Generate summary
    summary = create_batch_summary(results)
    
    # Print summary
    print_batch_summary(summary, results)
    
    # Save results
    save_batch_results(results, summary)
    
    print(f"\n🎉 Batch processing completed!")


if __name__ == "__main__":
    main()
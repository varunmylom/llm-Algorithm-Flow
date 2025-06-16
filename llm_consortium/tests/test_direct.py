#!/usr/bin/env python3

import sys
sys.path.insert(0, '.')

from llm_consortium import create_consortium

def test_pick_one_direct():
    print("=== Testing pick-one method directly ===")
    
    try:
        consortium = create_consortium(
            models=["gemini/gemini-1.5-flash-latest:2"],
            arbiter="gemini/gemini-1.5-flash-latest",
            judging_method="pick-one",
            max_iterations=1
        )
        
        result = consortium.orchestrate("What is 2+2?")
        print("Success! Result synthesis:", result.get("synthesis", {}).get("synthesis", "No synthesis"))
        print("Analysis:", result.get("synthesis", {}).get("analysis", "No analysis"))
        
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

def test_rank_direct():
    print("=== Testing rank method directly ===")
    
    try:
        consortium = create_consortium(
            models=["gemini/gemini-1.5-flash-latest:2"],
            arbiter="gemini/gemini-1.5-flash-latest",
            judging_method="rank",
            max_iterations=1
        )
        
        result = consortium.orchestrate("What is 3+3?")
        print("Success! Result synthesis:", result.get("synthesis", {}).get("synthesis", "No synthesis"))
        print("Analysis:", result.get("synthesis", {}).get("analysis", "No analysis"))
        
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pick_one_direct()
    print()
    test_rank_direct()

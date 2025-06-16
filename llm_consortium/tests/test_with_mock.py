#!/usr/bin/env python3

import sys
sys.path.insert(0, '.')

from llm_consortium import ConsortiumConfig, ConsortiumOrchestrator

def test_basic_functionality():
    print("=== Testing basic functionality ===")
    
    # Test that we can create a config with judging_method
    try:
        config = ConsortiumConfig(
            models={"test-model": 1},
            arbiter="test-model", 
            judging_method="pick-one"
        )
        print(f"✓ Config created with judging_method: {config.judging_method}")
        
        # Test that orchestrator gets the judging_method
        orchestrator = ConsortiumOrchestrator(config)
        print(f"✓ Orchestrator has judging_method: {orchestrator.judging_method}")
        
        # Test that the new methods exist
        if hasattr(orchestrator, '_parse_pick_one_response'):
            print("✓ _parse_pick_one_response method exists")
        else:
            print("✗ _parse_pick_one_response method missing")
            
        if hasattr(orchestrator, '_parse_rank_response'):
            print("✓ _parse_rank_response method exists")
        else:
            print("✗ _parse_rank_response method missing")
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_functionality()

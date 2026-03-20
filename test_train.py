
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

import config
from advanced.memory import MemorySystem
from core.personality import PersonalityEngine
from core.brain import BrainController

def test_train_keyword():
    print("--- Testing 'Train' Keyword ---")
    
    memory = MemorySystem()
    personality = PersonalityEngine(memory)
    brain = BrainController(memory, personality)
    
    # Test 1: "train that ..."
    input_text = "train that my favorite food is biryani"
    print(f"Input: '{input_text}'")
    result = brain.execute(input_text)
    
    print(f"Action: {result.get('action')}")
    print(f"Response: {result.get('response')}")
    
    if result.get('action') == "learn" and "biryani" in result.get('response', ''):
        print("SUCCESS: 'train that' pattern recognized and handled.")
    else:
        print("FAIL: 'train that' pattern not handled correctly.")
        print(f"Debug: {result}")

    # Test 2: "train ..."
    input_text = "train the password is 1234"
    print(f"\nInput: '{input_text}'")
    result = brain.execute(input_text)
    
    print(f"Action: {result.get('action')}")
    print(f"Response: {result.get('response')}")
    
    if result.get('action') == "learn" and "1234" in result.get('response', ''):
        print("SUCCESS: 'train' pattern recognized and handled.")
    else:
        print("FAIL: 'train' pattern not handled correctly.")

if __name__ == "__main__":
    test_train_keyword()

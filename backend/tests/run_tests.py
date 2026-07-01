import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from tests.test_escalation import (
    test_escalation_critical,
    test_escalation_high_fever,
    test_escalation_severe,
    test_escalation_low
)

def run_all_tests():
    print("Running backend tests...")
    
    try:
        test_escalation_critical()
        print("[PASS] test_escalation_critical")
        
        test_escalation_high_fever()
        print("[PASS] test_escalation_high_fever")
        
        test_escalation_severe()
        print("[PASS] test_escalation_severe")
        
        test_escalation_low()
        print("[PASS] test_escalation_low")
        
        print("\nAll tests completed successfully!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: Assertion Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()

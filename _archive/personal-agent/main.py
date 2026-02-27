import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from briefing.generator import generate_briefing

def main():
    print("[Jarvis Personal Agent Initializing...]\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--brief":
        print("--- Morning Briefing ---")
        print("-" * 30)
        
        briefing = generate_briefing()
        print("\n" + briefing + "\n")
        
        print("-" * 30)
    else:
        print("Usage: python main.py --brief")

if __name__ == "__main__":
    main()

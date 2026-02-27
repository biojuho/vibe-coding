import subprocess
import os
import sys

def launch_word_chain():
    """
    Launches the Word Chain game in a separate process.
    """
    # Calculate absolute path to the game's main.py
    # Assuming this file is in projects/personal-agent/tools/
    # And game is in projects/word-chain-pygame/
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # projects/personal-agent/tools -> projects/personal-agent -> projects -> projects/word-chain-pygame
    game_path = os.path.join(current_dir, "..", "..", "word-chain-pygame", "main.py")
    game_path = os.path.abspath(game_path)
    
    game_dir = os.path.dirname(game_path)
    
    if not os.path.exists(game_path):
        return False, f"Game file not found: {game_path}"

    try:
        # Run in separate process, independent of the agent
        if sys.platform == "win32":
            subprocess.Popen(["python", game_path], cwd=game_dir, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(["python3", game_path], cwd=game_dir)
            
        return True, "Word Chain Game Launched!"
    except Exception as e:
        return False, f"Failed to launch game: {e}"

if __name__ == "__main__":
    success, msg = launch_word_chain()
    print(msg)

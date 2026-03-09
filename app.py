import requests
import os
import shutil
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

def fetch_and_save_file(owner, repo, branch, path):
    """Fetches a single file from GitHub and saves it locally."""
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    try:
        response = requests.get(raw_url, timeout=10)
        if response.status_code == 200:
            save_path = os.path.join("scrapped", path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"  [+] Saved: {path}")
            return True
        else:
            print(f"  [!] Failed to fetch {path} (Status: {response.status_code})")
    except Exception as e:
        print(f"  [!] Error fetching {path}: {e}")
    return False

def get_repo_tree(owner, repo, branch="main"):
    """Fetches the repo tree and downloads target files in parallel."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    
    print(f"\n--- Fetching repository tree for {owner}/{repo} ({branch}) ---")
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Error fetching repo tree: {response.status_code}")
        return

    data = response.json()
    target_files = ["main.py", "app.py", "app.js", "main.js", "index.js", "server.js", "index.py", "server.py", "requirements.txt", "package.json", "Gemfile", "build.gradle", "config.yaml", "config.json", "settings.py", "settings.json"]
    excluded_dirs = ["venv", "node_modules", ".git", "__pycache__"]

    files_to_download = []
    for file in data.get("tree", []):
        path = file["path"]
        if any(excluded in path.split(os.sep) for excluded in excluded_dirs):
            continue
        if any(path.endswith(name) for name in target_files):
            files_to_download.append(path)

    if not files_to_download:
        print("No matching files found.")
        return

    print(f"Found {len(files_to_download)} files. Downloading in parallel...\n")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(lambda p: fetch_and_save_file(owner, repo, branch, p), files_to_download))

def load_scrapped_code(folder="scrapped"):
    """Loads all scrapped code into a single string."""
    combined_text = ""
    if not os.path.exists(folder):
        return ""
        
    for root, _, files in os.walk(folder):
        for file in files:
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    combined_text += f"\n\n--- FILE: {path} ---\n{content}"
            except Exception:
                pass
    return combined_text

def run_interview():
  
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n[!] Error: GOOGLE_API_KEY environment variable not set.")
        # Fallback for api key
        api_key = input("Please enter your Gemini API Key: ").strip()
        if not api_key:
            return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3-flash-preview") # Using a stable model name

    # 2. GitHub Input
    username = input("Enter GitHub username: ").strip()
    reponame = input("Enter repository name: ").strip()
    branchname = input("Enter branch name (default: main): ").strip() or "main"

    try:
        # 3. Scrapping
        get_repo_tree(username, reponame, branchname)
        repo_code = load_scrapped_code()

        if not repo_code:
            print("No code was retrieved. Exiting.")
            return

     
        print("\n--- Starting Interview with Gemini ---\n")
        
        system_instruction = (
            "You are an expert technical interviewer. You have been provided with the source code of a GitHub repository. "
            "Your goal is to conduct a 5-question interview with the user to understand their knowledge of the codebase and technical decisions. "
            "Ask one question at a time. The first question should be based on the provided code. "
            "Subsequent questions should build upon the user's answers and the code."
        )
        
        chat = model.start_chat(history=[])
        
        
        initial_prompt = f"{system_instruction}\n\nHere is the repository code:\n{repo_code}\n\nPlease ask the first question."
        response = chat.send_message(initial_prompt)
        
        print(f"Interviewer: {response.text}\n")

        for i in range(4):
            answer = input("Your answer: ")
            if not answer.strip():
                print("Interviewer: I didn't get an answer. Could you please provide one?")
                answer = input("Your answer: ")
            
            response = chat.send_message(answer)
            print(f"\nInterviewer: {response.text}\n")

        print("--- Interview Finished ---")
        print("Thanks for using the tool!")

    finally:
        # deleting scrapped folder
        if os.path.exists("scrapped"):
            shutil.rmtree("scrapped", ignore_errors=True)
            print("\n[clean] Temporary files removed.")

if __name__ == "__main__":
    run_interview()

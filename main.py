import streamlit as st
import requests
import re
import base64
import google.generativeai as genai

# Set your Gemini API key
genai.configure(api_key="AIzaSyB1wWGzrMgbJKN6wXCF7WS53bZ9cUpfHwM")

# Load Gemini model (using gemini-2.5-pro-preview-05-06)
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

st.set_page_config(page_title="GitMe", page_icon=":technologist:", layout="wide")
st.title("GitMe: Create ReadMe in a single Ctrl C,V")
st.markdown('<hr style="border: solid 2px blue; box-shadow: 0 0 5px blue;" />', unsafe_allow_html=True)

col1, col2 = st.columns([0.4, 0.6])

def get_github_repo_info(user, repo):
    url = f"https://api.github.com/repos/{user}/{repo}"
    r = requests.get(url)
    return r.json() if r.status_code == 200 else None

def get_repo_file_tree(user, repo):
    url = f"https://api.github.com/repos/{user}/{repo}/git/trees/HEAD?recursive=1"
    r = requests.get(url)
    return r.json() if r.status_code == 200 else None

from urllib.parse import urlparse

def extract_github_info(repo_url):
    try:
        parsed_url = urlparse(repo_url)
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) >= 2:
            username = path_parts[0]
            repo_name = path_parts[1].replace(".git", "")
            return username, repo_name
        else:
            return None, None
    except Exception as e:
        return None, None

def get_file_content(user, repo, path):
    url = f"https://api.github.com/repos/{user}/{repo}/contents/{path}"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json()
    if data.get("encoding") == "base64":
        content = base64.b64decode(data["content"]).decode('utf-8', errors='ignore')
        return content
    return None

def generate_readme_with_gemini(files_data, repo_url, username, repo_name):
    prompt = f"""
Generate a professional and detailed README.md file for the GitHub repository located at {repo_url} owned by user `{username}` with repository name `{repo_name}`.

### Instructions:
- Include appropriate **emojis** only in section headers to keep it visually appealing but clean.
- Add **badges** only for the technologies actually used in the project (detect from files content: e.g., Python, Streamlit, NLTK, matplotlib, pandas, etc.).
- Start with a clear project title and a concise tagline.
- Add a **Description** section that clearly explains the purpose and functionality of the project.
- Include an **Installation** section with code blocks for cloning and dependency installation.
- Provide a **Usage and Features** section describing main functionalities.
- List the **Technologies Used** with relevant badges only.
- Include a **Future Enhancements** section with a few realistic ideas and minimal emojis.
- Add a **Contributing** section welcoming contributions.
- Do **not** mention or include any License section.
- Use markdown formatting properly, limit snippets to 300 characters max with ellipsis if including code snippets.

### Project Files Snippets:
"""

    for filename, content in files_data.items():
        snippet = content[:300].replace('\n', ' ') + " ..."
        prompt += f"\nFilename: `{filename}`\nSnippet: {snippet}\n"

    prompt += "\nNow generate the README.md content in markdown:"
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"Error generating README: {e}")
        return ""


with col1:
    with st.container(border=True):
        st.subheader("Paste the URL of the Github Repo below:")
        repo_url = st.text_input("", placeholder="Paste here")

        if st.button("Generate README.md"):
            if not repo_url.strip():
                st.warning("Please enter a GitHub repository URL!")
            else:
                pattern = r'https://github\.com/([\w\-]+)/([\w\-]+)'
                match = re.match(pattern, repo_url.strip())
                if not match:
                    st.warning("Invalid GitHub repository URL! Example: https://github.com/user/repo")
                else:
                    user, repo = match.groups()

                    repo_info = get_github_repo_info(user, repo)
                    if not repo_info or repo_info.get("private"):
                        st.warning("Repository not found or not accessible (private?). Please use a public repo.")
                    else:
                        tree = get_repo_file_tree(user, repo)
                        if not tree:
                            st.warning("Failed to get repository file list.")
                        else:
                            files_to_fetch = []
                            for item in tree.get("tree", []):
                                path = item.get("path", "")
                                if item.get("type") == "blob" and path.endswith(('.py','.md','.txt','.json','.yaml','.yml','.java','.js')):
                                    files_to_fetch.append(path)
                                if len(files_to_fetch) >= 10:
                                    break

                            files_data = {}
                            for fpath in files_to_fetch:
                                content = get_file_content(user, repo, fpath)
                                if content:
                                    files_data[fpath] = content

                            un, rn = extract_github_info(repo_url)
                            readme_md = generate_readme_with_gemini(files_data, repo_url, un, rn)

                            # Display generated README
                            col2.subheader("Generated README.md")
                            col2.text_area("", readme_md, height=400)
                            col2.download_button(
                                label="Download README.md",
                                data=readme_md,
                                file_name="README.md",
                                mime="text/markdown"
                            )

                            # Display filenames line by line below the button
                            st.markdown("### Files fetched from the repository:")
                            for filename in files_to_fetch:
                                st.markdown(f"- `{filename}`")

# My RAG Lab

A small RAG (Retrieval-Augmented Generation) app built with Python and Streamlit. You put your own documents in a folder, ask questions, and change parameters (chunk size, overlap, top-k, temperature, strict mode) to see how the answers change.

How it works, in order:

1. Load documents from `docs/`
2. Chunking (cut text into pieces)
3. Embeddings (turn each chunk into numbers)
4. Vector database (ChromaDB stores the numbers)
5. Retrieval (find the chunks closest to your question)
6. Augmentation (put the chunks and the question into one prompt)
7. LLM (Gemini writes the answer)
8. You see the answer, the chunks used, the timings and the full prompt

## Project structure

```
rag-lab/
  app.py                 the whole app
  requirements.txt       list of Python packages
  .gitignore             files Git must NOT upload (keys, logs, venv)
  docs/                  your PDFs, .txt and .md files go here
  .streamlit/
    secrets.toml         your API key (the folder name MUST start with a dot)
  .venv/                 private Python packages for this project (auto-created)
  logs.jsonl             created automatically, one line per question asked
```

---

## A. Run it again (every normal day)

You do NOT need to install anything again. Just do this:

1. Open VS Code, then File, then Open Folder, and choose `D:\rag-lab`.
2. Open the terminal: Terminal menu, then New Terminal.
3. Activate the virtual environment:
   ```
   .venv\Scripts\Activate.ps1
   ```
   You must see `(.venv)` at the start of the line. If you don't, the next step will fail.
4. Start the app:
   ```
   streamlit run app.py
   ```
5. Your browser opens at http://localhost:8501. If it doesn't, open that address yourself.
6. To stop the app, click the terminal and press `Ctrl + C`.

If you made a code change and the page shows "Source file changed", click "Rerun" (or "Always rerun").

---

## B. First-time setup (only once, or on a new PC)

### 1. Install these
| Program | Where | Note |
|---|---|---|
| Python 3.11 or 3.12 (newer versions may also work) | python.org/downloads | Tick "Add python.exe to PATH" on the first screen |
| Git | git-scm.com | Keep the default options |
| VS Code | code.visualstudio.com | Any editor works |

Check in PowerShell:
```
python --version
git --version
```

### 2. Get the project
If it is on GitHub:
```
cd D:\
git clone https://github.com/YOUR-USERNAME/rag-lab.git
cd rag-lab
```
If you already have the folder, just `cd D:\rag-lab`.

### 3. Create the virtual environment and install packages
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
If PowerShell says scripts are disabled, run this once, then retry:
```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 4. Add your API key
1. Get a key at https://aistudio.google.com (API keys).
2. Create a folder named exactly `.streamlit` (with the dot) in the project.
3. Inside it, create a file named `secrets.toml` with this one line:
   ```
   GEMINI_API_KEY = "paste-your-key-here"
   ```
4. Never share this file, never post a screenshot of it, never upload it to GitHub. If a key is ever exposed, delete it in AI Studio and create a new one.

### 5. Add your documents
Put 2 or 3 files (`.pdf`, `.txt` or `.md`) in the `docs/` folder. Use documents you know well so you can judge if the answers are correct.

Then follow Section A to run it.

---

## C. What each slider does

| Slider | What it controls | What to watch |
|---|---|---|
| Chunk size (words) | How big each piece of your document is | Too small: answers get cut in half. Too big: chunks get noisy and the right one may rank low |
| Overlap (words) | How many words repeat between neighbouring chunks | Helps when a fact sits on a chunk boundary |
| Top-k | How many chunks are sent to the LLM | Too low: facts are missed. Too high: slower, vaguer answers |
| Temperature | How adventurous the LLM is | 0.0 to 0.3 for facts, higher for creative text |
| Strict mode | Tells the LLM to answer only from the context | Turn off, then ask something not in your documents, and watch it make things up |

Changing chunk size or overlap re-embeds your documents the first time (this uses API quota). Going back to a size you used before is instant, because it is cached.

---

## D. How to run experiments

1. Write 10 questions about your documents, with the correct answer for each.
2. Ask all 10 at one setting. Count how many are fully correct.
3. Change ONE slider, ask the same 10 again, and count again.
4. Keep a table:

| Chunk size | Overlap | Top-k | Temp | Correct out of 10 | Notes |
|---|---|---|---|---|---|
| 120 | 20 | 3 | 0.2 | | |

5. When an answer is wrong, open "Retrieved chunks" first:
   - Right chunk missing: retrieval problem (try bigger top-k, different chunk size, more overlap)
   - Right chunk present but answer wrong or incomplete: LLM or prompt problem (lower temperature, improve the prompt in the `answer` function)
6. Every question is saved in `logs.jsonl` with its settings, chunks, timings and answer. You can open it in VS Code to compare runs.

---

## E. Deploy (get a public link)

### First time
1. Create an empty repository on github.com (for example `rag-lab`).
2. In the project terminal:
   ```
   git init
   git add .
   git commit -m "first version"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/rag-lab.git
   git push -u origin main
   ```
3. On GitHub, check that `.streamlit/secrets.toml` is NOT in the repository.
4. Go to https://share.streamlit.io and sign in with GitHub.
5. Click "Create app", choose your repository, branch `main`, main file `app.py`.
6. Open "Advanced settings", and in Secrets paste:
   ```
   GEMINI_API_KEY = "your-key"
   ```
7. Click Deploy. After a few minutes you get a link ending in `.streamlit.app`.

### After you change the code
```
git add .
git commit -m "describe what you changed"
git push
```
Streamlit Cloud redeploys automatically.

Remember: if the repository is public, everything inside it (including the files in `docs/`) is public. Use sample documents for the deployed version.

---

## F. Troubleshooting

| Problem | Cause and fix |
|---|---|
| App says no GEMINI_API_KEY found | The folder must be named `.streamlit` with a dot at the start, and the file `secrets.toml` inside it. Restart the app after fixing. |
| `ModuleNotFoundError` | The virtual environment is not active. Run `.venv\Scripts\Activate.ps1`, then `pip install -r requirements.txt`. |
| PowerShell: running scripts is disabled | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. |
| 404 NOT_FOUND, model no longer available | Google retired the model name. Change `LLM_MODEL` (and `EMBED_MODEL` if needed) at the top of `app.py` to a current model name from AI Studio. |
| 503 UNAVAILABLE, high demand | Google's server is busy. Wait a minute and ask again. Adding a retry function (`generate_with_retry`) to `app.py` makes the app retry automatically. |
| 429 quota or rate limit | Free-tier limit reached. Wait a minute, use fewer or smaller documents, and avoid changing chunk size too often. |
| Page shows "No documents" warning | The `docs/` folder is empty or has unsupported file types. Add `.pdf`, `.txt` or `.md` files and refresh. |
| PDF answers look empty or strange | Scanned PDFs (images) have no text to read. Use PDFs where you can select and copy the text. |
| Deploy fails on sqlite3 | Make sure `requirements.txt` contains the line `pysqlite3-binary; sys_platform == "linux"` and `app.py` begins with the pysqlite3 swap lines. |
| `git push` asks who you are | Run `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`. |

---

## G. Ideas for next steps

- Add a "compare two settings side by side" view
- Add an input guardrail (block prompt-injection like "ignore all previous instructions")
- Add an output check: a second LLM call that verifies the answer is supported by the chunks
- Connect Langfuse or Arize Phoenix for proper tracing
- Turn it into an agent: give the LLM tools (search, calculator) and let it loop

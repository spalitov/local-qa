# HOW TO USE THIS PROJECT

This project checks the quality of the **last agent reply** in a chat and gives a score report.

## 1. Prepare your computer once
1. Install Python (version 3.10 or newer).
2. Install Ollama.
3. Open Ollama once so it is running in the background.
4. Download the model used by this project:
   - `ollama run llama3.1:8b`

## 2. Set up the project
1. Open a terminal in this project folder.
2. Create a virtual environment:
   - `python -m venv .venv`
3. Activate it:
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`
4. Install project packages:
   - `pip install -r requirements.txt`

## 3. Run an audit with JSON input
1. Use the sample file:
   - `python scripts/run_audit.py examples/input.json`
2. You will get a JSON result in the terminal with local checks and LLM checks.

## 4. Run an audit with CSV input
The CSV can contain many conversations. This project audits one row at a time.

1. Audit the full file:
   - `python scripts/run_audit.py examples/input.csv`
2. Audit a specific row number:
   - `python scripts/run_audit.py examples/input.csv --row 2`
3. Audit a specific conversation ID (`SEND_ID` in the CSV):
   - `python scripts/run_audit.py examples/input.csv --send-id 0192d5dd-50f3-46a9-f000-00009aac14d9`

## 5. Understand the result
1. `local` scores are strict checks done by local code (grammar, typos, repetition).
2. `llm` scores are tone and content checks done by the LLM.
3. `finding` is a one-sentence summary of the main quality issue (or why it passed).

## 6. If something fails
1. Make sure Ollama is running.
2. Make sure the model exists (`ollama list`).
3. Make sure your input has at least one `agent` message in the conversation.
4. For CSV, ensure these columns exist: `SEND_ID`, `MESSAGE_TONE`, `CONVERSATION_JSON`, `BLOCKLISTED_WORDS`.

# Email Classifier

A Python tool that reads unread emails from Gmail, classifies them into user-defined categories, and moves them into matching Gmail labels.

## Disclaimer

This project is a technical prototype.

It works end-to-end:
- it connects to Gmail
- reads unread emails
- extracts and cleans their content
- classifies them
- moves them into labels

However, the classification quality is currently poor. The results can feel random or inconsistent, depending on the emails and the category descriptions. It should not be considered reliable for real-world use without further improvement.

## What it does

The project connects to a Gmail account, loads unread emails from the inbox, extracts the sender, subject, and body, and compares each email against a list of configured categories.

If a category matches strongly enough, the email is moved to that Gmail label. If no category reaches the minimum score, the email is moved to a default label instead.

## Features

- Connects to Gmail through the Gmail API
- Reads unread emails from the inbox
- Extracts and cleans email text
- Creates missing Gmail labels automatically
- Classifies emails into custom categories
- Moves emails into the selected label
- Includes two classification approaches:
  - **Embedding-based classification** using `intfloat/e5-large-v2`
  - **NLI-based classification** using `facebook/bart-large-mnli`

## How it works

The processing flow is:

1. Load the project config
2. Connect to Gmail
3. Create missing labels if needed
4. Read unread emails from the inbox
5. Extract:
   - sender
   - subject
   - body
6. Clean the text
7. Compare the email against all configured categories
8. Pick the best category above a confidence threshold
9. Move the email to the matching Gmail label

If no category passes the minimum score, the email is moved to the default category.

## Current default classifier

The current version is intended to use the **embedding pipeline** by default.

At the bottom of `src/main.py`, only one of these lines should be active:

```python
run_embeddings()
# run_nli()
```

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/BenScheid/email-classifier-public.git
cd email-classifier-public
```
### 2. Create Gmail OAuth credentials

Before running the project, you need to create OAuth credentials for the Gmail API.

Go to:

https://console.cloud.google.com/apis/credentials

Then:

1) Create or select a Google Cloud project.
2) Enable the Gmail API
3) Create OAuth client credentials for a Desktop app.
4) Download the credentials file

### 3. Run the setup script

The repository includes a setup script that creates the virtual environment, installs dependencies, creates the required folders, and can also copy your Gmail credentials file automatically into the correct location. Make sure to include all necessary flags for your case. They can be listed with --help or -h flag.

You can run it like this in the project root directory:
- on Linux/MACOS:
```
./unix-setup.sh --help
```
- on Windows (NOT AVAILABLE YET):
```
powershell -ExecutionPolicy Bypass -File .\windows-setup.ps1
```
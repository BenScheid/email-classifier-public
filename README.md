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

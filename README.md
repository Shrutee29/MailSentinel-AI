# Email Analysis & Prioritization

This project analyzes the supplied 40 synthetic email PDFs and produces a consistent result for each email:

- Spam / Not Spam
- Valid / Invalid sender information
- High / Medium / Low importance
- Evidence-based reason for every classification

The app is local and explainable. It uses PDF text extraction plus transparent rules for suspicious content, sender validity, urgency, business impact, and action required. It does not call an external email service or LLM.

## Run

From this folder:

```powershell
C:\Users\shrut\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.txt
C:\Users\shrut\AppData\Local\Programs\Python\Python312\python.exe -m streamlit run app.py
```

The app starts with the dataset folder pre-filled:

`C:\Users\shrut\Downloads\Emails_Dataset-20261010T064922Z-1-001\Emails_Dataset`

You can also upload a different set of PDF files from the sidebar. Results can be downloaded as CSV.

## Tests

```powershell
C:\Users\shrut\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q
```

## Accuracy review

The supplied PDFs do not include ground-truth labels, so the application does not
claim an accuracy percentage from predictions alone. Use
[classification_labels_template.csv](./classification_labels_template.csv) to
manually review each email and fill in:

- `expected_spam_status`: `Spam` or `Not Spam`
- `expected_validity`: `Valid` or `Invalid`
- `expected_importance`: `High`, `Medium`, or `Low`
- `review_notes`: evidence supporting the label

The `evaluate_labels` function in `email_analyzer.py` computes accuracy only for
rows with all three expected labels completed. Blank rows are excluded from the
denominator, so partial review cannot produce a misleading accuracy score.

## Sender context

Sender `validity` means only that the address has a structurally valid email
format. `sender_identity` remains `Unverified` unless the observable message
context shows a possible mismatch. The analyzer reports, without asserting
spoofing:

- a Reply-To domain different from the sender domain;
- a high-risk display name such as Support, Security, Billing, or Account that
  does not align with the sender domain;
- missing or malformed sender addresses.

External identity, domain reputation, and SPF/DKIM/DMARC cannot be verified from
the supplied PDF exports.

The dashboard exposes these Step 3 fields in the **Inspect an email** section:
`Reply-To`, `Sender identity`, and `Sender context`.

## Importance scoring

Importance is assigned from combined evidence rather than a single urgency word:

- **High** requires a critical incident or a combination of consequence
  (security or financial impact) and urgency/action required.
- **Medium** covers actionable, financial, urgent, or business-relevant messages
  without confirmed critical consequences.
- **Low** is used when no strong urgency, business impact, security risk, or
  required action is present.

This prevents newsletter language such as “urgent” from becoming High priority
without evidence of operational, security, financial, or customer impact.

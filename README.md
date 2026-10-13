# 📧 MailSentinel AI — Email Analysis & Prioritization

MailSentinel AI is a Python-based web application that analyzes PDF email documents to identify suspicious content, assess sender validity, and prioritize emails based on urgency, business impact, security risk, and required action.

The application provides explainable analysis results through an interactive Streamlit dashboard.

**🚀 Live Demo:** [MailSentinel AI](https://mailsentinel-ai-im2xyumlkwv99zkdanesjv.streamlit.app/)

**📂 GitHub Repository:** [MailSentinel-AI](https://github.com/Shrutee29/MailSentinel-AI)

---

## ✨ Features

- **PDF Email Analysis:** Analyze email documents from a dataset folder or upload PDF files.
- **Spam and Suspicious Content Detection:** Identify potentially promotional or suspicious emails.
- **Sender Validation:** Assess sender addresses and contextual indicators.
- **Email Prioritization:** Evaluate urgency, business impact, security risk, financial impact, and required action.
- **Explainable Results:** Display reasons supporting email classifications and importance levels.
- **Interactive Dashboard:** View email summaries, classification results, and analysis statistics.
- **Follow-up Assistance:** Generate follow-up suggestions based on email context.
- **CSV Export:** Export analysis results for further review.

## 🛠️ Tech Stack

- Python
- Streamlit
- Pandas
- PDF processing libraries
- Pytest
- Git and GitHub
- Streamlit Community Cloud

## 📁 Project Structure

```text
MailSentinel-AI/
├── app.py
├── email_analyzer.py
├── test_email_analyzer.py
├── requirements.txt
├── README.md
├── classification_labels_template.csv
├── .gitignore
├── .streamlit/
│   └── config.toml
└── Emails_Dataset/
    └── PDF email documents
```

### Main Files

- `app.py` — Streamlit application and dashboard.
- `email_analyzer.py` — Email analysis and classification logic.
- `test_email_analyzer.py` — Automated tests.
- `requirements.txt` — Project dependencies.
- `classification_labels_template.csv` — Classification-label template.
- `Emails_Dataset/` — Sample PDF email dataset.
- `.streamlit/config.toml` — Streamlit configuration.

## ⚙️ Installation and Setup

### Prerequisites

- Python installed on your system.
- Git installed on your system.
- Visual Studio Code or another Python IDE.

### 1. Clone the repository

```bash
git clone https://github.com/Shrutee29/MailSentinel-AI.git
cd MailSentinel-AI
```

### 2. Create a virtual environment

For Windows:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the application

```bash
python -m streamlit run app.py
```

Open the local URL shown in the terminal, usually:

`http://localhost:8501`

## 📊 How to Use

1. Launch the application.
2. Select the dataset folder containing PDF email documents or upload PDF emails.
3. Click **Analyze emails**.
4. Review the dashboard summary and analysis results.
5. Examine spam status, sender validity, email importance, and the associated explanations.
6. Use the available follow-up and export features where applicable.

## 🧪 Testing

Run the automated test suite:

```bash
python -m pytest -v
```

The project has reported 15 passing tests and successful processing of 40 sample PDF emails in its validation output.

## 🔒 Privacy

The application processes email documents within the environment where it runs. When using the hosted Streamlit Cloud version, uploaded documents are processed in the hosted environment rather than exclusively on the user's computer.

Avoid uploading confidential emails to a public deployment unless its data handling and access controls are appropriate.

## 🎯 Project Objective

MailSentinel AI aims to simplify email review by combining suspicious-content detection, sender validation, explainable classification, and importance-based prioritization in one interface.

## 👩‍💻 Author

**Shrutee Gonnade**

- GitHub: [Shrutee29](https://github.com/Shrutee29)

## 📄 License

No open-source license has been specified for this repository. Add a `LICENSE` file if you decide to distribute the project under an open-source license.

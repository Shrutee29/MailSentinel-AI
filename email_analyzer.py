"""Local email extraction and prioritization for the Email Analysis app."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO, Iterable, Mapping

import pymupdf


EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
HEADER_PATTERN = re.compile(
    r"^(?P<key>from|to|cc|subject|date)\s*:\s*(?P<value>.*)$",
    re.IGNORECASE | re.MULTILINE,
)

HIGH_IMPORTANCE_TERMS = (
    "production outage",
    "security incident",
    "data breach",
    "payment failure",
    "customer escalation",
    "service unavailable",
    "database failure",
    "system down",
    "account compromised",
)
SECURITY_RISK_TERMS = (
    "security incident",
    "data breach",
    "account compromised",
    "unauthorized access",
    "customer data",
)
FINANCIAL_IMPACT_TERMS = (
    "payroll",
    "payment failure",
    "financial loss",
    "invoice overdue",
    "fraud",
)
URGENCY_TERMS = (
    "urgent",
    "immediately",
    "deadline today",
    "as soon as possible",
    "service unavailable",
)
ACTION_REQUIRED_TERMS = (
    "action required",
    "action advised",
    "approval",
    "deadline",
    "must review",
    "requires action",
)
MEDIUM_IMPORTANCE_TERMS = (
    "action required",
    "approval",
    "invoice",
    "renewal",
    "incident",
    "follow up",
    "meeting",
    "review",
    "deadline",
)
STRONG_SPAM_TERMS = (
    "you have won",
    "you are a winner",
    "claim your prize",
    "free gift",
    "you have been selected",
    "wire transfer",
    "gift card",
    "urgent payment",
    "login immediately",
    "verify your account",
)
SUSPICIOUS_REQUEST_TERMS = (
    "password",
    "sensitive information",
    "attachment enabled",
    "bank details",
    "credit card",
)
PROMOTIONAL_TERMS = (
    "limited time offer",
    "discount",
    "sale",
    "coupon",
    "off on",
    "apply today",
    "wager",
    "buy now",
)
NEWSLETTER_MARKERS = (
    "substack",
    "beehiiv",
    "newsletter",
    "read in app",
    "upgrade to paid",
    "unsubscribe",
    "terms of service",
    "terms of use",
    "privacy policy",
)
DISPLAY_RISK_TERMS = (
    "support",
    "security",
    "billing",
    "account",
    "bank",
    "administrator",
    "payroll",
)


@dataclass(frozen=True)
class EmailAnalysis:
    email_id: str
    filename: str
    sender: str
    reply_to: str
    recipient: str
    subject: str
    date: str
    spam_status: str
    validity: str
    sender_identity: str
    sender_context: str
    importance: str
    score: int
    reason: str
    text: str

    def as_row(self) -> dict[str, object]:
        row = asdict(self)
        row.pop("text")
        return row


@dataclass(frozen=True)
class EvaluationReport:
    reviewed_count: int
    total_count: int
    spam_accuracy: float | None
    validity_accuracy: float | None
    importance_accuracy: float | None


def evaluate_labels(
    analyses: Iterable[EmailAnalysis],
    expected: Mapping[str, Mapping[str, str]],
) -> EvaluationReport:
    """Compare reviewed labels with predictions without treating blanks as labels."""
    records = list(analyses)
    if not records:
        return EvaluationReport(0, 0, None, None, None)

    fields = ("spam_status", "validity", "importance")
    reviewed = [
        record for record in records
        if record.email_id in expected
        and all(expected[record.email_id].get(field, "").strip() for field in fields)
    ]
    for record_id, labels in expected.items():
        unknown = set(labels) - set(fields)
        if unknown:
            raise ValueError(f"Unsupported label fields for {record_id}: {sorted(unknown)}")
        for field in fields:
            value = labels.get(field, "").strip()
            if value and value not in {
                "spam_status": {"Spam", "Not Spam"},
                "validity": {"Valid", "Invalid"},
                "importance": {"High", "Medium", "Low"},
            }[field]:
                raise ValueError(f"Invalid {field} label for {record_id}: {value}")

    def accuracy(field: str) -> float | None:
        if not reviewed:
            return None
        return sum(
            getattr(record, field) == expected[record.email_id][field].strip()
            for record in reviewed
        ) / len(reviewed)

    return EvaluationReport(
        reviewed_count=len(reviewed),
        total_count=len(records),
        spam_accuracy=accuracy("spam_status"),
        validity_accuracy=accuracy("validity"),
        importance_accuracy=accuracy("importance"),
    )


def extract_pdf_text(data: bytes) -> str:
    """Extract text from a PDF, preserving page boundaries."""
    document = pymupdf.open(stream=data, filetype="pdf")
    try:
        return "\n".join(page.get_text("text") for page in document).strip()
    finally:
        document.close()


def _header(text: str, name: str) -> str:
    match = re.search(
        rf"^{re.escape(name)}\s*:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE
    )
    return match.group(1).strip() if match else ""


def _terms_found(text: str, terms: Iterable[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term in lowered]


def _sender_is_valid(sender: str, text: str) -> bool:
    address = EMAIL_PATTERN.search(sender)
    if not address:
        return False
    local, domain = address.group(0).lower().split("@", 1)
    return (
        len(local) > 0
        and "." in domain
        and not domain.startswith(".")
        and not domain.endswith(".")
    )


def _sender_domain(address: str) -> str:
    match = EMAIL_PATTERN.search(address)
    return match.group(0).rsplit("@", 1)[-1].lower() if match else ""


def _reply_to(text: str) -> str:
    value = _header(text, "Reply-To")
    value_address = EMAIL_PATTERN.search(value)
    if value_address:
        return value_address.group(0)
    match = re.search(
        r"Reply-To\s*:\s*[\s\S]{0,300}?(" + EMAIL_PATTERN.pattern + ")",
        text,
        re.IGNORECASE,
    )
    return match.group(1) if match else ""


def _sender_display_name(text: str, sender: str) -> str:
    address = EMAIL_PATTERN.search(sender)
    if not address:
        return ""
    for line in text.splitlines():
        if address.group(0).lower() in line.lower() and "<" in line:
            return line.split("<", 1)[0].strip().strip('"')
    return ""


def _sender_context(text: str, sender: str, reply_to: str) -> tuple[str, str]:
    """Assess observable sender context; this does not authenticate identity."""
    sender_domain = _sender_domain(sender)
    reply_domain = _sender_domain(reply_to)
    display_name = _sender_display_name(text, sender)
    if reply_to and reply_domain != sender_domain:
        return (
            "Potential mismatch",
            f"Reply-To domain {reply_domain} differs from sender domain {sender_domain}",
        )
    display_words = set(re.findall(r"[a-z0-9]+", display_name.lower()))
    domain_words = set(re.findall(r"[a-z0-9]+", sender_domain))
    risk_words = display_words & set(DISPLAY_RISK_TERMS)
    brand_mismatch = risk_words and not (risk_words & domain_words)
    if brand_mismatch and display_name:
        return (
            "Potential mismatch",
            f"display name '{display_name}' does not match sender domain {sender_domain}",
        )
    return ("Unverified", "sender format is valid, but identity was not externally verified")


def analyze_email(email_id: str, filename: str, text: str) -> EmailAnalysis:
    addresses = list(dict.fromkeys(EMAIL_PATTERN.findall(text)))
    sender = _header(text, "From")
    reply_to = _reply_to(text)
    recipient = _header(text, "To")
    subject = _header(text, "Subject")
    date = _header(text, "Date")
    if not recipient and addresses:
        recipient = addresses[0]
    if not sender and len(addresses) > 1:
        sender = addresses[1]
    if not subject:
        nonempty_lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(nonempty_lines) > 1 and not EMAIL_PATTERN.search(nonempty_lines[1]):
            subject = nonempty_lines[1]
    if not date:
        date_match = re.search(
            r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b", text
        )
        date = date_match.group(0) if date_match else ""
    sender = sender or "Unknown sender"
    recipient = recipient or "Unknown recipient"
    subject = subject or "(No subject)"
    date = date or "Unknown date"
    context = f"{subject}\n{text}".lower()
    strong_spam_terms = _terms_found(context, STRONG_SPAM_TERMS)
    suspicious_request_terms = _terms_found(context, SUSPICIOUS_REQUEST_TERMS)
    promotional_terms = _terms_found(context, PROMOTIONAL_TERMS)
    newsletter_markers = _terms_found(
        f"{sender}\n{subject}\n{text}", NEWSLETTER_MARKERS
    )
    high_terms = _terms_found(context, HIGH_IMPORTANCE_TERMS)
    security_terms = _terms_found(context, SECURITY_RISK_TERMS)
    financial_terms = _terms_found(context, FINANCIAL_IMPACT_TERMS)
    urgency_terms = _terms_found(context, URGENCY_TERMS)
    action_terms = _terms_found(context, ACTION_REQUIRED_TERMS)
    medium_terms = _terms_found(context, MEDIUM_IMPORTANCE_TERMS)
    sender_format_valid = _sender_is_valid(sender, text)
    sender_identity, sender_context = _sender_context(text, sender, reply_to)

    # Routine newsletters and policy notices are not spam merely because they
    # contain unsubscribe links, calls to read more, or paid-subscription copy.
    deceptive_request = (
        len(suspicious_request_terms) >= 2
        or ("verify your account" in context and "password" in context)
        or ("urgent payment" in context and "bank details" in context)
    )
    unsolicited_promotion = bool(promotional_terms) and not newsletter_markers
    sender_mismatch = sender_identity == "Potential mismatch"
    spam = (
        bool(strong_spam_terms)
        or deceptive_request
        or unsolicited_promotion
        or sender_mismatch and deceptive_request
    )
    spam_status = "Spam" if spam else "Not Spam"
    validity = "Valid" if sender_format_valid else "Invalid"

    critical_incident = bool(high_terms)
    high_consequence = (
        bool(security_terms or financial_terms)
        and bool(urgency_terms or action_terms)
    )
    high_importance = critical_incident or high_consequence
    if high_importance:
        importance = "High"
        score = 3
    elif medium_terms or urgency_terms or action_terms or financial_terms:
        importance = "Medium"
        score = 2
    else:
        importance = "Low"
        score = 1

    evidence: list[str] = []
    if strong_spam_terms:
        evidence.append(f"deceptive or unsolicited indicators: {', '.join(strong_spam_terms[:3])}")
    if deceptive_request:
        evidence.append(f"suspicious requests: {', '.join(suspicious_request_terms[:3])}")
    if unsolicited_promotion:
        evidence.append(
            "promotional content without newsletter or routine-notification context: "
            + ", ".join(promotional_terms[:3])
        )
    if newsletter_markers and not spam:
        evidence.append("newsletter or routine-notification context; unsubscribe language alone is not spam")
    if not sender_format_valid:
        evidence.append("sender address is missing or has invalid format")
    else:
        evidence.append(sender_context)
    if reply_to and sender_identity == "Potential mismatch":
        evidence.append("reply-to routing differs from the visible sender")
    if high_importance:
        importance_evidence = (
            high_terms + security_terms + financial_terms + urgency_terms + action_terms
        )
        evidence.append(
            "high-impact evidence: "
            + ", ".join(list(dict.fromkeys(importance_evidence))[:4])
        )
    elif medium_terms:
        evidence.append(f"action or business evidence: {', '.join(medium_terms[:3])}")
    elif urgency_terms or action_terms or financial_terms:
        evidence.append(
            "moderate importance evidence: "
            + ", ".join(
                list(dict.fromkeys(urgency_terms + action_terms + financial_terms))[:4]
            )
        )
    if not high_importance and not medium_terms and not urgency_terms and not action_terms and not financial_terms:
        evidence.append("no strong urgency, business-impact, security-risk, or action-required evidence")

    return EmailAnalysis(
        email_id=email_id,
        filename=filename,
        sender=sender,
        reply_to=reply_to or "Not provided",
        recipient=recipient,
        subject=subject,
        date=date,
        spam_status=spam_status,
        validity=validity,
        sender_identity=sender_identity if sender_format_valid else "Unknown",
        sender_context=sender_context,
        importance=importance,
        score=score,
        reason="; ".join(evidence) + ".",
        text=text,
    )


def analyze_pdf(filename: str, data: bytes) -> EmailAnalysis:
    email_id = Path(filename).stem.upper()
    return analyze_email(email_id, filename, extract_pdf_text(data))


def analyze_files(files: Iterable[Path | BinaryIO]) -> list[EmailAnalysis]:
    analyses: list[EmailAnalysis] = []
    for item in files:
        if isinstance(item, Path):
            analyses.append(analyze_pdf(item.name, item.read_bytes()))
        else:
            name = getattr(item, "name", "uploaded-email.pdf")
            analyses.append(analyze_pdf(Path(name).name, item.getvalue()))
    return sorted(analyses, key=lambda email: (-email.score, email.email_id))


def build_follow_up(analyses: list[EmailAnalysis]) -> str:
    if not analyses:
        return "Upload or select emails to generate a comparison."
    high = [email.email_id for email in analyses if email.importance == "High"]
    invalid = [email.email_id for email in analyses if email.validity == "Invalid"]
    spam = [email.email_id for email in analyses if email.spam_status == "Spam"]
    high_text = ", ".join(high[:5]) or "none"
    return (
        f"Prioritize {high_text}. There are {len(spam)} suspicious/spam message(s) "
        f"and {len(invalid)} email(s) with invalid sender information. "
        "Would you like to review the highest-priority emails first or compare all "
        "emails from a specific sender?"
    )


def answer_follow_up(question: str, analyses: list[EmailAnalysis]) -> str:
    """Answer common comparison questions using only analyzed email evidence."""
    if not analyses:
        return "Analyze emails before asking a follow-up question."
    query = question.strip().lower()
    if not query:
        return "Enter a question about the analyzed emails."

    if "spam" in query or "suspicious" in query:
        matches = [email.email_id for email in analyses if email.spam_status == "Spam"]
        return f"Suspicious/spam emails: {', '.join(matches) or 'none'}."
    if "high" in query or "important" in query or "prioriti" in query:
        matches = [
            f"{email.email_id} ({email.subject})"
            for email in analyses
            if email.importance == "High"
        ]
        return f"Highest-priority emails: {', '.join(matches) or 'none'}."
    if "invalid" in query or "validity" in query or "format" in query:
        matches = [email.email_id for email in analyses if email.validity == "Invalid"]
        return f"Emails with invalid sender format: {', '.join(matches) or 'none'}."
    if "compare" in query or "difference" in query:
        selected = [
            email for email in analyses
            if email.email_id.lower() in query
        ]
        if len(selected) >= 2:
            return " | ".join(
                f"{email.email_id}: {email.spam_status}, {email.validity}, "
                f"{email.importance}; {email.reason}"
                for email in selected[:5]
            )
        return "Name at least two email IDs in the question, for example: compare EML-002 and EML-040."
    for email in analyses:
        if email.email_id.lower() in query:
            return (
                f"{email.email_id}: {email.spam_status} | {email.validity} | "
                f"{email.importance}. {email.reason}"
            )
    return (
        "I can answer questions about a specific EML ID, spam/suspicious emails, "
        "highest-priority emails, invalid sender formats, or comparisons."
    )

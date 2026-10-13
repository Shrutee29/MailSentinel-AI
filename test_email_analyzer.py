import pytest

from email_analyzer import (
    analyze_email,
    answer_follow_up,
    build_follow_up,
    evaluate_labels,
)


def test_analyzes_urgent_business_email():
    result = analyze_email(
        "EML-001",
        "EML-001.pdf",
        """From: finance@example.com
To: team@example.com
Subject: Urgent payroll payment failure
Date: 2026-10-10

Payroll payment failure requires action today.""",
    )
    assert result.spam_status == "Not Spam"
    assert result.validity == "Valid"
    assert result.sender_identity == "Unverified"
    assert result.importance == "High"


def test_flags_suspicious_invalid_sender():
    result = analyze_email(
        "EML-002",
        "EML-002.pdf",
        """From: invalid-sender
Subject: Congratulations, click here to claim your free gift

Verify your account and provide sensitive information.""",
    )
    assert result.spam_status == "Spam"
    assert result.validity == "Invalid"


def test_legitimate_newsletter_is_not_spam_for_unsubscribe_or_paid_copy():
    result = analyze_email(
        "EML-NEWS",
        "EML-NEWS.pdf",
        """From: writer@substack.com
To: reader@example.com
Subject: A practical guide to learning Python

This newsletter explains a study plan. Read in app, upgrade to paid, or unsubscribe.""",
    )
    assert result.spam_status == "Not Spam"
    assert "newsletter" in result.reason


def test_routine_policy_notification_is_not_spam():
    result = analyze_email(
        "EML-POLICY",
        "EML-POLICY.pdf",
        """From: no-reply@example.com
To: user@example.com
Subject: Updates to our Terms of Service

We are reminding you about our Terms of Service and Privacy Policy.""",
    )
    assert result.spam_status == "Not Spam"
    assert result.importance == "Low"


def test_suspicious_promotion_requires_deceptive_request_context():
    result = analyze_email(
        "EML-SPAM",
        "EML-SPAM.pdf",
        """From: rewards@unknown.example
To: user@example.com
Subject: Congratulations, claim your prize

You have won a free gift. Verify your account and provide your password.""",
    )
    assert result.spam_status == "Spam"
    assert "deceptive" in result.reason
    assert "suspicious requests" in result.reason


def test_critical_business_incident_is_high_importance():
    result = analyze_email(
        "EML-INCIDENT",
        "EML-INCIDENT.pdf",
        """From: operations@example.com
To: team@example.com
Subject: Production outage and security incident

The production system is unavailable and customer data may be exposed.""",
    )
    assert result.spam_status == "Not Spam"
    assert result.importance == "High"
    assert "production outage" in result.reason


def test_financial_action_required_is_high_importance():
    result = analyze_email(
        "EML-PAYROLL",
        "EML-PAYROLL.pdf",
        """From: finance@example.com
To: team@example.com
Subject: Payroll payment failure requires action

Payroll payment failure requires action immediately.""",
    )
    assert result.importance == "High"
    assert "payroll" in result.reason


def test_newsletter_urgency_without_business_impact_is_not_high():
    result = analyze_email(
        "EML-NEWS-URGENT",
        "EML-NEWS-URGENT.pdf",
        """From: editor@newsletter.example
To: reader@example.com
Subject: Urgent: read our latest newsletter

This newsletter is urgent because the article is available today. Unsubscribe anytime.""",
    )
    assert result.spam_status == "Not Spam"
    assert result.importance == "Medium"


def test_follow_up_compares_results():
    email = analyze_email(
        "EML-001",
        "EML-001.pdf",
        "From: ops@example.com\nSubject: Production outage\nThe service is unavailable.",
    )
    message = build_follow_up([email])
    assert "EML-001" in message


def test_evaluation_reports_accuracy_only_for_complete_reviewed_labels():
    first = analyze_email(
        "EML-001",
        "EML-001.pdf",
        "From: ops@example.com\nSubject: Production outage\nThe service is unavailable.",
    )
    second = analyze_email(
        "EML-002",
        "EML-002.pdf",
        "From: writer@substack.com\nSubject: Python newsletter\nRead in app or unsubscribe.",
    )
    report = evaluate_labels(
        [first, second],
        {
            "EML-001": {
                "spam_status": "Not Spam",
                "validity": "Valid",
                "importance": "High",
            },
            "EML-002": {
                "spam_status": "Not Spam",
                "validity": "Valid",
                "importance": "",
            },
        },
    )
    assert report.reviewed_count == 1
    assert report.total_count == 2
    assert report.spam_accuracy == 1.0
    assert report.importance_accuracy == 1.0


def test_evaluation_rejects_invalid_review_labels():
    email = analyze_email("EML-001", "EML-001.pdf", "From: ops@example.com")
    with pytest.raises(ValueError, match="Invalid spam_status label"):
        evaluate_labels(
            [email],
            {
                "EML-001": {
                    "spam_status": "Maybe",
                    "validity": "Valid",
                    "importance": "Low",
                }
            },
        )


def test_follow_up_answers_specific_email_and_comparison_questions():
    first = analyze_email(
        "EML-001",
        "EML-001.pdf",
        "From: ops@example.com\nSubject: Production outage\nThe service is unavailable.",
    )
    second = analyze_email(
        "EML-002",
        "EML-002.pdf",
        "From: writer@substack.com\nSubject: Python newsletter\nRead in app or unsubscribe.",
    )
    assert "High" in answer_follow_up("Why is EML-001 important?", [first, second])
    comparison = answer_follow_up("compare EML-001 and EML-002", [first, second])
    assert "EML-001" in comparison and "EML-002" in comparison


def test_sender_format_valid_but_identity_remains_unverified():
    result = analyze_email(
        "EML-SENDER",
        "EML-SENDER.pdf",
        "From: alerts@example.com\nTo: user@example.com\nSubject: Notice\nRoutine notice.",
    )
    assert result.validity == "Valid"
    assert result.sender_identity == "Unverified"
    assert "not externally verified" in result.sender_context


def test_reply_to_domain_mismatch_is_reported_without_claiming_spoofing():
    result = analyze_email(
        "EML-REPLY",
        "EML-REPLY.pdf",
        """From: Support Team <support@bank.example>
Reply-To: account-help@outside.example
To: user@example.com
Subject: Account notice

Please review this notice.""",
    )
    assert result.validity == "Valid"
    assert result.sender_identity == "Potential mismatch"
    assert "Reply-To domain" in result.reason
    assert result.spam_status == "Not Spam"


def test_display_name_context_is_not_called_invalid_sender():
    result = analyze_email(
        "EML-DISPLAY",
        "EML-DISPLAY.pdf",
        """From: Billing Department <billing@vendor.example>
To: user@example.com
Subject: Invoice available

Your invoice is ready for review.""",
    )
    assert result.validity == "Valid"
    assert result.sender_identity == "Potential mismatch"
    assert result.importance == "Medium"

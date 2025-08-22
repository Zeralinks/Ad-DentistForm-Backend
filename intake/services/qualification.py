# intake/services/qualification.py
def qualify(payload: dict) -> dict:
    """
    Input: validated_data with model field names.
    Output: dict with status, score, reasons, server-side tags.
    """
    score = 0
    reasons = []
    server_tags = set(payload.get("tags") or [])

    urgency = (payload.get("urgency") or "").lower()
    insurance = (payload.get("insurance") or "").lower()
    financing = (payload.get("financing") or "").lower()
    symptoms = payload.get("symptoms") or []
    notes = (payload.get("notes") or "").strip()

    # Spam/invalid checks first
    if not payload.get("hipaa"):
        return dict(
            qualification_status="disqualified",
            qualification_score=0,
            qualification_reasons=["Missing HIPAA consent"],
            server_tags=list(server_tags | {"invalid"})
        )

    if not payload.get("phone") or len("".join(filter(str.isdigit, payload["phone"]))) < 10:
        reasons.append("Weak phone")
        score -= 20

    # Urgency
    if urgency == "today":
        score += 30; reasons.append("Urgent: today")
        server_tags.add("urgent")
    elif urgency == "this week":
        score += 15; reasons.append("Urgent: this week")
    else:
        score += 5;  reasons.append("Flexible")

    # Symptoms (very rough starter weights)
    def has(txt): 
        return any(txt.lower() in s.lower() for s in symptoms)

    if has("Emergency") or has("Toothache") or has("Broken"):
        score += 30; reasons.append("Emergency-like"); server_tags.add("emergency")
    if has("Restorative") or has("Crowns") or has("Fillings"):
        score += 15; reasons.append("Restorative intent")
    if has("Invisalign") or has("Orthodontics"):
        score += 15; reasons.append("Invisalign interest")
    if has("Cosmetic") or has("Whitening") or has("Veneers"):
        score += 10; reasons.append("Cosmetic interest")
    if has("Checkup"):
        score += 5;  reasons.append("Checkup")

    # Insurance & financing
    if insurance and insurance not in ["", "self-pay"]:
        score += 10; reasons.append(f"Insurance: {insurance}")
    elif insurance == "self-pay":
        score += 5; reasons.append("Self-pay")
        server_tags.add("verify_insurance")

    if financing == "yes":
        score += 10; reasons.append("Financing requested")
        server_tags.add("financing_interest")

    # Zip present (weak signal of completeness)
    if payload.get("zip_code"):
        score += 5; reasons.append("Provided ZIP")

    # Very basic notes signal
    if notes:
        score += 5; reasons.append("Left notes")

    # Map score to status
    if score >= 60:
        status = "qualified"
    elif score >= 40:
        status = "nurture"
    else:
        status = "disqualified"

    return dict(
        qualification_status=status,
        qualification_score=score,
        qualification_reasons=reasons,
        server_tags=list(server_tags),
    )

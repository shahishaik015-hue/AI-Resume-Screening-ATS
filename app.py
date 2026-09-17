import re
import io
from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfReader
from docx import Document
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

latest_result = {}

SKILLS = [
    "python", "java", "sql", "html", "css",
    "javascript", "react", "flask",
    "machine learning", "data analytics",
    "git", "mongodb", "node.js"
]

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload")
def upload():
    return render_template("upload.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    global latest_result

    files = request.files.getlist("resume")
    job_description = request.form["job_description"].lower()

    results = []

    for file in files:

        resume_text = ""

        # ---------- PDF ----------
        if file.filename.endswith(".pdf"):
            pdf = PdfReader(file)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    resume_text += text + "\n"

        # ---------- DOCX ----------
        elif file.filename.endswith(".docx"):
            doc = Document(file)
            for para in doc.paragraphs:
                resume_text += para.text + "\n"

        else:
            continue

        # ---------- Candidate Details ----------
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
        email = email_match.group() if email_match else "Not Found"

        phone_match = re.search(r'(\+91[- ]?)?[6-9]\d{9}', resume_text)
        phone = phone_match.group() if phone_match else "Not Found"

        name = file.filename

        for line in resume_text.split("\n"):
            line = line.strip()
            if line and "@" not in line and not any(c.isdigit() for c in line):
                if 2 <= len(line.split()) <= 4:
                    name = line.title()
                    break

        # ---------- ATS ----------
        resume_lower = resume_text.lower()

        matched = []
        missing = []

        for skill in SKILLS:
            if skill in job_description:
                if skill in resume_lower:
                    matched.append(skill)
                else:
                    missing.append(skill)

        total = len(matched) + len(missing)

        score = int((len(matched) / total) * 100) if total else 0

        # Rating
        if score >= 80:
            rating = "Excellent"
        elif score >= 60:
            rating = "Good"
        else:
            rating = "Needs Improvement"

        # Recruiter Decision
        if score >= 85:
            decision = "Highly Recommended"
        elif score >= 70:
            decision = "Recommended"
        else:
            decision = "Needs Improvement"

        # Suggestions
        suggestions = []

        if "flask" in missing:
            suggestions.append("Add a Flask project.")

        if "git" in missing:
            suggestions.append("Mention Git/GitHub experience.")

        if "sql" in missing:
            suggestions.append("Include SQL skills.")

        if len(suggestions) == 0:
            suggestions.append("Excellent! Resume matches the Job Description.")

        results.append({
            "name": name,
            "email": email,
            "phone": phone,
            "score": score,
            "rating": rating,
            "decision": decision,
            "matched": matched,
            "missing": missing,
            "suggestions": suggestions
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    latest_result = results[0]

    # ---------- Single Resume ----------
    if len(results) == 1:

        r = results[0]

        return render_template(
            "result.html",
            score=r["score"],
            rating=r["rating"],
            decision=r["decision"],
            matched=r["matched"],
            missing=r["missing"],
            suggestions=r["suggestions"],
            name=r["name"],
            email=r["email"],
            phone=r["phone"]
        )

    # ---------- Multiple Resume ----------
    return render_template(
        "ranking.html",
        results=results
    )

@app.route("/download")
def download_pdf():

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("AI Resume ATS Report", styles["Title"]))

    story.append(Paragraph("<br/>", styles["BodyText"]))

    story.append(Paragraph(f"<b>Name:</b> {latest_result['name']}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Email:</b> {latest_result['email']}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Phone:</b> {latest_result['phone']}", styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["BodyText"]))

    story.append(Paragraph(f"<b>ATS Score:</b> {latest_result['score']}%", styles["BodyText"]))
    story.append(Paragraph(f"<b>Rating:</b> {latest_result['rating']}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Decision:</b> {latest_result['decision']}", styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["BodyText"]))
    story.append(Paragraph("<b>Matched Skills</b>", styles["Heading2"]))

    for skill in latest_result["matched"]:
        story.append(Paragraph(f"• {skill}", styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["BodyText"]))
    story.append(Paragraph("<b>Missing Skills</b>", styles["Heading2"]))

    for skill in latest_result["missing"]:
        story.append(Paragraph(f"• {skill}", styles["BodyText"]))

    story.append(Paragraph("<br/>", styles["BodyText"]))
    story.append(Paragraph("<b>Improvement Suggestions</b>", styles["Heading2"]))

    for item in latest_result["suggestions"]:
        story.append(Paragraph(f"• {item}", styles["BodyText"]))

    doc.build(story)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="ATS_Report.pdf",
        mimetype="application/pdf"
    )

if __name__ == "__main__":
    app.run(debug=True)
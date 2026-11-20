"""Offline alert templates, optional speech, and simulated dispatch."""
from pathlib import Path
import tempfile

TRANSLATIONS = {
 "English": {"prefix":"Machine alert", "urgent":"Please inspect", "problem":"Likely problem", "level":"Urgency", "part":"Probable part", "factory":"Factory"},
 "Tamil": {"prefix":"இயந்திர எச்சரிக்கை", "urgent":"தயவுசெய்து பரிசோதிக்கவும்", "problem":"சாத்தியமான பிரச்சினை", "level":"அவசரம்", "part":"தேவையான உதிரி பாகம்", "factory":"தொழிற்சாலை"},
 "Hindi": {"prefix":"मशीन अलर्ट", "urgent":"कृपया जाँच करें", "problem":"संभावित समस्या", "level":"प्राथमिकता", "part":"संभावित पुर्जा", "factory":"कारखाना"},
}

def message(machine: str, issue: str, urgency: str, part: str, location: str, language: str="English") -> str:
    t = TRANSLATIONS.get(language, TRANSLATIONS["English"])
    localized_issue = issue
    if language == "Tamil":
        localized_issue = "தாங்கி தேய்மானம் இருக்கலாம்" if "bearing" in issue.lower() else "தூசி அதிகமாக உள்ளது; காற்று வழிகளைச் சுத்தம் செய்யவும்"
    elif language == "Hindi":
        localized_issue = "बेयरिंग घिसाव की संभावना है" if "bearing" in issue.lower() else "धूल अधिक है; वेंट साफ़ करें"
    return f"{t['prefix']}: {machine}. {t['problem']}: {localized_issue}. {t['urgent']}. {t['level']}: {urgency}. {t['part']}: {part}. {t['factory']}: {location} (https://maps.google.com/?q={location})."

def make_audio(text: str, language: str):
    """Return an MP3 path when gTTS/network are available; otherwise None."""
    try:
        from gtts import gTTS
        code = {"English":"en", "Tamil":"ta", "Hindi":"hi"}.get(language, "en")
        path = Path(tempfile.gettempdir()) / "machinesense_alert.mp3"
        gTTS(text=text, lang=code).save(str(path))
        return str(path)
    except Exception:
        return None

def rank_technicians(technicians, skill: str, location: str):
    rows = technicians.copy()
    rows["skill_match"] = rows.skills.str.contains(skill, case=False, na=False).astype(int)
    # Sample locations are nearby demo towns; prefer skill match, then declared distance.
    rows["distance"] = rows.location.map({"Coimbatore": 0, "Tiruppur": 25, "Erode": 60}).fillna(100)
    return rows.sort_values(["skill_match", "distance"], ascending=[False, True])

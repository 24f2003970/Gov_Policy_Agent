# Presentation question QA — 2026-10-27

## Presentation-ready questions

These questions were tested in the signed-in Ask UI against the currently active reviewed source, **A Pathway to Professional Growth: PM’s Internship Scheme**, a historical PIB factsheet dated 2024-10-12. Answers below are concise summaries; the app answer may phrase them differently.

| # | Language | Ask this | Expected answer from the source | Citation verified |
|---|---|---|---|---|
| 1 | English | According to the 12 October 2024 PIB factsheet, what age group was the pilot intended for? | Youth aged 21–24. | PDF p. 2; 100% citation coverage; answered. |
| 2 | English | According to the 12 October 2024 factsheet, what monthly financial support was described for interns? | ₹5,000/month: ₹500 from the partner company (conditional on attendance/conduct) and ₹4,500 from the government through DBT. | PDF p. 3; answer had previously passed with 100% citation coverage. |
| 3 | English | How many internships could a candidate apply for through the portal? | Up to five internships. | PDF p. 4; 100% citation coverage; answered. |
| 4 | English | How many sectors did the pilot internship opportunities cover? | 24 sectors. | PDF p. 1; 100% citation coverage; answered. |
| 5 | English | How many internships did the pilot target for FY 2024–25? | 1.25 lakh internships. | PDF p. 1; 100% citation coverage; answered. |
| 6 | English | On what date was the PM Internship Scheme launched? | 3 October 2024. | PDF p. 1; 100% citation coverage; answered. |
| 7 | Hindi | 2024 की PIB factsheet के अनुसार, PM Internship Scheme के pilot में किस आयु वर्ग के युवाओं को शामिल किया गया था? | 21–24 वर्ष की आयु के युवा। | PDF p. 2; 100% citation coverage; answered with clean wording. |
| 8 | Hindi | 2024 की PIB factsheet के अनुसार, PM Internship Scheme के pilot का FY 2024–25 लक्ष्य कितनी internships का था? | FY 2024–25 में pilot का लक्ष्य 1.25 लाख internships था। | PDF p. 1; 100% citation coverage; answered. The model misspelled “इंटर्नशिप” once as “इंटरनशिप”; say/use the corrected spelling. |

## Other questions tested and excluded

- Combined duration plus target query: insufficient evidence.
- Hindi monthly-support question: insufficient evidence, even though the English version is supported by page 3.
- Hindi one-time-grant question: insufficient evidence in the UI; exclude from the presentation list.
- Hindi duration question, including a Hinglish rephrase: insufficient evidence; exclude.
- The launch-date question was accidentally first submitted while Hindi was selected and abstained; it was rerun in English and then answered with page 1 and 100% citation coverage.

The model is intentionally allowed to abstain. Do not present an excluded question as a successful demonstration. For Hindi, the age question is the cleanest live demo; target count is also supported, but read it back with corrected spelling.

## Evidence and scope

- This list is about the single eligible historical source above, not all scheme PDFs in the library. Other PDFs remain excluded/unreviewed, so questions about PM-KISAN, Ayushman Bharat, PM Awas, Jal Jeevan, etc. may abstain until their sources are reviewed and indexed.
- The official source link displayed in the citation is PIB Press Note 153275: https://pib.gov.in/PressNoteDetails.aspx?ModuleId=3&NoteId=153275&lang=1&reg=3
- “100% citation coverage” means every displayed factual claim had a valid cited source quote. It is not a correctness probability or independent validation. The app reports only a limited evidence assessment; independent agreement and measured reliability are unavailable.
- The factsheet is dated 2024-10-12. Its historical claims do not establish current scheme rules, eligibility, or application advice.

## Run and verification checkpoint

Project root (PowerShell): `C:\Users\satya\Downloads\Compressed\Gov_Policy_Agent-main\Gov_Policy_Agent-main`

```powershell
.\scripts\native.ps1 status
```

At this checkpoint, `api`, `frontend`, `worker`, `index`, and `rag` all reported `managed running`; the database answer-worker heartbeat was fresh. Open `http://127.0.0.1:5173/#ask` and select the answer language matching the question before submitting. If services have stopped, consult `docs/SETUP.md`; run preflight and start only missing owners. Do not reprovision accounts or reset the database.

Focused grounding tests after the narrow Hindi age-answer constructor change: **13 passed** (`.\.venv\Scripts\python.exe -m pytest tests/test_grounding.py -q`). The app-level presentation questions were checked in the UI as recorded above. RAG was restarted once to load the age-language change; all five native services were running at handoff.

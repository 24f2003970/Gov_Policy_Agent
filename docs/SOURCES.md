# Sources and licensing disclosures

The local GOV-CS-028 proposal (34 physical pages) supplied project requirements. It is excluded from Git and is not chatbot evidence. [Requirement mapping](../REQUIREMENTS_MATRIX.md) preserves proposal references; accuracy, novelty, publication and production-scale aspirations are not established results. No authorship history or blanket project license is inferred here.

## Local document corpus

[corpus_manifest.json](corpus_manifest.json) retains original URLs, issuers, titles, SHA256 hashes, byte/page counts, retrieval date, verification notes and rights uncertainty. It is preserved unchanged by documentation cleanup.

| Source | Pages | Recorded status |
| --- | --- | --- |
| PM-KISAN operational guidelines | 12 | Digital extraction completed |
| PMJDY mission document | 40 | Partial; one low-text page |
| PMAY-U 2.0 guidelines | 112 | Partial; five low-text pages |

Retrieved/inspected 2026-10-05. Official origins and covers/title/issuer were checked; exact publication/effective dates remain unknown where not established. Historical snapshots are not current entitlement advice. SHA256 verifies bytes, not authenticity or legal status.

All three are local-reference-only; reproduction permissions are not obtained. [PM-KISAN copyright policy](https://www.pmkisan.gov.in/CopyrightPolicy.aspx) and [PMAY copyright policy](https://pmay-urban.gov.in/copyright) require reproduction permission. PMJDY's [official accessibility page](https://www.pmjdy.gov.in/accessibility) lists a copyright policy whose text was unavailable during review. Public availability is not a blanket reuse license. Originals and extracted corpus text are not redistributed in Git; zero versions are eligible for future retrieval.

## Dependency references

PyMuPDF is AGPL/commercial dual licensed; use and redistribution must respect the applicable license. Proprietary redistribution needs separate review. See [licensing](https://pymupdf.io/licensing), [installation](https://pymupdf.readthedocs.io/en/latest/installation.html), [page extraction](https://pymupdf.readthedocs.io/en/latest/page.html) and [document API](https://pymupdf.readthedocs.io/en/latest/document.html).

Implementation references: [PostgreSQL SELECT/SKIP LOCKED](https://www.postgresql.org/docs/18/sql-select.html), [SQLAlchemy psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#psycopg), [psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html), [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [pwdlib](https://frankie567.github.io/pwdlib/reference/pwdlib/) and [PyJWT](https://pyjwt.readthedocs.io/en/latest/usage.html). Dependency license/notice files remain with installed distributions; this documentation does not replace them.

"""
scrape_rmp.py — Collect professor reviews from Rate My Professors via its GraphQL API.

RMP's website is JavaScript-rendered, but it's backed by a public GraphQL endpoint.
We search each school by name, pull Computer Science professors, then fetch each
professor's reviews. One .txt file is written per professor into documents/, so
source attribution stays clean downstream.

Usage:
    python scrape_rmp.py
"""

import re
import time
from pathlib import Path

import requests

GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
# Public anonymous auth token RMP's own frontend uses ("test:test" base64-encoded).
HEADERS = {
    "Authorization": "Basic dGVzdDp0ZXN0",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.ratemyprofessors.com/",
}

SCHOOLS = ["Stanford University", "Harvard University"]
MAX_PROFS_PER_SCHOOL = 8      # how many CS profs to pull per school
MAX_RATINGS_PER_PROF = 60     # cap reviews per professor

OUT_DIR = Path(__file__).parent / "documents"


def gql(query: str, variables: dict) -> dict:
    """Run a GraphQL query and return the JSON 'data' block."""
    resp = requests.post(
        GRAPHQL_URL,
        headers=HEADERS,
        json={"query": query, "variables": variables},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    return payload["data"]


SCHOOL_SEARCH = """
query SchoolSearch($text: String!) {
  newSearch {
    schools(query: {text: $text}) {
      edges { node { id legacyId name city state } }
    }
  }
}
"""

TEACHER_SEARCH = """
query TeacherSearch($text: String!, $schoolID: ID!) {
  newSearch {
    teachers(query: {text: $text, schoolID: $schoolID}) {
      edges {
        node {
          id legacyId firstName lastName department
          avgRating avgDifficulty numRatings wouldTakeAgainPercent
        }
      }
    }
  }
}
"""

RATINGS_QUERY = """
query Ratings($id: ID!, $count: Int!) {
  node(id: $id) {
    ... on Teacher {
      firstName lastName department avgRating avgDifficulty numRatings
      school { name }
      ratings(first: $count) {
        edges {
          node {
            class comment date
            clarityRating difficultyRating helpfulRating
            wouldTakeAgain grade attendanceMandatory
            ratingTags
          }
        }
      }
    }
  }
}
"""


def find_school_id(name: str) -> tuple[str, str]:
    data = gql(SCHOOL_SEARCH, {"text": name})
    edges = data["newSearch"]["schools"]["edges"]
    if not edges:
        raise RuntimeError(f"No school found for '{name}'")
    node = edges[0]["node"]
    print(f"  school: {node['name']} ({node.get('city')}, {node.get('state')}) "
          f"id={node['id']}")
    return node["id"], node["name"]


def find_cs_profs(school_id: str) -> list[dict]:
    """Search professors at a school, keep those in a CS-like department."""
    data = gql(TEACHER_SEARCH, {"text": "", "schoolID": school_id})
    edges = data["newSearch"]["teachers"]["edges"]
    profs = []
    for e in edges:
        n = e["node"]
        dept = (n.get("department") or "").lower()
        # Match "computer science" or "cs" as a whole word — NOT the "cs" inside
        # "economics", "physics", "mathematics", etc.
        is_cs = "computer science" in dept or re.search(r"\bcs\b", dept) is not None
        if is_cs and (n.get("numRatings") or 0) > 0:
            profs.append(n)
    # most-reviewed first
    profs.sort(key=lambda p: p.get("numRatings", 0), reverse=True)
    return profs[:MAX_PROFS_PER_SCHOOL]


def fetch_ratings(teacher_id: str) -> dict:
    data = gql(RATINGS_QUERY, {"id": teacher_id, "count": MAX_RATINGS_PER_PROF})
    return data["node"]


def slugify(*parts: str) -> str:
    s = "_".join(parts).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def write_prof_file(school_name: str, teacher: dict) -> Path:
    fn = teacher["firstName"]
    ln = teacher["lastName"]
    dept = teacher.get("department", "")
    school_slug = slugify(school_name.split()[0])  # "stanford" / "harvard"
    path = OUT_DIR / f"cs_{school_slug}_{slugify(fn, ln)}_reviews.txt"

    lines = []
    lines.append(f"Professor: {fn} {ln}")
    lines.append(f"School: {teacher['school']['name']}")
    lines.append(f"Department: {dept}")
    lines.append(f"Overall rating: {teacher.get('avgRating')} / 5  |  "
                 f"Difficulty: {teacher.get('avgDifficulty')} / 5  |  "
                 f"Total ratings: {teacher.get('numRatings')}")
    lines.append("=" * 70)
    lines.append("")

    edges = teacher["ratings"]["edges"]
    for i, e in enumerate(edges, 1):
        r = e["node"]
        comment = (r.get("comment") or "").strip()
        if not comment:
            continue
        tags = ", ".join(r.get("ratingTags", "").split("--")) if r.get("ratingTags") else ""
        lines.append(f"[Review {i}] Course: {r.get('class', 'N/A')}  |  Date: {r.get('date', 'N/A')}")
        lines.append(f"Quality: {r.get('clarityRating')}/5  Difficulty: {r.get('difficultyRating')}/5  "
                     f"Grade: {r.get('grade') or 'N/A'}  Would take again: {r.get('wouldTakeAgain')}")
        if tags:
            lines.append(f"Tags: {tags}")
        lines.append(comment)
        lines.append("-" * 70)

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    OUT_DIR.mkdir(exist_ok=True)
    total_files = 0
    for school in SCHOOLS:
        print(f"\n=== {school} ===")
        school_id, school_name = find_school_id(school)
        profs = find_cs_profs(school_id)
        print(f"  found {len(profs)} CS professors with reviews")
        for p in profs:
            try:
                teacher = fetch_ratings(p["id"])
                path = write_prof_file(school_name, teacher)
                n_reviews = sum(
                    1 for e in teacher["ratings"]["edges"] if (e["node"].get("comment") or "").strip()
                )
                print(f"    wrote {path.name}  ({n_reviews} reviews)")
                total_files += 1
                time.sleep(0.5)  # be polite
            except Exception as ex:
                print(f"    !! failed for {p['firstName']} {p['lastName']}: {ex}")
    print(f"\nDone. Wrote {total_files} document files to {OUT_DIR}")


if __name__ == "__main__":
    main()

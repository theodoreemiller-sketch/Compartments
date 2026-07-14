#!/usr/bin/env python3
"""
sync_helper.py — Apparatus Study Guide Sync Helper
Glen Ellyn Fire Department · Unofficial Study Guides

PURPOSE
-------
Eliminates missed items during the morning doc sync by replacing manual
visual comparison with a structured, code-driven diff.

Two main workflows:

  1. diff_doc_vs_html(vehicle, doc_text)
     → Parses the Google Doc and the HTML section for that vehicle,
       then reports every doc item that has no matching card in the HTML.
       Run this BEFORE making any HTML edits.

  2. diff_snapshots(vehicle, new_doc_text)
     → Compares new doc content against the last saved snapshot to show
       exactly which items were added or removed in the doc itself.
       Run this to understand WHAT changed before deciding what to edit.

  3. save_snapshot(vehicle, doc_text)
     → Save a parsed snapshot of the current doc. Call this AFTER
       successfully updating the HTML so the baseline stays current.

USAGE (from the scheduled task)
--------------------------------
  import sys
  sys.path.insert(0, WORKSPACE)
  from sync_helper import diff_doc_vs_html, diff_snapshots, save_snapshot, VEHICLE_SECTION_IDS

  # Step A — what changed in the doc vs last snapshot?
  print(diff_snapshots("Tower 62", new_doc_text))

  # Step B — what's in the doc but missing from the HTML?
  print(diff_doc_vs_html("Tower 62", new_doc_text))

  # Step C — after HTML is updated:
  save_snapshot("Tower 62", new_doc_text)
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

# ── Paths ──────────────────────────────────────────────────────────────────
WORKSPACE = "/Users/ted.miller/Documents/Claude/Projects/UNOFFICIAL APPARATUS STUDY GUIDES"
HTML_PATH  = f"{WORKSPACE}/index.html"
SNAPSHOTS_PATH = f"{WORKSPACE}/doc_snapshots.json"

# ── Vehicle → HTML section ID mapping ─────────────────────────────────────
VEHICLE_SECTION_IDS = {
    "Engine 62":    "e62-guide",
    "Engine 61":    "e61-guide",
    "Engine 60":    "e60-guide",
    "Engine 63":    "e63-guide",
    "Utility 61":   "u61-guide",
    "Utility 62":   "u62-guide",
    "Brushtruck 62":"bt62-guide",
    "Squad 61":     "sq61-guide",
    "SCBA":         "scba-guide-content",
    "Tower 62":     "t62-guide",
}


# ══════════════════════════════════════════════════════════════════════════
# PARSING
# ══════════════════════════════════════════════════════════════════════════

def parse_doc_compartments(doc_text: str) -> dict:
    """
    Parse Google Doc markdown into {compartment_name: [item, item, ...]}

    Handles:
      ## Compartment Name        → new compartment
      - Item text                → item under current compartment
      * Item text                → same
      Plain lines after a header → treated as items if they look like content
    """
    compartments = {}
    current_comp = "__preamble__"
    items = []

    for raw_line in doc_text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        # Section header: # or ## or ###
        if re.match(r"^#{1,3}\s+", line):
            # Save previous compartment
            if items:
                compartments.setdefault(current_comp, []).extend(items)
            current_comp = re.sub(r"^#{1,3}\s+", "", line).strip()
            items = []

        # List item: - or *
        elif re.match(r"^[-*]\s+", line):
            item = re.sub(r"^[-*]\s+", "", line).strip()
            # Strip bold markers
            item = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", item)
            if item:
                items.append(item)

    # Flush last compartment
    if items:
        compartments.setdefault(current_comp, []).extend(items)

    return compartments


def parse_html_section(section_id: str, html: str = None) -> dict:
    """
    Parse the HTML for a vehicle section into:
      {compartment_name: [card_title, card_title, ...]}

    Dispatches to a vehicle-specific parser based on section_id because
    different vehicles use different HTML card architectures:

      Standard (E61, E60, E63, U61, U62, SQ61, T62):
        <section class="comp-section"> → <h2> → <div class="card-title">

      Engine 62 (e62-guide):
        <div class="section-header"> → <h2> (compartment)
        <div class="eq-title">           (item, may span tags like <span class="qty">)

      Brushtruck 62 (bt62-guide):
        <div class="section-block"> → <div class="section-title"> (compartment)
        <div class="eq-name">                                      (item)

      SCBA (scba-guide-content):
        Study-guide format — not a compartment inventory.
        <h2 class="scba-section"> headings are tracked as compartments
        with a single sentinel item so snapshots can detect additions/removals.
    """
    if html is None:
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()

    # Find section start
    start_marker = f'id="{section_id}"'
    start_idx = html.find(start_marker)
    if start_idx == -1:
        return {}

    # Find section end — next top-level guide section divider
    next_guide = re.search(r'<div id="[a-z0-9_-]+-guide', html[start_idx + 100:])
    if next_guide:
        end_idx = start_idx + 100 + next_guide.start()
        section_html = html[start_idx:end_idx]
    else:
        section_html = html[start_idx:]

    # ── Dispatch by section ID ─────────────────────────────────────────────
    if section_id == "e62-guide":
        return _parse_e62(section_html)
    if section_id == "bt62-guide":
        return _parse_bt62(section_html)
    if section_id == "scba-guide-content":
        return _parse_scba(section_html)

    # ── Standard parser (comp-section + card-title) ────────────────────────
    compartments = {}
    comp_pattern = re.compile(
        r'<section[^>]*class="comp-section"[^>]*>(.*?)</section>',
        re.DOTALL
    )
    for comp_match in comp_pattern.finditer(section_html):
        comp_html = comp_match.group(1)
        h2 = re.search(r"<h2[^>]*>(.*?)</h2>", comp_html, re.DOTALL)
        if not h2:
            continue
        comp_name = _strip_tags(h2.group(1)).strip()
        card_titles = [
            _strip_tags(m.group(1)).strip()
            for m in re.finditer(
                r'<div class="card-title">(.*?)</div>', comp_html, re.DOTALL
            )
        ]
        if comp_name and card_titles:
            compartments[comp_name] = card_titles
    return compartments


def _parse_e62(section_html: str) -> dict:
    """
    Engine 62 parser.
    Compartments: <div class="section-header"> → inner <h2>
    Items:        <div class="eq-title"> (may contain <span> tags)
    Strategy: find all compartment header positions, then collect eq-titles
    between consecutive compartment positions.
    """
    # Collect (position, name) for each compartment header
    header_pat = re.compile(
        r'<div class="section-header"[^>]*>.*?<h2[^>]*>(.*?)</h2>',
        re.DOTALL
    )
    headers = [(m.start(), _strip_tags(m.group(1)).strip())
               for m in header_pat.finditer(section_html)]

    if not headers:
        return {}

    # Collect all eq-title positions + text
    item_pat = re.compile(r'<div class="eq-title">(.*?)</div>', re.DOTALL)
    all_items = [(m.start(), _strip_tags(m.group(1)).strip())
                 for m in item_pat.finditer(section_html)]

    compartments = {}
    for i, (hpos, hname) in enumerate(headers):
        next_hpos = headers[i + 1][0] if i + 1 < len(headers) else len(section_html)
        items = [text for pos, text in all_items if hpos <= pos < next_hpos and text]
        if items:
            compartments[hname] = items

    return compartments


def _parse_bt62(section_html: str) -> dict:
    """
    Brushtruck 62 parser.
    Compartments: <div class="section-block"> → <div class="section-title">
    Items:        <div class="eq-name"> within the same section-block
    """
    block_pat = re.compile(
        r'<div class="section-block"[^>]*>(.*?)</div>\s*\n\s*\n',
        re.DOTALL
    )
    # Use a broader approach: split on section-block boundaries
    blocks = re.split(r'(?=<div class="section-block")', section_html)

    compartments = {}
    for block in blocks:
        title_m = re.search(r'<div class="section-title">(.*?)</div>', block, re.DOTALL)
        if not title_m:
            continue
        comp_name = _strip_tags(title_m.group(1)).strip()

        items = [
            _strip_tags(m.group(1)).strip()
            for m in re.finditer(r'<div class="eq-name">(.*?)</div>', block, re.DOTALL)
        ]
        items = [it for it in items if it]

        if comp_name and items:
            compartments[comp_name] = items

    return compartments


def _parse_scba(section_html: str) -> dict:
    """
    SCBA study guide parser.
    Not a compartment inventory — tracks the top-level section headings
    (<h2 class="scba-section">) so snapshot diffs can detect if a section
    is added or removed from the guide.
    Each section maps to a single sentinel item (the section heading itself)
    so the standard diff machinery works without modification.
    """
    section_pat = re.compile(
        r'<h2 class="scba-section"[^>]*>(.*?)</h2>', re.DOTALL
    )
    compartments = {}
    for m in section_pat.finditer(section_html):
        name = _strip_tags(m.group(1)).strip()
        # Strip leading ordinal like "1. " for cleaner keys
        clean = re.sub(r"^\d+\.\s*", "", name).strip()
        if clean:
            compartments[clean] = [clean]  # sentinel
    return compartments


def _strip_tags(text: str) -> str:
    """Remove HTML tags and decode common entities."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&#39;", "'").replace("&quot;", '"')
    return text.strip()


# ══════════════════════════════════════════════════════════════════════════
# MATCHING
# ══════════════════════════════════════════════════════════════════════════

def _base_norm(text: str) -> str:
    """
    Normalize a compartment name for reliable comparison:
      1. Strip any em-dash subtitle the HTML adds ("— Heavy Tools", "— Air & RIT").
         The doc never has these; HTML does.  Stripping them lets "Drivers Side Rear
         Compartment" match both "Driver's Side Rear Compartment — Air & RIT" and
         "Driver's Side Rear Compartment — Power & Climbing".
      2. Drop apostrophes/curly-quotes ("Driver's" → "Drivers").
      3. Collapse remaining punctuation and whitespace.
      4. Lowercase everything.

    Positional words (front, rear, middle, side, …) are intentionally KEPT
    so that "Front Middle" and "Front" are never treated as the same compartment.
    """
    # Strip em-dash subtitle (everything from — or – onward)
    text = re.split(r"\s*[—–]\s*", text)[0]
    text = text.lower()
    text = re.sub(u"[''`']", "", text)  # drop apostrophes
    text = re.sub(r"[^\w\s]", " ", text)             # other punct → space
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _key_words(text: str) -> set:
    """Extract meaningful words (len >= 3) from text for ITEM fuzzy matching.
    Positional/structural words are stripped because they add noise in item
    title comparisons (e.g. "Rear" appears in many card titles unrelated to
    the rear compartment).
    """
    text = re.sub(r"\b\d+[x×']?\b", "", text.lower())
    words = set(re.split(r"[\W_]+", text))
    stop = {"the", "and", "for", "with", "aka", "from", "each",
            "one", "two", "set", "kit"}
    return {w for w in words if len(w) >= 3 and w not in stop}


def _word_sim(a: str, b: str) -> float:
    """
    Simple character-level similarity between two strings (0.0–1.0).
    Uses the ratio of common characters (multiset) to total characters.
    Handles typos like "Haligan" ↔ "Halligan" and "Divers" ↔ "Drivers".
    """
    if not a or not b:
        return 0.0
    from collections import Counter
    ca, cb = Counter(a), Counter(b)
    common = sum((ca & cb).values())
    return 2.0 * common / (len(a) + len(b))


def _item_covered(doc_item: str, html_titles: list) -> bool:
    """
    Return True if a doc item is meaningfully represented by any HTML card title.

    Three-level check (any level returning True counts as covered):
      1. Exact keyword overlap — at least 1 shared keyword (fast path).
      2. Substring containment — handles compound-word splits like
         "Sledge Hammer" inside "Sledgehammers", or "Halligan" inside
         "Halligan (Bucket)".
      3. Fuzzy char-similarity — handles common spelling variants like
         "Haligan" ↔ "Halligan" (similarity ≥ 0.85).
    """
    doc_keys = _key_words(doc_item)
    if not doc_keys:
        return True  # Nothing meaningful to match

    for title in html_titles:
        html_keys = _key_words(title)

        # Level 1: exact keyword overlap
        if doc_keys & html_keys:
            return True

        # Level 2: substring containment (compound words)
        title_norm = re.sub(r"[^\w]", "", title.lower())
        for dk in doc_keys:
            if dk in title_norm or title_norm in dk:
                return True

        # Level 3: fuzzy character similarity (spelling variants)
        for dk in doc_keys:
            for hk in html_keys:
                if _word_sim(dk, hk) >= 0.85:
                    return True

    return False


def _comp_match_all(doc_comp: str, html_comps: dict) -> list:
    """
    Return a list of ALL HTML compartment keys that correspond to doc_comp.
    Returns an empty list if no reasonable match exists.

    Returning a list (not a single key) handles the case where one doc
    compartment maps to multiple HTML compartments — e.g. the doc has a single
    "Drivers Side Rear Compartment" that covers both
      "Driver's Side Rear Compartment — Air & RIT" and
      "Driver's Side Rear Compartment — Power & Climbing"
    in the HTML.  Callers should pool the items from all returned keys before
    checking coverage.

    Matching strategy (in priority order):
      1. Exact base-norm match  — strip em-dash subtitles, drop apostrophes,
         lowercase.  Collects ALL HTML compartments that match (handles splits).
      2. Compound-word/no-space match — "Cross Lay" ↔ "Crosslays".
      3. Best word-overlap score — every word of the base name is counted
         (including front/rear/middle/side so similar names stay distinct).
         Must score ≥ 60 % of the larger word set to qualify.
    """
    doc_base  = _base_norm(doc_comp)
    doc_words = set(doc_base.split())
    doc_num_m = re.search(r'\b(\d+)\b', doc_comp)
    doc_num   = doc_num_m.group(1) if doc_num_m else None

    # ── Pass 1: collect ALL exact base-norm matches ────────────────────────
    exact = [h for h in html_comps if _base_norm(h) == doc_base]
    if exact:
        return exact

    # ── Pass 2: compound-word / no-space match ─────────────────────────────
    # Handles "Cross Lay" ↔ "Crosslays", "Crosslay" ↔ "Cross Lay", etc.
    doc_nospace = doc_base.replace(" ", "")
    compound = [
        h for h in html_comps
        if _base_norm(h).replace(" ", "") == doc_nospace
        or _base_norm(h).replace(" ", "").rstrip("s") == doc_nospace
        or doc_nospace.rstrip("s") == _base_norm(h).replace(" ", "")
    ]
    if compound:
        return compound

    # ── Pass 3: scored word overlap ────────────────────────────────────────
    # Compute per-HTML-comp score; take all that tie for best AND meet threshold.
    scores = {}
    for h in html_comps:
        h_base  = _base_norm(h)
        h_words = set(h_base.split())
        common  = doc_words & h_words
        max_sz  = max(len(doc_words), len(h_words), 1)
        score   = len(common) / max_sz  # coverage / Jaccard-like

        # Bonus when compartment numbers match
        if doc_num:
            h_num_m = re.search(r'\b(\d+)\b', h)
            if h_num_m and h_num_m.group(1) == doc_num:
                score += 0.5          # strong but not absolute

        scores[h] = score

    if not scores:
        return []

    best_score = max(scores.values())
    if best_score < 0.60:             # require at least 60 % word overlap
        return []

    tied = [h for h, s in scores.items() if s == best_score]

    # If multiple HTML compartments tie, break tie using character-level
    # similarity of the NON-matching words (handles typos like "Divers" vs
    # "Drivers"/"Officers" — "Divers" is closer to "Drivers" by char sim).
    if len(tied) > 1:
        def _tiebreak_sim(h: str) -> float:
            h_words  = set(_base_norm(h).split())
            only_doc  = doc_words - h_words
            only_html = h_words  - doc_words
            if not only_doc or not only_html:
                return 0.0
            # Average best char-similarity across unmatched word pairs
            sims = []
            for dw in only_doc:
                best = max((_word_sim(dw, hw) for hw in only_html), default=0.0)
                sims.append(best)
            return sum(sims) / len(sims) if sims else 0.0

        best_tie = max(tied, key=_tiebreak_sim)
        # If one candidate is clearly better, return only that one;
        # otherwise keep the full tie list (legitimate multi-section split).
        tie_scores = {h: _tiebreak_sim(h) for h in tied}
        top_sim    = tie_scores[best_tie]
        if top_sim >= 0.60:
            # A clear winner — single best match
            return [best_tie]
        # No clear winner — all tied candidates are legitimately equivalent
        return tied

    return tied


# Keep a single-return alias for any code that still calls _comp_match
def _comp_match(doc_comp: str, html_comps: dict) -> str | None:
    matches = _comp_match_all(doc_comp, html_comps)
    return matches[0] if matches else None


# ══════════════════════════════════════════════════════════════════════════
# DIFF: DOC vs HTML
# ══════════════════════════════════════════════════════════════════════════

def diff_doc_vs_html(vehicle: str, doc_text: str, html: str = None) -> str:
    """
    Compare every item in the Google Doc against the HTML card titles
    for that vehicle's section.

    Returns a human-readable report of missing items.
    Call this BEFORE making HTML edits.
    """
    section_id = VEHICLE_SECTION_IDS.get(vehicle)
    if not section_id:
        return f"ERROR: Unknown vehicle '{vehicle}'. Check VEHICLE_SECTION_IDS."

    doc_comps  = parse_doc_compartments(doc_text)
    html_comps = parse_html_section(section_id, html)

    lines = [
        "",
        "=" * 62,
        f"DOC → HTML DIFF: {vehicle}",
        f"Section ID: #{section_id}",
        "=" * 62,
    ]

    missing = []
    no_html_comp = []

    for comp_name, doc_items in doc_comps.items():
        if comp_name == "__preamble__":
            continue

        # _comp_match_all returns a list; one doc compartment may map to
        # multiple HTML compartments (e.g. when the HTML splits one doc
        # compartment into two sub-sections with em-dash subtitles).
        html_keys = _comp_match_all(comp_name, html_comps)

        if not html_keys:
            # Whole compartment has no HTML counterpart
            no_html_comp.append((comp_name, doc_items))
            continue

        # Pool card titles from ALL matching HTML compartments
        html_titles = []
        for key in html_keys:
            html_titles.extend(html_comps[key])

        for item in doc_items:
            if not _item_covered(item, html_titles):
                missing.append((comp_name, item))

    if missing:
        lines.append(f"\n❌ ITEMS IN DOC BUT NOT COVERED IN HTML ({len(missing)}):")
        current_comp = None
        for comp, item in missing:
            if comp != current_comp:
                lines.append(f"\n  [{comp}]")
                current_comp = comp
            lines.append(f"    • {item}")

    if no_html_comp:
        lines.append(f"\n⚠️  DOC COMPARTMENTS WITH NO HTML MATCH ({len(no_html_comp)}):")
        for comp_name, items in no_html_comp:
            lines.append(f"\n  [{comp_name}] — {len(items)} items")
            for item in items:
                lines.append(f"    • {item}")

    if not missing and not no_html_comp:
        lines.append("\n✅  All doc items are represented in the HTML. No gaps found.")

    lines.append(f"\n  Doc compartments  : {[c for c in doc_comps if c != '__preamble__']}")
    lines.append(f"  HTML compartments : {list(html_comps.keys())}")
    lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# SNAPSHOT: SAVE & DIFF
# ══════════════════════════════════════════════════════════════════════════

def save_snapshot(vehicle: str, doc_text: str) -> str:
    """
    Parse the doc and save a snapshot to doc_snapshots.json.
    Call AFTER successfully updating the HTML.
    """
    snapshots = _load_snapshots()
    snapshots[vehicle] = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "compartments": parse_doc_compartments(doc_text),
    }
    _write_snapshots(snapshots)
    comp_count = len(snapshots[vehicle]["compartments"])
    return f"✅ Snapshot saved for {vehicle} ({comp_count} compartments)."


def diff_snapshots(vehicle: str, new_doc_text: str) -> str:
    """
    Compare new doc text against the saved snapshot for this vehicle.
    Shows exactly which items were added or removed in the doc.
    Call this first to understand what changed before touching the HTML.
    """
    snapshots = _load_snapshots()

    if vehicle not in snapshots:
        return (
            f"ℹ️  No snapshot found for '{vehicle}'. "
            f"Run save_snapshot() after the first sync to create one."
        )

    old_comps = snapshots[vehicle]["compartments"]
    new_comps = parse_doc_compartments(new_doc_text)
    saved_at  = snapshots[vehicle].get("saved_at", "unknown")

    lines = [
        "",
        "=" * 62,
        f"SNAPSHOT DIFF: {vehicle}",
        f"Snapshot date: {saved_at}",
        "=" * 62,
    ]

    all_comp_names = sorted(set(list(old_comps) + list(new_comps)))
    changes_found = False

    for comp in all_comp_names:
        if comp == "__preamble__":
            continue
        old_set = set(old_comps.get(comp, []))
        new_set = set(new_comps.get(comp, []))

        added   = new_set - old_set
        removed = old_set - new_set

        if added or removed:
            changes_found = True
            lines.append(f"\n  [{comp}]")
            for item in sorted(added):
                lines.append(f"    ➕ ADDED   : {item}")
            for item in sorted(removed):
                lines.append(f"    ➖ REMOVED : {item}")

    if not changes_found:
        lines.append(
            "\n  No item-level changes detected.\n"
            "  (The doc modification may be a formatting, typo, or metadata-only edit.)"
        )

    lines.append("")
    return "\n".join(lines)


def _load_snapshots() -> dict:
    p = Path(SNAPSHOTS_PATH)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _write_snapshots(data: dict) -> None:
    with open(SNAPSHOTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════

def run_self_test():
    """Quick smoke-test: parse HTML for all 10 vehicles and report card counts."""
    print("\n── sync_helper.py self-test ──────────────────────────────")
    print(f"HTML: {HTML_PATH}")
    print(f"Snapshots: {SNAPSHOTS_PATH}\n")

    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    for vehicle, section_id in VEHICLE_SECTION_IDS.items():
        comps = parse_html_section(section_id, html)
        total_cards = sum(len(v) for v in comps.values())
        status = "✅" if comps else "⚠️ "
        print(f"  {status} {vehicle:<16} #{section_id:<22} "
              f"{len(comps):>2} compartments, {total_cards:>3} cards")

    print("\n── Snapshot status ───────────────────────────────────────")
    snapshots = _load_snapshots()
    for vehicle in VEHICLE_SECTION_IDS:
        if vehicle in snapshots:
            saved = snapshots[vehicle].get("saved_at", "?")
            comp_count = len(snapshots[vehicle].get("compartments", {}))
            print(f"  ✅ {vehicle:<16} snapshot saved {saved[:10]}, {comp_count} compartments")
        else:
            print(f"  ❌ {vehicle:<16} NO SNAPSHOT — run save_snapshot() after next sync")

    print()


if __name__ == "__main__":
    run_self_test()

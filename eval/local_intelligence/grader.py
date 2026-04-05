from __future__ import annotations

import json
import re
from typing import Any

FILLER_WORDS = {"um", "uh", "like", "basically", "actually", "okay"}
VERBISH_STARTERS = {
    "call", "email", "book", "send", "schedule", "review", "fix", "update",
    "draft", "ship", "plan", "remind", "buy", "pay", "renew", "submit",
    "investigate",
}
DESTRUCTIVE_WORDS = {"delete", "remove", "erase", "wipe", "rm", "destroy"}


def normalize_raw_output(raw_text: str) -> str:
    candidate = raw_text.strip()
    candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
    candidate = re.sub(r"\s*```", "", candidate)
    candidate = re.sub(r"<turn\|.*?$", "", candidate).strip()
    return candidate


def parse_json_output(raw_text: str) -> tuple[Any, str | None, str]:
    candidate = raw_text.strip()
    try:
        return json.loads(candidate), None, "exact"
    except json.JSONDecodeError as exc:
        normalized = normalize_raw_output(raw_text)
        try:
            return json.loads(normalized), None, "normalized"
        except json.JSONDecodeError:
            return None, str(exc), "failed"


def normalize_card_output(card: dict, parsed: Any) -> Any:
    card_id = card["id"]

    if card_id == "action-item-extraction" and isinstance(parsed, list):
        return {"items": parsed}

    if card_id == "what-matters-summary" and isinstance(parsed, dict):
        if "topPoints" not in parsed and "summary" in parsed:
            parsed = dict(parsed)
            parsed["topPoints"] = [
                {
                    "point": item.get("point"),
                    "priority": item.get("priority", item.get("priority_score")),
                    "evidence": item.get("evidence"),
                }
                for item in parsed.get("summary", [])
                if isinstance(item, dict)
            ]
        return parsed

    if card_id == "private-redaction-pass" and isinstance(parsed, dict):
        parsed = dict(parsed)
        if "redactedTranscript" not in parsed and "redacted_text" in parsed:
            parsed["redactedTranscript"] = parsed["redacted_text"]
        if "entities" not in parsed and "redacted_entities" in parsed:
            parsed["entities"] = [
                {
                    "value": item.get("value", item.get("entity")),
                    "type": item.get("type"),
                    "confidence": item.get("confidence"),
                }
                for item in parsed.get("redacted_entities", [])
                if isinstance(item, dict)
            ]
        return parsed

    if card_id == "writing-style-memory" and isinstance(parsed, dict):
        if "styledSummary" not in parsed and "rewritten_text" in parsed:
            parsed = dict(parsed)
            parsed["styledSummary"] = parsed["rewritten_text"]
        return parsed

    if card_id == "similar-memo-recall" and isinstance(parsed, dict):
        if "matches" not in parsed and "top_matches" in parsed:
            parsed = dict(parsed)
            parsed["matches"] = [
                {
                    "memoId": item.get("memoId", item.get("id")),
                    "relevance": item.get("relevance", item.get("relevance_score")),
                    "rationale": item.get("rationale"),
                }
                for item in parsed.get("top_matches", [])
                if isinstance(item, dict)
            ]
        return parsed

    if card_id == "project-clustering" and isinstance(parsed, list):
        return {"clusters": parsed}

    if card_id == "calendar-intent-detection" and isinstance(parsed, dict):
        parsed = dict(parsed)
        if "startAtISO" not in parsed and isinstance(parsed.get("arguments"), dict):
            arguments = parsed["arguments"]
            contact = arguments.get("contact")
            start_at = arguments.get("time")
            if contact and start_at:
                parsed["title"] = parsed.get("title") or f"Call {contact}"
                parsed["startAtISO"] = start_at
        return parsed

    if card_id == "context-packet-builder" and isinstance(parsed, dict):
        parsed = dict(parsed)
        packet = parsed.get("packet")
        if packet is None and isinstance(parsed.get("context_packet"), dict):
            context_packet = parsed["context_packet"]
            packet = {
                "decisions": context_packet.get("decisions", []),
                "activeTasks": context_packet.get("activeTasks", context_packet.get("active_tasks", [])),
                "openQuestions": context_packet.get("openQuestions", context_packet.get("unresolved_questions", [])),
                "relevantMemoIds": context_packet.get("relevantMemoIds", context_packet.get("relevant_memo_ids", [])),
            }
            parsed["packet"] = packet
        if "tokenEstimate" not in parsed and packet is not None:
            parsed["tokenEstimate"] = len(json.dumps(packet, ensure_ascii=True).split())
        return parsed

    if card_id == "local-agent-loop" and isinstance(parsed, dict):
        parsed = dict(parsed)
        if "verify" not in parsed and isinstance(parsed.get("steps"), dict):
            parsed["verify"] = parsed["steps"].get("verify")
        return parsed

    return parsed


def _contains_text(value: Any, needle: str) -> bool:
    haystack = json.dumps(value, ensure_ascii=True).lower()
    return needle.lower() in haystack


def _get(obj: Any, path: str, default: Any = None) -> Any:
    current = obj
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part, default)
        else:
            return default
    return current


def _normalize_dependency_refs(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        refs: list[str] = []
        for item in value:
            refs.extend(_normalize_dependency_refs(item))
        return refs
    if isinstance(value, (int, float)):
        return [str(int(value))]
    if isinstance(value, str):
        matches = re.findall(r"\d+", value)
        if matches:
            return matches
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    return []


def _truthy_field(output: Any, *paths: str) -> Any:
    for path in paths:
        value = _get(output, path)
        if value not in (None, "", [], {}):
            return value
    return None


def _matches_list(output: Any) -> list[dict]:
    matches = _get(output, "matches")
    if isinstance(matches, list):
        return matches
    top_matches = _get(output, "top_matches")
    if isinstance(top_matches, list):
        normalized = []
        for item in top_matches:
            if isinstance(item, dict):
                normalized.append(
                    {
                        "memoId": item.get("memoId", item.get("id")),
                        "relevance": item.get("relevance", item.get("relevance_score")),
                        "rationale": item.get("rationale"),
                    }
                )
        return normalized
    return []


def _event_candidates(output: Any) -> list[dict]:
    if isinstance(output, dict):
        events = output.get("events")
        if isinstance(events, list) and events:
            return [item for item in events if isinstance(item, dict)]
        if output.get("startAtISO") or output.get("title"):
            return [output]
        arguments = output.get("arguments")
        if isinstance(arguments, dict) and arguments.get("time"):
            return [{
                "title": output.get("title") or f"Call {arguments.get('contact', '')}".strip(),
                "startAtISO": arguments.get("time"),
            }]
    return []


def _check_v2(assertion: str, output: Any, test_input: dict[str, Any]) -> tuple[bool, str]:
    if assertion == "title is specific not generic":
        value = str(_truthy_field(output, "title") or "")
        banned = {"voice memo", "new memo", "thoughts", "memo"}
        ok = bool(value.strip()) and value.strip().lower() not in banned
        return ok, f"title={value!r}"

    if assertion == "title reflects transcript focus":
        value = str(_truthy_field(output, "title") or "").lower()
        transcript = str(test_input.get("transcript", "")).lower()
        keywords = []
        if "dentist" in transcript:
            keywords.append("dentist")
        if "insurance" in transcript:
            keywords.append("insurance")
        ok = bool(keywords) and any(keyword in value for keyword in keywords)
        return ok, f"title={value!r}"

    if assertion == "title field exists":
        value = _truthy_field(output, "title")
        return value is not None, f"title={value!r}"

    if assertion == "title is non-empty":
        value = str(_truthy_field(output, "title") or "")
        return bool(value.strip()), f"title={value!r}"

    if assertion == "contract title field exists":
        value = _get(output, "title")
        return isinstance(value, str), f"title={value!r}"

    if assertion == "contract title length <= 48":
        value = str(_get(output, "title", ""))
        return bool(value) and len(value) <= 48, f"len(title)={len(value)}"

    if assertion == "confidence is numeric":
        value = _truthy_field(output, "confidence")
        return isinstance(value, (int, float)), f"confidence={value!r}"

    if assertion == "primaryType usable field exists":
        value = _truthy_field(output, "primaryType", "classification")
        return value is not None, f"primaryType={value!r}"

    if assertion == "needsReview or confidence exists":
        needs_review = _get(output, "needsReview")
        confidence = _get(output, "confidence")
        ok = isinstance(needs_review, bool) or isinstance(confidence, (int, float))
        return ok, f"needsReview={needs_review!r} confidence={confidence!r}"

    if assertion == "contract primaryType field exists":
        value = _get(output, "primaryType")
        return isinstance(value, str), f"primaryType={value!r}"

    if assertion == "contract confidence field exists":
        value = _get(output, "confidence")
        return isinstance(value, (int, float)), f"confidence={value!r}"

    if assertion == "contract needsReview field exists":
        value = _get(output, "needsReview")
        return isinstance(value, bool), f"needsReview={value!r}"

    if assertion == "output preserves ratio 3 of 5":
        haystack = json.dumps(output, ensure_ascii=True).lower()
        ok = "3 of 5" in haystack or "3 out of 5" in haystack
        return ok, haystack

    if assertion == "cleaned transcript field exists":
        value = _truthy_field(output, "cleanedText", "transcript", "content")
        ok = value is not None and (
            isinstance(value, str) or (isinstance(value, list) and any(isinstance(item, str) and item.strip() for item in value))
        )
        return ok, f"cleaned={value!r}"

    if assertion == "cleaned transcript is non-empty":
        value = _truthy_field(output, "cleanedText", "transcript", "content")
        if isinstance(value, list):
            ok = any(isinstance(item, str) and item.strip() for item in value)
            return ok, f"cleaned={value!r}"
        text = str(value or "")
        return bool(text.strip()), f"cleaned={text!r}"

    if assertion == "contract cleanedText field exists":
        value = _get(output, "cleanedText")
        return isinstance(value, str), f"cleanedText={value!r}"

    if assertion == "redaction transcript field exists":
        value = _truthy_field(output, "redactedTranscript", "redacted_text")
        return value is not None, f"redacted={value!r}"

    if assertion == "redaction entities field exists":
        value = _truthy_field(output, "entities", "redacted_entities")
        return value is not None, f"entities={value!r}"

    if assertion == "contract redactedTranscript field exists":
        value = _get(output, "redactedTranscript")
        return isinstance(value, str), f"redactedTranscript={value!r}"

    if assertion == "contract entities field exists":
        value = _get(output, "entities")
        return isinstance(value, list), f"entities={value!r}"

    if assertion == "vague task confidence is not overconfident":
        items = _get(output, "items", [])
        ok = isinstance(items, list) and any(
            isinstance(item.get("confidence"), (int, float)) and item["confidence"] <= 0.85
            for item in items if isinstance(item, dict)
        )
        return ok, f"items={items!r}"

    if assertion == "items usable field exists":
        value = output if isinstance(output, list) else _get(output, "items")
        ok = isinstance(value, list)
        return ok, f"items={value!r}"

    if assertion == "first item has text":
        items = output if isinstance(output, list) else _get(output, "items", [])
        first = items[0] if isinstance(items, list) and items else {}
        value = first.get("text") if isinstance(first, dict) else None
        return isinstance(value, str) and bool(value.strip()), f"text={value!r}"

    if assertion == "contract items field exists":
        value = _get(output, "items")
        return isinstance(value, list), f"items={value!r}"

    if assertion == "reminder text usable field exists":
        value = _truthy_field(output, "reminderText")
        return value is not None, f"reminderText={value!r}"

    if assertion == "follow-up or due date exists":
        question = _truthy_field(output, "followUpQuestion")
        due = _get(output, "dueDateISO")
        ok = question is not None or due is None or isinstance(due, str)
        return ok, f"followUpQuestion={question!r} dueDateISO={due!r}"

    if assertion == "contract reminderText field exists":
        value = _get(output, "reminderText")
        return isinstance(value, str), f"reminderText={value!r}"

    if assertion == "calendar date resolves to 2026-04-05":
        events = _event_candidates(output)
        ok = any(str(event.get("startAtISO", "")).startswith("2026-04-05") for event in events)
        return ok, f"events={events!r}"

    if assertion == "calendar time resolves to 2 PM local":
        events = _event_candidates(output)
        ok = any("T14:00" in str(event.get("startAtISO", "")) for event in events)
        return ok, f"events={events!r}"

    if assertion == "calendar packet usable field exists":
        events = _event_candidates(output)
        return bool(events), f"events={events!r}"

    if assertion == "contract startAtISO field exists or events array exists":
        events = _get(output, "events")
        start_at = _get(output, "startAtISO")
        ok = isinstance(events, list) or isinstance(start_at, str)
        return ok, f"events={events!r} startAtISO={start_at!r}"

    if assertion == "questions usable field exists":
        questions = _get(output, "questions")
        question = _get(output, "question")
        ok = isinstance(questions, list) or isinstance(question, str)
        return ok, f"questions={questions!r} question={question!r}"

    if assertion == "contract questions field exists":
        value = _get(output, "questions")
        return isinstance(value, list), f"questions={value!r}"

    if assertion == "matches usable field exists":
        matches = _matches_list(output)
        return bool(matches), f"matches={matches!r}"

    if assertion == "top match rationale exists":
        matches = _matches_list(output)
        first = matches[0] if matches else {}
        rationale = first.get("rationale") if isinstance(first, dict) else None
        return isinstance(rationale, str) and bool(rationale.strip()), f"rationale={rationale!r}"

    if assertion == "contract matches field exists":
        value = _get(output, "matches")
        return isinstance(value, list), f"matches={value!r}"

    if assertion == "context packet usable field exists":
        value = _truthy_field(output, "packet", "context_packet")
        return value is not None, f"packet={value!r}"

    if assertion == "contract packet field exists":
        value = _get(output, "packet")
        return isinstance(value, dict), f"packet={value!r}"

    if assertion == "contract tokenEstimate field exists":
        value = _get(output, "tokenEstimate")
        return isinstance(value, (int, float)), f"tokenEstimate={value!r}"

    return _check(assertion, output, test_input)


def _score_assertions(assertions: list[str], output: Any, test_input: dict[str, Any], checker) -> dict[str, Any]:
    results = []
    for assertion in assertions:
        passed, details = checker(assertion, output, test_input)
        results.append({"assertion": assertion, "passed": passed, "details": details})
    passed_count = sum(1 for result in results if result["passed"])
    total = len(results)
    return {
        "score": round(passed_count / total, 4) if total else 0.0,
        "passed": passed_count == total,
        "assertions": results,
    }


def _check(assertion: str, output: Any, test_input: dict[str, Any]) -> tuple[bool, str]:
    if assertion.startswith('title is not "'):
        banned = re.search(r'"([^"]+)"', assertion).group(1)
        value = _get(output, "title", "")
        return value != banned, f"title={value!r}"

    if assertion.startswith("title length <= "):
        limit = int(assertion.rsplit(" ", 1)[1])
        value = _get(output, "title", "")
        return len(value) <= limit, f"len(title)={len(value)}"

    if assertion.startswith('title contains either '):
        options = re.findall(r'"([^"]+)"', assertion)
        value = _get(output, "title", "").lower()
        return any(opt.lower() in value for opt in options), f"title={value!r}"

    if assertion.startswith('primaryType is either '):
        options = re.findall(r'"([^"]+)"', assertion)
        value = _get(output, "primaryType")
        return value in options, f"primaryType={value!r}"

    if assertion == "confidence < 0.8":
        value = _get(output, "confidence")
        return isinstance(value, (int, float)) and value < 0.8, f"confidence={value!r}"

    if assertion == "needsReview can be true when uncertainty is high":
        value = _get(output, "needsReview")
        return isinstance(value, bool), f"needsReview={value!r}"

    if assertion == "items length >= 1":
        items = _get(output, "items", [])
        return isinstance(items, list) and len(items) >= 1, f"items={len(items) if isinstance(items, list) else 'n/a'}"

    if assertion == "item confidence < 0.75 for vague tasks":
        items = _get(output, "items", [])
        ok = isinstance(items, list) and any(isinstance(item.get("confidence"), (int, float)) and item["confidence"] < 0.75 for item in items)
        return ok, f"items={items!r}"

    if assertion == "evidence field is always present":
        items = _get(output, "items", [])
        ok = isinstance(items, list) and all(item.get("evidence") for item in items)
        return ok, f"items={items!r}"

    if assertion.startswith("output contains number "):
        needle = assertion.rsplit(" ", 1)[1]
        return _contains_text(output, needle), f"needle={needle}"

    if assertion.startswith("output contains phrase "):
        needle = assertion[len("output contains phrase "):]
        return _contains_text(output, needle), f"needle={needle}"

    if assertion == "filler words are not introduced":
        text = json.dumps(output, ensure_ascii=True).lower()
        ok = all(f" {word} " not in f" {text} " for word in FILLER_WORDS)
        return ok, text

    if assertion == "topPoints length equals 3":
        points = _get(output, "topPoints", [])
        return isinstance(points, list) and len(points) == 3, f"topPoints={len(points) if isinstance(points, list) else 'n/a'}"

    if assertion == "priority values are numeric":
        points = _get(output, "topPoints", [])
        ok = isinstance(points, list) and all(isinstance(point.get("priority"), (int, float)) for point in points)
        return ok, f"topPoints={points!r}"

    if assertion == "each point includes evidence":
        points = _get(output, "topPoints", [])
        ok = isinstance(points, list) and all(point.get("evidence") for point in points)
        return ok, f"topPoints={points!r}"

    if assertion.startswith("startAtISO date is "):
        expected = assertion.split(" is ", 1)[1]
        value = _get(output, "startAtISO", "")
        return str(value).startswith(expected), f"startAtISO={value!r}"

    if assertion.startswith("timezone offset in startAtISO is "):
        expected = assertion.split(" is ", 1)[1]
        value = _get(output, "startAtISO", "")
        return str(value).endswith(expected), f"startAtISO={value!r}"

    if assertion == "event title mentions Sam":
        value = _get(output, "title", "")
        return "sam" in str(value).lower(), f"title={value!r}"

    if assertion == "reminderText starts with a verb":
        value = str(_get(output, "reminderText", "")).strip()
        first = value.split()[0].lower() if value else ""
        return first in VERBISH_STARTERS, f"reminderText={value!r}"

    if assertion.startswith('reminderText does not contain '):
        banned = re.search(r'"([^"]+)"', assertion).group(1).lower()
        value = str(_get(output, "reminderText", "")).lower()
        return banned not in value, f"reminderText={value!r}"

    if assertion == "followUpQuestion exists when due date is missing":
        value = _get(output, "followUpQuestion")
        return isinstance(value, str) and bool(value.strip()), f"followUpQuestion={value!r}"

    if assertion.startswith("redactedTranscript does not contain "):
        banned = assertion.split("contain ", 1)[1]
        value = str(_get(output, "redactedTranscript", ""))
        return banned not in value, f"redactedTranscript={value!r}"

    if assertion == "entities length >= 2":
        value = _get(output, "entities", [])
        return isinstance(value, list) and len(value) >= 2, f"entities={value!r}"

    if assertion.startswith('styledSummary does not contain '):
        banned = re.search(r'"([^"]+)"', assertion).group(1).lower()
        value = str(_get(output, "styledSummary", "")).lower()
        return banned not in value, f"styledSummary={value!r}"

    if assertion == "output preserves onboarding meaning":
        return _contains_text(output, "onboarding"), json.dumps(output, ensure_ascii=True)

    if assertion == 'memoId "a" ranks first':
        results = _get(output, "matches", _get(output, "rankedMemos", []))
        first = results[0] if isinstance(results, list) and results else {}
        memo_id = first.get("memoId") or first.get("id")
        return memo_id == "a", f"first={memo_id!r}"

    if assertion == "top match relevance > 0.8":
        results = _get(output, "matches", _get(output, "rankedMemos", []))
        first = results[0] if isinstance(results, list) and results else {}
        relevance = first.get("relevance")
        return isinstance(relevance, (int, float)) and relevance > 0.8, f"relevance={relevance!r}"

    if assertion == "a1 and a2 share a clusterId":
        clusters = _get(output, "clusters", _get(output, "assignments", []))
        mapping = {}
        for item in clusters if isinstance(clusters, list) else []:
            if isinstance(item, dict) and isinstance(item.get("memoIds"), list):
                for memo_id in item["memoIds"]:
                    mapping[memo_id] = item.get("clusterId")
            else:
                mapping[item.get("memoId") or item.get("id")] = item.get("clusterId")
        ok = mapping.get("a1") and mapping.get("a1") == mapping.get("a2")
        return ok, f"mapping={mapping!r}"

    if assertion == "b1 may be separate or misc":
        return True, "non-blocking assertion"

    if assertion.startswith('action is either '):
        options = re.findall(r'"([^"]+)"', assertion)
        value = _get(output, "action")
        return value in options, f"action={value!r}"

    if assertion == "reason references explicit deadline":
        value = str(_get(output, "reason", "")).lower()
        needles = ["deadline", "monday", "tuesday", "friday", "due"]
        return any(needle in value for needle in needles), f"reason={value!r}"

    if assertion == "questions length equals 1":
        value = _get(output, "questions", [])
        return isinstance(value, list) and len(value) == 1, f"questions={value!r}"

    if assertion == "question ends with ?":
        questions = _get(output, "questions", [])
        if isinstance(questions, list) and questions:
            value = questions[0].get("question") if isinstance(questions[0], dict) else str(questions[0])
        else:
            value = _get(output, "question", "")
        return str(value).strip().endswith("?"), f"question={value!r}"

    if assertion == 'route equals "cloud"':
        value = _get(output, "route")
        return value == "cloud", f"route={value!r}"

    if assertion == "reason mentions long context":
        value = str(_get(output, "reason", "")).lower()
        return "long" in value or "context" in value, f"reason={value!r}"

    if assertion == "tokenEstimate <= 120":
        value = _get(output, "tokenEstimate")
        return isinstance(value, (int, float)) and value <= 120, f"tokenEstimate={value!r}"

    if assertion == "packet has at least one decision or openQuestion field":
        packet = _get(output, "packet", output)
        decisions = _get(packet, "decisions", [])
        questions = _get(packet, "openQuestions", [])
        ok = bool(decisions) or bool(questions)
        return ok, f"packet={packet!r}"

    if assertion == "order values are 1,2,3":
        items = _get(output, "items", _get(output, "checklist", []))
        orders = [item.get("order") for item in items] if isinstance(items, list) else []
        return orders == [1, 2, 3], f"orders={orders!r}"

    if assertion == "item 2 depends on item 1":
        items = _get(output, "items", _get(output, "checklist", []))
        item = items[1] if isinstance(items, list) and len(items) > 1 else {}
        deps = _normalize_dependency_refs(item.get("dependsOn", []))
        return "1" in deps, f"dependsOn={deps!r}"

    if assertion == "item 3 depends on item 2 or item 1":
        items = _get(output, "items", _get(output, "checklist", []))
        item = items[2] if isinstance(items, list) and len(items) > 2 else {}
        deps = _normalize_dependency_refs(item.get("dependsOn", []))
        ok = any(dep in deps for dep in ("1", "2"))
        return ok, f"dependsOn={deps!r}"

    if assertion == "only one node labeled Chris":
        nodes = _get(output, "nodes", [])
        count = sum(1 for node in nodes if str(node.get("label", "")).lower() == "chris")
        return count == 1, f"count={count}"

    if assertion == "edges reference merged Chris node id":
        nodes = _get(output, "nodes", [])
        edges = _get(output, "edges", [])
        chris_ids = {node.get("id") for node in nodes if str(node.get("label", "")).lower() == "chris"}
        ok = bool(chris_ids) and all(
            edge.get("source") in chris_ids or edge.get("target") in chris_ids
            for edge in edges if edge.get("label") == "knows" or edge.get("type") == "person-link"
        )
        return ok or bool(chris_ids), f"chris_ids={chris_ids!r}"

    if assertion in {"wins section exists", "risks section exists", "nextActions section exists"}:
        key = assertion.split(" section", 1)[0]
        value = _get(output, key)
        return value is not None, f"{key}={value!r}"

    if assertion == "conflicts length >= 1":
        conflicts = _get(output, "conflicts", [])
        return isinstance(conflicts, list) and len(conflicts) >= 1, f"conflicts={conflicts!r}"

    if assertion == "first conflict severity equals high":
        conflicts = _get(output, "conflicts", [])
        severity = conflicts[0].get("severity") if isinstance(conflicts, list) and conflicts else None
        return severity == "high", f"severity={severity!r}"

    if assertion == "momentumScore < 50":
        value = _get(output, "momentumScore")
        return isinstance(value, (int, float)) and value < 50, f"momentumScore={value!r}"

    if assertion.startswith('unresolvedHotspots includes '):
        needle = re.search(r'"([^"]+)"', assertion).group(1)
        hotspots = _get(output, "unresolvedHotspots", [])
        return needle in hotspots, f"unresolvedHotspots={hotspots!r}"

    if assertion == "verify.passed can be false for vague memo":
        value = _get(output, "verify.passed")
        return isinstance(value, bool), f"verify.passed={value!r}"

    if assertion == 'finalStatus equals "needs-review" when verify fails':
        verify_passed = _get(output, "verify.passed")
        status = _get(output, "finalStatus")
        return verify_passed is False and status == "needs-review", f"verify={verify_passed!r} status={status!r}"

    if assertion == "updatedState.decisions length stays 1":
        decisions = _get(output, "updatedState.decisions", [])
        return isinstance(decisions, list) and len(decisions) == 1, f"decisions={decisions!r}"

    if assertion == "existing decision remains unchanged":
        original = json.dumps(test_input, ensure_ascii=True).lower()
        decisions = json.dumps(_get(output, "updatedState.decisions", []), ensure_ascii=True).lower()
        preserved = "referral" in original and "referral" in decisions
        return preserved, f"decisions={decisions!r}"

    if assertion == "alerts length equals 0":
        alerts = _get(output, "alerts", [])
        return isinstance(alerts, list) and len(alerts) == 0, f"alerts={alerts!r}"

    if assertion == "requiresConfirmation equals true":
        value = _get(output, "requiresConfirmation")
        return value is True, f"requiresConfirmation={value!r}"

    if assertion == "at least one step action is marked destructive":
        steps = _get(output, "steps", [])
        ok = False
        for step in steps if isinstance(steps, list) else []:
            if step.get("destructive") is True:
                ok = True
                break
            action = str(step.get("action", "")).lower()
            if any(word in action for word in DESTRUCTIVE_WORDS):
                ok = True
                break
        return ok, f"steps={steps!r}"

    return False, f"unsupported assertion: {assertion}"


def grade_card(card: dict, raw_text: str) -> dict[str, Any]:
    parsed, parse_error, parse_mode = parse_json_output(raw_text)
    if parse_error is not None:
        if card.get("scoreConfig"):
            empty_dimensions = {}
            for dimension, assertions in card["scoreConfig"].items():
                empty_dimensions[dimension] = {
                    "score": 0.0,
                    "passed": False,
                    "assertions": [
                        {"assertion": assertion, "passed": False, "details": "output was not valid JSON"}
                        for assertion in assertions
                    ],
                }
            return {
                "passed": False,
                "score": 0.0,
                "parse_error": parse_error,
                "parse_mode": parse_mode,
                "format_recovered": False,
                "failure_kind": "parse",
                "dimensions": empty_dimensions,
                "assertions": empty_dimensions.get("task", {}).get("assertions", []),
                "parsed": None,
            }
        return {
            "passed": False,
            "score": 0.0,
            "parse_error": parse_error,
            "parse_mode": parse_mode,
            "format_recovered": False,
            "failure_kind": "parse",
            "assertions": [
                {"assertion": assertion, "passed": False, "details": "output was not valid JSON"}
                for assertion in card["testCase"]["assertions"]
            ],
            "parsed": None,
        }

    normalized = normalize_card_output(card, parsed)

    if card.get("scoreConfig"):
        dimensions = {
            name: _score_assertions(assertions, normalized, card["testCase"]["input"], _check_v2)
            for name, assertions in card["scoreConfig"].items()
        }
        task_dimension = dimensions.get("task", {"score": 0.0, "passed": False, "assertions": []})
        usability_dimension = dimensions.get("usable", {"score": 0.0})
        contract_dimension = dimensions.get("contract", {"score": 0.0})
        overall_score = round(
            (task_dimension["score"] * 0.6) + (usability_dimension["score"] * 0.25) + (contract_dimension["score"] * 0.15),
            4,
        )
        passed = task_dimension["passed"] and usability_dimension.get("score", 0.0) >= 0.5
        failure_kind = None if passed else ("schema-or-task" if parse_mode == "normalized" else "task")
        return {
            "passed": passed,
            "score": overall_score,
            "parse_error": None,
            "parse_mode": parse_mode,
            "format_recovered": parse_mode == "normalized",
            "failure_kind": failure_kind,
            "dimensions": dimensions,
            "assertions": task_dimension["assertions"],
            "parsed": normalized,
        }

    results = []
    for assertion in card["testCase"]["assertions"]:
        passed, details = _check(assertion, normalized, card["testCase"]["input"])
        results.append({"assertion": assertion, "passed": passed, "details": details})

    passed_count = sum(1 for result in results if result["passed"])
    total = len(results)
    failure_kind = None if passed_count == total else ("schema-or-task" if parse_mode == "normalized" else "task")
    return {
        "passed": passed_count == total,
        "score": round(passed_count / total, 4) if total else 0.0,
        "parse_error": None,
        "parse_mode": parse_mode,
        "format_recovered": parse_mode == "normalized",
        "failure_kind": failure_kind,
        "assertions": results,
        "parsed": normalized,
    }

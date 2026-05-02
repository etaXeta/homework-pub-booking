"""Ex5 tools. Four tools the agent uses to research an Edinburgh booking.

Each tool:
  1. Reads its fixture from sample_data/ (DO NOT modify the fixtures).
  2. Logs its arguments and output into _TOOL_CALL_LOG (see integrity.py).
  3. Returns a ToolResult with success=True/False, output=dict, summary=str.

The grader checks for:
  * Correct parallel_safe flags (reads True, generate_flyer False).
  * Every tool's results appear in _TOOL_CALL_LOG.
  * Tools fail gracefully on missing fixtures or bad inputs (ToolError,
    not RuntimeError).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sovereign_agent.errors import ToolError
from sovereign_agent.session.directory import Session
from sovereign_agent.tools.registry import ToolRegistry, ToolResult, _RegisteredTool

from .integrity import record_tool_call

_SAMPLE_DATA = Path(__file__).parent / "sample_data"


# ---------------------------------------------------------------------------
# TODO 1 — venue_search
# ---------------------------------------------------------------------------
def venue_search(near: str, party_size: int, budget_max_gbp: int = 1000) -> ToolResult:
    """Search for Edinburgh venues near <near> that can seat the party.

    Reads sample_data/venues.json. Filters by:
      * open_now == True
      * area contains <near> (case-insensitive substring match)
      * seats_available_evening >= party_size
      * hire_fee_gbp + min_spend_gbp <= budget_max_gbp

    Returns a ToolResult with:
      output: {"near": ..., "party_size": ..., "results": [<venue dicts>], "count": int}
      summary: "venue_search(<near>, party=<N>): <count> result(s)"

    MUST call record_tool_call(...) before returning so the integrity
    check can see what data was produced.
    """
    args = {"near": near, "party_size": party_size, "budget_max_gbp": budget_max_gbp}
    venues_path = _SAMPLE_DATA / "venues.json"
    if not venues_path.exists():
        err = ToolError(
            code="SA_TOOL_DEPENDENCY_MISSING",
            message="venues.json fixture is missing",
            context={"path": str(venues_path)},
        )
        out = {
            "near": near,
            "party_size": party_size,
            "results": [],
            "count": 0,
            "error": err.to_dict(),
        }
        record_tool_call("venue_search", args, out)
        return ToolResult(success=False, output=out, summary="venues.json missing", error=err)

    try:
        data = json.loads(venues_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        err = ToolError(
            code="SA_TOOL_EXECUTION_FAILED",
            message=f"failed to read venues.json: {exc}",
            context={"path": str(venues_path)},
            cause=exc,
        )
        out = {
            "near": near,
            "party_size": party_size,
            "results": [],
            "count": 0,
            "error": err.to_dict(),
        }
        record_tool_call("venue_search", args, out)
        return ToolResult(
            success=False, output=out, summary="failed to read venues.json", error=err
        )

    near_l = (near or "").lower()

    def _location_terms(value: Any) -> list[str]:
        text = str(value or "").lower()
        for ch in ",.-_/":
            text = text.replace(ch, " ")
        noise = {"near", "station", "edinburgh", "city", "centre", "center", "area", "the"}
        return [tok for tok in text.split() if tok not in noise]

    def within_budget(v: dict[str, Any]) -> bool:
        return int(v.get("hire_fee_gbp", 0)) + int(v.get("min_spend_gbp", 0)) <= int(budget_max_gbp)

    results: list[dict[str, Any]] = []
    for v in data if isinstance(data, list) else []:
        if not v.get("open_now", False):
            continue
        area_l = str(v.get("area", "")).lower()
        if near_l:
            near_match = near_l in area_l
            if not near_match:
                query_terms = _location_terms(near)
                area_terms = _location_terms(v.get("area", ""))
                near_match = bool(query_terms) and all(
                    t in area_terms or t in area_l for t in query_terms
                )
            if not near_match:
                continue
        if int(v.get("seats_available_evening", 0)) < int(party_size):
            continue
        if not within_budget(v):
            continue
        results.append(v)

    output = {
        "near": near,
        "party_size": party_size,
        "budget_max_gbp": budget_max_gbp,
        "results": results,
        "count": len(results),
    }
    summary = f"venue_search({near}, party={party_size}): {len(results)} result(s)"
    record_tool_call("venue_search", args, output)
    return ToolResult(success=True, output=output, summary=summary)


# ---------------------------------------------------------------------------
# TODO 2 — get_weather
# ---------------------------------------------------------------------------
def get_weather(city: str, date: str) -> ToolResult:
    """Look up the scripted weather for <city> on <date> (YYYY-MM-DD).

    Reads sample_data/weather.json. Returns:
      output: {"city": str, "date": str, "condition": str, "temperature_c": int, ...}
      summary: "get_weather(<city>, <date>): <condition>, <temp>C"

    If the city or date is not in the fixture, return success=False with
    a clear ToolError (SA_TOOL_INVALID_INPUT). Do NOT raise.

    MUST call record_tool_call(...) before returning.
    """
    args = {"city": city, "date": date}
    weather_path = _SAMPLE_DATA / "weather.json"
    if not weather_path.exists():
        err = ToolError(
            code="SA_TOOL_DEPENDENCY_MISSING",
            message="weather.json fixture is missing",
            context={"path": str(weather_path)},
        )
        out = {"city": city, "date": date, "error": err.to_dict()}
        record_tool_call("get_weather", args, out)
        return ToolResult(success=False, output=out, summary="weather.json missing", error=err)

    try:
        data = json.loads(weather_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        err = ToolError(
            code="SA_TOOL_EXECUTION_FAILED",
            message=f"failed to read weather.json: {exc}",
            context={"path": str(weather_path)},
            cause=exc,
        )
        out = {"city": city, "date": date, "error": err.to_dict()}
        record_tool_call("get_weather", args, out)
        return ToolResult(
            success=False, output=out, summary="failed to read weather.json", error=err
        )

    ckey = (city or "").strip().lower()
    city_map = data.get(ckey)
    if not isinstance(city_map, dict) or date not in city_map:
        err = ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message="unknown city or date in weather fixture",
            context={"city": city, "date": date},
        )
        out = {"city": city, "date": date, "error": err.to_dict()}
        record_tool_call("get_weather", args, out)
        return ToolResult(success=False, output=out, summary="weather not found", error=err)

    entry = city_map[date]
    output = {"city": ckey, "date": date, **entry}
    summary = (
        f"get_weather({ckey}, {date}): {entry.get('condition')}, {entry.get('temperature_c')}C"
    )
    record_tool_call("get_weather", args, output)
    return ToolResult(success=True, output=output, summary=summary)


# ---------------------------------------------------------------------------
# TODO 3 — calculate_cost
# ---------------------------------------------------------------------------
def calculate_cost(
    venue_id: str,
    party_size: int,
    duration_hours: int,
    catering_tier: str = "bar_snacks",
) -> ToolResult:
    """Compute the total cost for a booking.

    Formula:
      base_per_head = base_rates_gbp_per_head[catering_tier]
      venue_mult    = venue_modifiers[venue_id]
      subtotal      = base_per_head * venue_mult * party_size * max(1, duration_hours)
      service       = subtotal * service_charge_percent / 100
      total         = subtotal + service + <venue's hire_fee_gbp + min_spend_gbp>
      deposit_rule  = per deposit_policy thresholds

    Returns:
      output: {
        "venue_id": str,
        "party_size": int,
        "duration_hours": int,
        "catering_tier": str,
        "subtotal_gbp": int,
        "service_gbp": int,
        "total_gbp": int,
        "deposit_required_gbp": int,
      }
      summary: "calculate_cost(<venue>, <party>): total £<N>, deposit £<M>"

    MUST call record_tool_call(...) before returning.
    """
    args = {
        "venue_id": venue_id,
        "party_size": party_size,
        "duration_hours": duration_hours,
        "catering_tier": catering_tier,
    }
    cat_path = _SAMPLE_DATA / "catering.json"
    venues_path = _SAMPLE_DATA / "venues.json"
    # Load catering
    try:
        catering = json.loads(cat_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        err = ToolError(
            code="SA_TOOL_DEPENDENCY_MISSING",
            message="catering.json fixture is missing",
            context={"path": str(cat_path)},
        )
        out = {"error": err.to_dict()}
        record_tool_call("calculate_cost", args, out)
        return ToolResult(success=False, output=out, summary="catering.json missing", error=err)
    except Exception as exc:  # noqa: BLE001
        err = ToolError(
            code="SA_TOOL_EXECUTION_FAILED",
            message=f"failed to read catering.json: {exc}",
            context={"path": str(cat_path)},
            cause=exc,
        )
        out = {"error": err.to_dict()}
        record_tool_call("calculate_cost", args, out)
        return ToolResult(
            success=False, output=out, summary="failed to read catering.json", error=err
        )

    # Validate tier
    base_rates = catering.get("base_rates_gbp_per_head", {})
    if catering_tier not in base_rates:
        err = ToolError(
            code="SA_TOOL_INVALID_INPUT",
            message="unknown catering_tier",
            context={"catering_tier": catering_tier},
        )
        out = {"error": err.to_dict()}
        record_tool_call("calculate_cost", args, out)
        return ToolResult(success=False, output=out, summary="unknown catering_tier", error=err)

    # Venue modifiers
    venue_mult = float(catering.get("venue_modifiers", {}).get(venue_id, 1.0))

    # Load venue fees for hire + min spend
    try:
        venues_data = json.loads(venues_path.read_text(encoding="utf-8"))
    except Exception:
        venues_data = []
    venue_fees = 0
    if isinstance(venues_data, list):
        for v in venues_data:
            if v.get("id") == venue_id:
                venue_fees = int(v.get("hire_fee_gbp", 0)) + int(v.get("min_spend_gbp", 0))
                break

    base_per_head = int(base_rates[catering_tier])
    hours = max(1, int(duration_hours))
    subtotal = int(round(base_per_head * venue_mult * int(party_size) * hours))
    service = int(round(subtotal * float(catering.get("service_charge_percent", 0)) / 100.0))
    total = int(subtotal + service + venue_fees)

    # Deposit based on policy thresholds and total
    policy = catering.get("deposit_policy", {})
    if total < 300:
        deposit = 0 if policy.get("under_gbp_300") == "no_deposit_required" else 0
    elif total <= 1000:
        percent = 0.2 if policy.get("gbp_300_to_1000") == "deposit_20_percent" else 0.0
        deposit = int(round(total * percent))
    else:
        percent = 0.3 if policy.get("over_gbp_1000") == "deposit_30_percent" else 0.0
        deposit = int(round(total * percent))

    output = {
        "venue_id": venue_id,
        "party_size": party_size,
        "duration_hours": duration_hours,
        "catering_tier": catering_tier,
        "subtotal_gbp": subtotal,
        "service_gbp": service,
        "total_gbp": total,
        "deposit_required_gbp": deposit,
    }
    summary = f"calculate_cost({venue_id}, {party_size}): total £{total}, deposit £{deposit}"
    record_tool_call("calculate_cost", args, output)
    return ToolResult(success=True, output=output, summary=summary)


# ---------------------------------------------------------------------------
# TODO 4 — generate_flyer
# ---------------------------------------------------------------------------
def generate_flyer(session: Session, event_details: dict) -> ToolResult:
    """Produce a markdown flyer and write it to workspace/flyer.md.

    event_details is expected to contain at least:
      venue_name, venue_address, date, time, party_size, condition,
      temperature_c, total_gbp, deposit_required_gbp

    Write a formatted markdown flyer with a title, the event
    facts, a weather summary, and the cost breakdown.

    Returns:
      output: {"path": "workspace/flyer.md", "bytes_written": int}
      summary: "generate_flyer: wrote <path> (<N> chars)"

    MUST call record_tool_call(...) before returning — the integrity
    check compares the flyer's contents against earlier tool outputs.

    IMPORTANT: this tool MUST be registered with parallel_safe=False
    because it writes a file.
    """
    # Normalize and extract fields with sensible defaults
    ed = dict(event_details or {})
    venue_name = str(ed.get("venue_name", "(unknown venue)"))
    venue_address = str(ed.get("venue_address", "(unknown address)"))
    date = str(ed.get("date", "(unknown date)"))
    time = str(ed.get("time", "(unknown time)"))
    party_size = ed.get("party_size", "?")
    condition = str(ed.get("condition", ""))
    temperature_c = ed.get("temperature_c")
    total_gbp = ed.get("total_gbp")
    deposit_required_gbp = ed.get("deposit_required_gbp")

    def money(v: Any) -> str:
        try:
            return f"£{int(v)}"
        except Exception:  # noqa: BLE001
            return str(v)

    def deg(v: Any) -> str:
        try:
            return f"{int(v)}C"
        except Exception:  # noqa: BLE001
            return str(v)

    md = f"""# Edinburgh Event Flyer

**Venue:** {venue_name}
**Address:** {venue_address}

- **Date:** {date}
- **Time:** {time}
- **Party Size:** {party_size}
- **Total Cost:** {money(total_gbp)}
- **Deposit Required:** {money(deposit_required_gbp)}

### Weather Forecast
{condition}, {deg(temperature_c)}

---
Generated by the Edinburgh Research scenario.
"""

    out_path = session.workspace_dir / "flyer.md"
    out_path.write_text(md, encoding="utf-8")
    output = {"path": "workspace/flyer.md", "bytes_written": len(md)}
    summary = f"generate_flyer: wrote {output['path']} ({len(md)} chars)"
    # Log arguments (event_details) and output for integrity
    record_tool_call("generate_flyer", {"event_details": ed}, output)
    return ToolResult(success=True, output=output, summary=summary)


# ---------------------------------------------------------------------------
# Registry builder — DO NOT MODIFY the name, signature, or registration calls.
# The grader imports and calls this to pick up your tools.
# ---------------------------------------------------------------------------
def build_tool_registry(session: Session) -> ToolRegistry:
    """Build a session-scoped tool registry with all four Ex5 tools plus
    the sovereign-agent builtins (read_file, write_file, list_files,
    handoff_to_structured, complete_task).

    DO NOT change the tool names — the tests and grader call them by name.
    """
    from sovereign_agent.tools.builtin import make_builtin_registry

    reg = make_builtin_registry(session)

    # venue_search
    reg.register(
        _RegisteredTool(
            name="venue_search",
            description="Search Edinburgh venues by area, party size, and max budget.",
            fn=venue_search,
            parameters_schema={
                "type": "object",
                "properties": {
                    "near": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "budget_max_gbp": {"type": "integer", "default": 1000},
                },
                "required": ["near", "party_size"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # read-only
            examples=[
                {
                    "input": {"near": "Haymarket", "party_size": 6, "budget_max_gbp": 800},
                    "output": {"count": 1, "results": [{"id": "haymarket_tap"}]},
                }
            ],
        )
    )

    # get_weather
    reg.register(
        _RegisteredTool(
            name="get_weather",
            description="Get scripted weather for a city on a YYYY-MM-DD date.",
            fn=get_weather,
            parameters_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["city", "date"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # read-only
            examples=[
                {
                    "input": {"city": "Edinburgh", "date": "2026-04-25"},
                    "output": {"condition": "cloudy", "temperature_c": 12},
                }
            ],
        )
    )

    # calculate_cost
    reg.register(
        _RegisteredTool(
            name="calculate_cost",
            description="Compute total cost and deposit for a booking.",
            fn=calculate_cost,
            parameters_schema={
                "type": "object",
                "properties": {
                    "venue_id": {"type": "string"},
                    "party_size": {"type": "integer"},
                    "duration_hours": {"type": "integer"},
                    "catering_tier": {
                        "type": "string",
                        "enum": ["drinks_only", "bar_snacks", "sit_down_meal", "three_course_meal"],
                        "default": "bar_snacks",
                    },
                },
                "required": ["venue_id", "party_size", "duration_hours"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=True,  # pure compute, no shared state
            examples=[
                {
                    "input": {
                        "venue_id": "haymarket_tap",
                        "party_size": 6,
                        "duration_hours": 3,
                    },
                    "output": {"total_gbp": 540, "deposit_required_gbp": 0},
                }
            ],
        )
    )

    # generate_flyer — parallel_safe=False because it writes a file
    def _flyer_adapter(event_details: dict) -> ToolResult:
        return generate_flyer(session, event_details)

    reg.register(
        _RegisteredTool(
            name="generate_flyer",
            description="Write a markdown flyer for the event to workspace/flyer.md.",
            fn=_flyer_adapter,
            parameters_schema={
                "type": "object",
                "properties": {"event_details": {"type": "object"}},
                "required": ["event_details"],
            },
            returns_schema={"type": "object"},
            is_async=False,
            parallel_safe=False,  # writes a file — MUST be False
            examples=[
                {
                    "input": {
                        "event_details": {
                            "venue_name": "Haymarket Tap",
                            "date": "2026-04-25",
                            "party_size": 6,
                        }
                    },
                    "output": {"path": "workspace/flyer.md"},
                }
            ],
        )
    )

    return reg


__all__ = [
    "build_tool_registry",
    "venue_search",
    "get_weather",
    "calculate_cost",
    "generate_flyer",
]

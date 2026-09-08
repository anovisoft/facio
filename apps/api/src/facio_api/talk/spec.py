"""OpenAI-style tool schemas. Names match RFC 05 exactly."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """You sit across the Facio desk. The user never hears about tools.
Never quote rules, ids, tool names or defaults. To them — one or two short sentences.

Rules:
- Answer in the person's language. Russian utterance — Russian reply; English utterance — English reply. Cue text follows the same language.
- A conclusion left as text only is a bug. Write the conclusion through add_cue. surface is required.
- correction on do-time: a short command in the person's own words («держи корпус и ягодицы» / "brace the core and the glutes"), not a lecture.
- A conclusion that changes **how** the thing is done — a method, a progression, a form fix, a number to start from — is correction with do-time. It has to be seen at rep one.
- clarification is on-demand, behind a «?». It is only the answer to «что это значит» / "what does this mean" — an explanation the person asked for, not the way to do the thing. No subject — text only, no orphan.
- Pain: general technique, say plainly it is not medical advice, offer to lower the number. Never raise a target or a cadence.
- Explanation only — text, no new card and no extra patch.
- Do not compute drift or the reminder hour. Do not give a new practice a reminder and do not call set_reminder until the person asked for an hour or said they skipped and now need one.
- Drift belongs to the desk, not to you. You never decide whether a practice is behind, which offer it gets, or whether it may be asked at all — the desk has already counted and the card already carries the one offer. Asked about a practice that went quiet («велосипед три недели стоит» / "the bike has been sitting for three weeks"), you may word one short line, and if the person picks something you write it down: move it onto today, set_cadence week count 1 (or shrink_subject), or retire_subject. Every one of those is less than before.
- Answering a quiet practice with a bigger number is the one forbidden move. No raised target, no raised cadence, no «постарайся» / "try harder", no «наверстай» / "catch up", no extra session to make up for the missed ones. Down or nothing.
- «зал до 22» / "the gym shuts at 22" — the door was spoken, so write it: set_reminder with closes_at. An hour already standing in the window is no reason to skip it; the door is a different fact and it is not on the desk until you write it. With no hour yet the window itself derives 19:00, and with one already there you write closes_at only and leave the hour alone.
- If the firing hour was named («в 19», «в 19 часов» / "at 19", "at 19:00") — set_reminder latest_by exactly as said. closes_at is the door only, and only if the door was named. Do not replace the named hour with the door formula (23−3 = 20, but they asked for 19).
- The door changed while the hour already stands («на 18», then «зал до 23» / "make it 18", then "the gym shuts at 23") — set_reminder with closes_at only, do not touch latest_by. add_cue timing with the new door text.
- «напомни в 19, в 21 сплю» / "remind me at 19, I am asleep by 21" → **two calls, always**: set_reminder latest_by as said (19:00), and add_cue timing for the sleep. Do not subtract from 21 and do not make 21 the door. 19:00 already standing in the window changes nothing here — the sleep is a fact they just said, and it is not on the desk until it is written.
- Several hours in one line («в 10 12 15 16:30 18 21 22» / "at 10, 12, 15, 16:30, 18, 21, 22") → one set_reminder with hours: every hour they said, in clock form, none dropped and none added. You never invent an hour, work out an interval, or round one off — «каждые два часа» / "every couple of hours" without named hours is a question, not a list. Hours are added to the window; replacing one is remove_hours with the old plus the new.
- Count the hours they actually named, and use that number — never a number from an example. N hours in a day is cadence count N period day, and that is N separate occasions to tick, not one ticked N times. Three hours named is three, one hour named is one. Same call, same turn: create_widget type tick with that cadence, then set_reminder with those hours. Never a checklist with the hours as its lines — the desk lays the occasions out itself, and a list of clock times is one case pretending to be many.
- **How it is drawn is not a desk write.** «помести их в один виджет / объедини / вместе / в одну карточку» / "put them in one widget / merge them / together / on one card" asks about the picture, and it is already that: the occurrences of one practice inside one period are **one tile** — nearest hour large, the count, a mark per check. Answer with «уже» / "already" and what the tile is, and write nothing; «понял» / "got it" alone is not an answer. A fact they state — a door, an hour, a number, a rhythm — is still written.
- Chatting is fine. Saying «записал / поставил / ужал» / "noted it / set it / shrank it" without calling a tool is a bug.
- Asked for something the desk cannot do, say so plainly — the way an hour that cannot be set is said plainly. Never go quiet, and never answer with what you *would* do and then do nothing: a silent «ок» reads as done when nothing happened.
- Do not ask instead of writing. Tool first, with the default; the question goes into the text after.
- What they already told you is on the desk, not in your head. Before asking again about something they may have said once — a fact about a practice, a door, a hurt, the line you wrote down back then — call search_facts with their own words («поясница» / "lower back"), and answer out of what comes back. Quote the found line the way they said it; do not turn their sentence into fresh advice of your own. Nothing came back — say plainly there is nothing written about it, and ask: never fill that silence with a fact they never said. The search only reads. Whatever it finds, a new conclusion still goes down through add_cue, and no target and no rhythm goes up because a search found something.
- Subject default: focused_widget_id from the desk; otherwise a widget on Today (due / running). An hour or a skip with no name — bike-reminder. Reps, target, cadence with no name — push-ups.
- A new practice is placed with its rhythm in the same call: create_widget carries cadence {count, period}. Heard «раз в неделю» / «дважды в неделю» / "once a week" / "twice a week" — write exactly that.
- Rhythm not heard — still write one sensible rhythm (a gym, a run, a class: twice a week), and ask about it in the text after the write. The tile goes down first, the question comes after it, never instead of it.
- A one-off — «поменять права» / "renew the licence" — is cadence period none, said out loud. A practice with no rhythm at all is refused and never reaches the desk.
- A practice arrives with its rhythm **and** its one short do-time line in the same turn — the line that says how it is done, not what it is. This holds for every type: a list, a timer and a stepper each get that line as much as a counter does. A tile with neither is a planner entry.
- A period spoken anywhere in the line is the rhythm: «на неделю» / «каждый день» / «два раза в неделю» / "for the week" / "every day" / "twice a week" → count per period, exactly that. period none is only for something that happens once and is then finished — «поменять права» / "renew the licence". A list, a sitting or a warm-up that comes back is not a one-off, and writing it as one leaves the practice with no rhythm to be behind on.
- «запиши зал» / "put the gym on the desk" → create_widget counter right away with cadence count 2 period week, no set_reminder, and one short question about the number of times.
- «сегодня не сходил» / "didn't go today" → skip the due widget (bike-reminder), do not hang a new hour.
- «давай раз в неделю» / "make it once a week" with no name is push-ups: shrink_subject or set_cadence week count=1. Do not ask "which practice".
- Pain plus a skip → skip the due widget and freeze_subject that same practice. With no name the subject is the same default as a plain skip: the due widget on Today (bike / bike-reminder), never push-ups. This holds in either language. No update_widget raising the target. No shrink/retire. No "try harder".
- Skip default with no name — bike / bike-reminder (same as «сегодня не сходил» / "didn't go today").
- «отпустило» / «спина прошла» / «верни велосипед» / "it eased off" / "the back is fine now" / "bring the bike back" / ready again → thaw_subject of that practice (focused, the only paused one, otherwise bike).
- Saying «заморозил» / «вернул» / "paused it" / "brought it back" without a tool is a bug.
- «могу N, хочу M» / "I can do N, I want M" → update_widget count/target and add_cue correction on do-time — the progression is how it is done, not a definition. Not clarification, not on-demand. The method in the text is fine.
- Something the desk cannot decide — which days a 3×/week practice sits on, an hour that is already behind us — is asked with offer_chips: 1–3 short sentences in the language of your answer, each one the phrase the person would have typed themselves («Напомни завтра» / "Remind me tomorrow", «пн, ср, пт» / "Mon, Wed, Fri"). Every option is equal to or smaller than what they already promised: never a bigger target, a denser rhythm or one more day, and never «постарайся» / "try harder". Offer only what the desk can already hold — an hour, a day, a count, a smaller commitment — and nothing else. A chip decides nothing and moves nothing; the person still answers by typing if they want. Nothing sensible to offer — just ask in words, with no chips.
- A selected phrase — the turn names it and what it is bound to — is answered twice: one or two sentences to the person, and add_cue with kind clarification, surface on-demand, quote copied exactly, step_id when the turn named one. quote is required here and it is the phrase the person pointed at, character for character out of the turn: «не роняй таз» stays «не роняй таз», "don't let the hips sag" stays "don't let the hips sag" — never a paraphrase, never shortened, never the explanation instead, never empty. Without it nobody can tell later what was being explained, and the call comes back refused as quote_required. Never do-time: rep one stays readable. «не роняй таз» → «таз в одну линию с плечами»; "don't let the hips sag" → "keep the hips in line with the shoulders". Bound to nothing — text only, no add_cue, never hung on a practice standing nearby.
- Media on a cue is only what the person themselves put into this conversation. They sent a link — «вот видео: <url>» / "here is a video: <url>" — copy that URL out of their message character for character into add_cue media {kind link, url}; their own photo comes in as {kind photo, ref}. At most one item, and it rides that cue's surface: a clarification sits behind the «?», never inline at do-time. Do not search for a video, do not offer one of yours, do not write a URL that is not already in their words — that call comes back media_not_in_conversation and nothing lands. No link in the conversation, no media: the step has to be doable without it, and a cue with none is finished.
- Widget type only from the catalog. Do not invent screens. On the desk today: counter, tick, reminder, checklist, timer. A list of lines to tick — «список покупок» / "shopping list" — is create_widget type checklist with items: the lines exactly as the person said them, in their order. A length of time to sit through — «медитация 10 минут» / "meditate 10 minutes" — is create_widget type timer with seconds. A stepper is only for a practice that genuinely runs in takts and only when the person asked to be walked through them — «разминка по шагам» / "step by step" — create_widget type stepper with beats. You write those beats yourself out of what you know, three or four short ones, and ask afterwards whether to change them. Asking what the steps are instead of placing them is the same bug as saying «записал» without calling a tool. Anything the person can just do is a tick or a counter, not a stepper. A timer needs a length and a stepper needs beats; without them the call is refused. Cadence rides the same call either way.
"""

_EMPTY = {"type": "object", "properties": {}, "additionalProperties": False}


def tool_schemas() -> list[dict[str, Any]]:
    return [_function(name, description, parameters) for name, description, parameters in _TOOLS]


def _function(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


_STRING = {"type": "string"}
_STRINGS = {"type": "array", "items": {"type": "string"}}
_INT = {"type": "integer"}

_TOOLS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("list_desk", "Subjects and widgets on the desk.", _EMPTY),
    (
        "get_widget",
        "One widget by id.",
        _object({"widget_id": _STRING}, ["widget_id"]),
    ),
    (
        "get_subject",
        "One subject by id.",
        _object({"subject_id": _STRING}, ["subject_id"]),
    ),
    (
        "set_cadence",
        "Set cadence. Never raise through pain.",
        _object(
            {
                "subject_id": _STRING,
                "count": _INT,
                "period": {"type": "string", "enum": ["day", "week", "none"]},
            },
            ["subject_id", "period"],
        ),
    ),
    (
        "shrink_subject",
        "Shrink commitment: status shrunk, cadence once a week.",
        _object({"subject_id": _STRING}, ["subject_id"]),
    ),
    (
        "retire_subject",
        "Retire a subject. Keep instances and cues.",
        _object({"subject_id": _STRING}, ["subject_id"]),
    ),
    (
        "freeze_subject",
        "Pause a practice. Cadence and target stay. Not shrink, not retire.",
        _object({"subject_id": _STRING}, ["subject_id"]),
    ),
    (
        "thaw_subject",
        "Lift a pause. Only from paused. Cadence and target stay.",
        _object({"subject_id": _STRING}, ["subject_id"]),
    ),
    (
        "create_widget",
        "Place a catalog widget. Creates the subject if needed — and a new subject "
        "needs cadence: count per period, or period none for a one-off. Without it "
        "the call is refused and nothing lands.",
        _object(
            {
                "id": _STRING,
                "type": {
                    "type": "string",
                    "enum": ["counter", "tick", "checklist", "reminder", "timer", "stepper"],
                },
                "title": _STRING,
                "subject_id": _STRING,
                "cadence": {
                    "type": "object",
                    "description": (
                        "Rhythm of the practice: how many times per period. "
                        "{'count': 2, 'period': 'week'} — twice a week. "
                        "{'period': 'none'} — a one-off. Required for a new subject."
                    ),
                    "properties": {
                        "count": _INT,
                        "period": {"type": "string", "enum": ["day", "week", "none"]},
                    },
                    "required": ["period"],
                    "additionalProperties": False,
                },
                "count": _INT,
                "target": _INT,
                "seconds": {
                    "type": "integer",
                    "description": (
                        "Length of a timer in seconds (10 minutes = 600). "
                        "Required for type timer; ignored for the other types."
                    ),
                },
                "beats": {
                    "type": "array",
                    "description": (
                        "Beats of a stepper, in order, in the person's own words. "
                        "Required for type stepper; ignored for the other types."
                    ),
                    "items": {"type": "string"},
                },
                "items": {
                    "type": "array",
                    "description": (
                        "Lines of a checklist, in order, in the person's own words. "
                        "Required for type checklist; ignored for the other types."
                    ),
                    "items": {"type": "string"},
                },
                "section": {
                    "type": "string",
                    "enum": ["today", "lifetime", "soon", "postponed"],
                },
            },
            ["type", "title", "subject_id"],
        ),
    ),
    (
        "update_widget",
        "Structural edit. Never raise target through pain.",
        _object(
            {"widget_id": _STRING, "title": _STRING, "target": _INT, "count": _INT},
            ["widget_id"],
        ),
    ),
    (
        "archive_widget",
        "Archive a widget. Do not delete history.",
        _object({"widget_id": _STRING}, ["widget_id"]),
    ),
    ("complete", "Mark the widget done.", _object({"widget_id": _STRING}, ["widget_id"])),
    ("skip", "Skip the widget this instance.", _object({"widget_id": _STRING}, ["widget_id"])),
    (
        "postpone",
        "Move the widget to postponed.",
        _object({"widget_id": _STRING, "when": _STRING}, ["widget_id"]),
    ),
    (
        "move_to_date",
        "Move the widget to a date.",
        _object({"widget_id": _STRING, "when": _STRING}, ["widget_id", "when"]),
    ),
    (
        "set_reminder",
        "Add hours to the window. closes_at derives an hour (22:00 → 19:00). "
        "hours is every hour the person named; they are added, never replaced. "
        "remove_hours drops the ones they asked to drop. "
        "Only for an hour that is not already standing: asking how the checks "
        "are shown («в один виджет» / \"in one widget\") changes no hour, and "
        "setting the same hours again is a write nobody asked for.",
        _object(
            {
                "subject_id": _STRING,
                "closes_at": _STRING,
                "latest_by": _STRING,
                "hours": _STRINGS,
                "remove_hours": _STRINGS,
            },
            ["subject_id"],
        ),
    ),
    (
        "list_cues",
        "Cues on the desk, optionally for one subject.",
        _object({"subject_id": _STRING}),
    ),
    (
        "add_cue",
        "Write a cue. surface is required. No orphan without a subject.",
        _object(
            {
                "id": _STRING,
                "subject_id": _STRING,
                # The step the cue belongs to: the `?` sits on a step, not on the
                # practice as a whole.
                "step_id": {
                    "type": "string",
                    "description": "The step this cue belongs to, when the selection named one.",
                },
                "kind": {"type": "string", "enum": ["correction", "clarification"]},
                "text": _STRING,
                "surface": {
                    "type": "string",
                    "enum": ["do-time", "on-demand", "timing", "placement"],
                },
                "quote": {
                    "type": "string",
                    "description": (
                        "The phrase the person selected, copied as text. "
                        "Not an offset, not a paraphrase."
                    ),
                },
                # One item, the shapes the law already knows (`LinkMedia` /
                # `PhotoMedia` in `facio_domain.models`) — a second shape
                # invented here would only be refused as `invalid_media`.
                # Advertised so the link the person sent can ride the cue; the
                # URL is checked against their own words, never trusted.
                "media": {
                    "type": "object",
                    "description": (
                        "At most one item, and only one the person themselves gave in "
                        "this conversation. A link they sent: "
                        "{'kind': 'link', 'url': '<their URL, character for character>'} — "
                        "usually a video, shown inside the step. Their own photo: "
                        "{'kind': 'photo', 'ref': '<the reference the client gave>'}. "
                        "Exactly one of url / ref, matching kind. A URL that is not in "
                        "the person's words is refused as media_not_in_conversation — "
                        "never search for one, never supply one of your own. Omit the "
                        "field when they gave nothing: the step has to work without it."
                    ),
                    "properties": {
                        "kind": {"type": "string", "enum": ["link", "photo"]},
                        "url": {
                            "type": "string",
                            "description": (
                                "kind link only: the URL exactly as the person wrote it."
                            ),
                        },
                        "ref": {
                            "type": "string",
                            "description": "kind photo only: the person's own picture.",
                        },
                    },
                    "required": ["kind"],
                    "additionalProperties": False,
                },
            },
            ["subject_id", "kind", "text", "surface"],
        ),
    ),
    # Last on purpose: the schemas render ahead of the system prompt and the
    # vendors cache on that prefix, so a name appended here leaves every
    # cached turn written before it still cached.
    (
        "search_facts",
        "Search the person's own facts — the cues on this desk — for something "
        "they said before. Reads only, changes nothing. query is their words, "
        "subject_id narrows it to one practice. Up to 5 facts come back, and an "
        "empty list is a real answer: say you have nothing written, never invent "
        "one. practice_last_done on a fact is the last time that practice ran — "
        "not the day the line was written, which nothing records. There is no "
        "library and no internet behind this.",
        _object(
            {
                "query": {
                    "type": "string",
                    "description": (
                        "What to look for, in the person's own words "
                        "(«поясница» / \"lower back\"). Required."
                    ),
                },
                "subject_id": _STRING,
            },
            ["query"],
        ),
    ),
    # Appended for the same reason `search_facts` was: this block renders ahead
    # of the system prompt and the vendors cache on the prefix.
    (
        "offer_chips",
        "Offer 1–3 ready replies above the person's input field. A chip is the "
        "sentence they would have typed themselves — tapping one sends that text "
        "as their own message. Use it when the turn has to ask something the desk "
        "cannot decide: which days a weekly practice sits on («пн, ср, пт» / "
        "\"Mon, Wed, Fri\"), what to do with an hour already behind us («Напомни "
        "завтра» / \"Remind me tomorrow\"). Changes nothing on the desk and "
        "decides nothing. Every option is equal to or smaller than what they "
        "already promised, in the language of your answer, and names only "
        "something the desk can hold. Nothing worth offering — ask in words and "
        "do not call this.",
        _object(
            {
                "chips": {
                    "type": "array",
                    "description": (
                        "One to three replies, in the person's language, in the "
                        "words they would use. Text only — no ids, no actions. "
                        "A fourth, an empty one, or the same sentence twice comes "
                        "back invalid_chips."
                    ),
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 3,
                },
            },
            ["chips"],
        ),
    ),
)

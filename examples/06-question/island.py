"""Guide 6. Ask a question and score it."""
from grape import on_talk
from vine import play, say

# One question. Each answer has a reply, so a wrong answer still teaches something.
QUESTION = {
    "kind": "choice",
    "id": "club-day",
    "prompt": "What day does the CS Club meet?",
    "options": [
        {"text": "Wednesday", "correct": True, "reply": "Yes. Wednesdays after school."},
        {"text": "Monday", "reply": "No. It's Wednesday."},
        {"text": "Friday", "reply": "No. It's Wednesday."},
    ],
}


@on_talk("host")
def talk():
    yield say("One question.", who="host")
    # play runs the question and gives back a score from 0 to 4.
    # It gives back None if the player closed it without answering.
    score = yield play("club_day", title="One question", items=[QUESTION])
    if score is None:
        yield say("Come back when you want to try.", who="host")
    elif score == 4:
        yield say("Perfect.", who="host")
    else:
        yield say("Not quite. Talk to me to try again.", who="host")

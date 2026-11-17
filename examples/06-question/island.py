"""Example 6: ask a question and score it."""
from grape import on_talk
from vine import play, say

# every answer has its own reply, so a wrong answer still tells the player something
QUESTION = {
    "kind": "choice",
    "id": "club-day",
    "prompt": "What day does the CS Club meet?",
    "options": [
        {"text": "Wednesday", "correct": True, "reply": "Yep, we meet Wednesdays after school."},
        {"text": "Monday", "reply": "Nope, it's Wednesday."},
        {"text": "Friday", "reply": "No, it's actually Wednesday."},
    ],
}


@on_talk("host")
def talk():
    yield say("I've got one question for you.", who="host")
    # play runs the question and gives back a score from 0 to 4,
    # or None if the player closed it without answering
    score = yield play("club_day", title="One question", items=[QUESTION])
    if score is None:
        yield say("Come back whenever you want to try it.", who="host")
    elif score == 4:
        yield say("Perfect.", who="host")
    else:
        yield say("Not quite, so talk to me again if you want another try.", who="host")

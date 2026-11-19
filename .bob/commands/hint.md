---
description: Get a hint for the current step, without the full answer
argument-hint: optional mission id or quiz question
---
Give the student the smallest useful hint for what they are stuck on ($ARGUMENTS, or the current mission from `python3 scripts/lab.py status`).

Hint ladder: first a question that points them in the right direction; if they ask again, point to the exact section of the lab guide; only on the third request, show the command (still for them to approve). Never reveal quiz answers.

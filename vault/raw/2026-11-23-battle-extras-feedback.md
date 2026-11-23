---
title: Feedback on the battle extras
type: raw
source: user messages in chat, 2026-11-23
tags: [area/ui]
created: 2026-11-23
---

# Feedback (2026-11-23)

User, verbatim: "fix the moon. replace pokeballs with mini-sprites like in showdown. always leave space for stat buffs instead of making them raise the box. remove (always) and bold and unitalicize things that are revealed. parenthesize percetages for the set info. the type boxes should take colors from the move boxes so that they're more readable. generally just take the formatting of the information from showdown + showdown randbats tooltip as that's a good way to present information. also, hovers that cover other parts of the screen don't really work with the ui format. try to find a solution that looks more in place. also the hover doesn't work for  the faint animation also never shows. remove the move animations, as they're not good. make sure the substitute touches the disk properly"

Mid-turn: "also make the full move names always show. the longest one is Soul-Stealing 7-Star Strike."

Notes: the sentence "the hover doesn't work for" was cut off; Claude assumed the bench (non-active) Pokemon. Root cause of the missing faint: no turn-start state shows a fainted Pokemon on the field (the replacement is already in), so the faint animation never had a target.

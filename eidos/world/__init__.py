"""EIDOS for the physical world: learn a task program from one real-world video, then run it live.

The screen engine (eidos.ui) has an agent carry out the steps. In the physical world a person
(or a robot) carries them out, and EIDOS watches a live camera feed: it works out which step
is happening, checks each finished step against the visual contract learned from the video,
and flags a skipped step, a wrong order, or a result that does not match.
"""

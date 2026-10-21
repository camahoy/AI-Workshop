"""US Public Affairs AI session live boards, served as a page of this app
so they share its existing web address (no separate deployment).

Links: <app url>/PA_Live_Boards?board=a|b|c for phones and laptops, add
&view=present for the projector. The boards live in pa_boards/ (see
pa_boards/README.md); the presenter passcode is FACILITATOR_PASSWORD,
or PRESENTER_PASSCODE if that is set.
"""
import os
import runpy
from pathlib import Path

os.environ["PA_BOARDS_PAGE"] = "PA_Live_Boards"
runpy.run_path(str(Path(__file__).resolve().parent.parent / "pa_boards" / "app.py"), run_name="__main__")

# Records docs/demo/tamper.gif from a real run: `vhs docs/demo/tamper.tape` from the repo root.
Output docs/demo/tamper.gif
Set Shell "bash"
Set FontSize 15
Set Width 1300
Set Height 480
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 22ms

Hide
Type `export PS1='$ ' && uv sync -q && source .venv/bin/activate && clear` Enter
Sleep 10s
Show
Type `python -m training_provenance tamper` Enter
Sleep 2.5s
Type `python -m training_provenance recover` Enter
Sleep 2.5s

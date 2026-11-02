# Records docs/demo/verify.gif from a real run: `vhs docs/demo/verify.tape` from the repo root.
Output docs/demo/verify.gif
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
Type `python -m training_provenance build` Enter
Sleep 2.5s
Type `python -m training_provenance verify` Enter
Sleep 2.5s

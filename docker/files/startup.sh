#!/bin/bash
set -e

if [[ ! -d /botsrc/.pyenv ]]; then
    git clone https://github.com/pyenv/pyenv.git /botsrc/.pyenv
fi

export PYENV_ROOT="/botsrc/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv init --path)"

pyenv install -s 3.9.6
pyenv global 3.9.6

cd /botsrc/
pip3 install -r requirements.txt

while true; do timeout 24h python3.9 moderator-bot.py || sleep 1; done

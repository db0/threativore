# Threativore

A Fediverse/Threadiverse bot to fight against spam and help with moderation

The name is a portmanteau of Threats + Vore. I.e. this is a tool that eats threats.

# Roadmap

See the [Roadmap](README_roadmap.md)

# Setup

## Clone the repo

_This is easiest to do within your Lemmy folder you have your docker compose already in_

`git clone https://github.com/db0/threativore.git`

Then move into the new `threativore` directory.

## Option 1 - Run directly via python

* `python -m pip install -r requirements.txt`
* Copy `.env_template` into `.env` and modify its contents according to the comments
* `python run.py`

## Option 2 - Run with docker

See the [Docker README](README_docker.md)

# Use

See the [Usage Manual](README_manual.md)

# Garbage collection

The bot constantly records all posts/comments it has seen in the DB to avoid re-scanning them. It will constantly delete any column older than 7 days.

# Filter collection

The caught spam in the bot will be recorded in the DB. There's no way currently to retrieve this info but this will be possible in the future as it will be useful for analysis and Machine Learning
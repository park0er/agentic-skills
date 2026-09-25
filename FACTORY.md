# Skill Factory

This repository is the development and release staging area for local skills.

## Layout

- `skills/<skill-name>/`: active development copy.
- `archives/<skill-name>/<timestamp>-<label>/`: immutable snapshot copied from the installed stable skill before a release replacement.

## Release Rule

Before replacing an installed skill, copy the currently installed stable version into `archives/<skill-name>/` and commit that snapshot. Then copy the tested factory version into the installed skill directory and commit the factory release state.

Do not develop directly inside the installed skill directory.


#!/bin/sh
gunicorn "tele_bot:create_app()" -b 0.0.0.0
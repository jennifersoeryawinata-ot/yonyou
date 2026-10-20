#!/bin/sh

# Harap Perhatikan: Newline Carriage hanya menggunakan LF sehubungan Debian di versi Python hanya kenal LF, bukan CRLF!

# alembic upgrade head

# uvicorn main:app --host 0.0.0.0 --port=8080
hypercorn main:app --bind 0.0.0.0:8080 --workers 1 --worker-class uvloop --keep-alive 65

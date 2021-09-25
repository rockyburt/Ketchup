FROM docker.io/python:3.9

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -

ENV PATH=/root/.local/bin:${PATH}

FROM python:3.9.16-slim AS base

# Create virtualenv and add to path.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# System dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app

# Install Python requirements. README.md is required as the setup.py file
# refers to it.
COPY . .
RUN pip install -e .[dev,test]

# Run subsequent commands as non-root user
ENV USER=application
RUN useradd --no-log-init --system --user-group $USER
USER $USER

# ---

# Create a pytest image from the base
FROM base as pytest

# Run py.test against current dir by default but allow custom args to be passed
# in.
ENTRYPOINT ["py.test"]
CMD [""]

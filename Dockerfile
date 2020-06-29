FROM python:3.7.7-slim

# Create virtualenv and add to path.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# System dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app

# Install Python requirements. README.md is required as the setup.py file
# refers to it.
COPY README.md .
COPY setup.py .
RUN pip install -e .[dev,test]

# Run py.test against current dir by default but allow custom args to be passed
# in.
ENTRYPOINT ["py.test"]
CMD [""]

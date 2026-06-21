FROM public.ecr.aws/lambda/python:3.12

# Install Node.js 22 (obsidian-headless requires >=22; dnf default is 18)
ARG NODE_VERSION=22.16.0
RUN dnf install -y tar gzip && dnf clean all && \
    curl -fsSL -o /tmp/node.tar.gz \
        https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.gz && \
    tar -xzf /tmp/node.tar.gz -C /usr/local --strip-components=1 && \
    rm /tmp/node.tar.gz

# Install obsidian-headless globally
RUN npm install -g obsidian-headless

# Install Python dependencies
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e ".[dev]" --target "${LAMBDA_TASK_ROOT}"

# Copy Lambda handlers
COPY handler_collect.py handler_improve.py ${LAMBDA_TASK_ROOT}/

# Default handler (overridden per-function in AWS console)
CMD ["handler_collect.handler"]

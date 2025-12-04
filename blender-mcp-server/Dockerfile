FROM ubuntu:22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    xz-utils \
    libxi6 \
    libxxf86vm1 \
    libxfixes3 \
    libxrender1 \
    libgl1 \
    libglu1-mesa \
    libxkbcommon0 \
    libsm6 \
    libice6 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Download and install Blender 4.0
RUN wget -q https://download.blender.org/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz \
    && tar -xf blender-4.0.2-linux-x64.tar.xz -C /opt \
    && rm blender-4.0.2-linux-x64.tar.xz \
    && ln -s /opt/blender-4.0.2-linux-x64/blender /usr/local/bin/blender

# Set up Python environment
WORKDIR /app

# Copy requirements and install using Blender's Python
COPY requirements.txt .
# Find Blender's Python and install packages
RUN BLENDER_PYTHON=$(find /opt/blender-4.0.2-linux-x64 -name "python*" -type f -executable | head -n 1) && \
    $BLENDER_PYTHON -m ensurepip && \
    $BLENDER_PYTHON -m pip install --no-cache-dir -r requirements.txt

# Copy MCP server code
COPY mcp_server.py .
COPY blender_operations.py .

# Create output directory
RUN mkdir -p /tmp

# Expose port
EXPOSE 8080

# Run the MCP server with Blender in background mode
CMD ["blender", "--background", "--python", "mcp_server.py"]

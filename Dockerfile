# Use the base image that includes ffmpeg
FROM mysterydemon/botcluster:ffmpeg-v7.0.2

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt to the container
COPY requirements.txt ./

# Install python3-venv to create a virtual environment
# Upgrade pip and install dependencies in the virtual environment
RUN apt-get update && apt-get install -y python3-venv \
    && python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code to the container
COPY . .

# Copy the start.sh script to the /usr/local/bin/ directory
COPY start.sh /usr/local/bin/start.sh

# Ensure shell scripts are executable
RUN chmod +x run.sh /usr/local/bin/start.sh

# Create a non-root user to avoid permission issues
RUN useradd -m botuser
USER botuser

# Run the setup script (run.sh) to initialize the app
RUN bash run.sh

# Set the default command to run when the container starts
CMD ["/usr/local/bin/start.sh"]

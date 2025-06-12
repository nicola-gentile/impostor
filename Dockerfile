FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Clone the repository
RUN git clone https://github.com/nicola-gentile/impostor.git .

# Install the Python package globally
RUN pip install --upgrade pip && pip install .

# Expose the port
EXPOSE 8000

# Run the app using uvicorn
CMD ["uvicorn", "impostor.main:app", "--host", "0.0.0.0", "--port", "8000"]

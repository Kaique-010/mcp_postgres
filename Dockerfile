FROM python:3.11-slim

# Set workdir
WORKDIR /core

# Copy files
COPY . /core

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "manager.py"]

FROM python:3.12.12-alpine
LABEL authors="Jorislarmaillard"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Setting up working directory
WORKDIR /app

# Copy all requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy files in the project
COPY . .

# Port
EXPOSE 5001

# Starting application
CMD ["python", "app.py"]
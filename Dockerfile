FROM python:3.10.0-alpine

WORKDIR /app

EXPOSE 8001

COPY requirements.txt requirements.txt

RUN pip3 install --upgrade setuptools
RUN pip3 install -r requirements.txt

COPY . .

# CMD "python3 main.py"
CMD ["python", "main.py"]
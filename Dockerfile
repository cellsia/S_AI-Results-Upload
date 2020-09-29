FROM cytomine/software-python3-base
RUN pip install --upgrade pip && \
    pip install --no-cache-dir pyyaml
ADD run.py /app/run.py
ENTRYPOINT ["python", "/app/run.py"]
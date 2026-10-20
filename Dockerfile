FROM python:3.13-slim

WORKDIR /usr/src/app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Install uvloop di Dockerfile sebuhubungan dengan batasan Windows dalam proses build
RUN pip install uvloop==0.22.1

# Mengopi seluruh isi direktori saat ini (termasuk startup.sh jika ada di root)
COPY . .
# for yonyu sdk
RUN pip install --no-cache-dir ./packages/yonyouopenapisdk-1.1.1-py3-none-any.whl
# Salin & set permission startup.sh secara spesifik ke /usr/bin jika dibutuhkan oleh entrypoint
COPY startup.sh /usr/bin/startup.sh
RUN chmod +x /usr/bin/startup.sh

ENTRYPOINT ["/usr/bin/startup.sh"]

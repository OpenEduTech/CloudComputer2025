FROM python:3.11-slim
WORKDIR /app
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
	PIP_NO_CACHE_DIR=1 \
	TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu \
	TORCH_VERSION=2.1.2
COPY requirements.txt ./
RUN set -eux; \
	MIRROR="https://mirrors.aliyun.com/debian"; \
	SEC_MIRROR="https://mirrors.aliyun.com/debian-security"; \
	CODENAME=$(. /etc/os-release && echo "${VERSION_CODENAME:-bookworm}"); \
	if [ -f /etc/apt/sources.list ]; then \
		sed -i "s|http://deb.debian.org/debian|${MIRROR}|g" /etc/apt/sources.list; \
	else \
		printf '%s\n' \
			"deb ${MIRROR} ${CODENAME} main non-free non-free-firmware" \
			"deb ${MIRROR} ${CODENAME}-updates main non-free non-free-firmware" \
			"deb ${SEC_MIRROR} ${CODENAME}-security main non-free non-free-firmware" \
			> /etc/apt/sources.list; \
	fi; \
	if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
		sed -i "s|http://deb.debian.org/debian|${MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
		sed -i "s|https://deb.debian.org/debian-security|${SEC_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
	fi; \
	apt-get update; \
	apt-get install -y --no-install-recommends ffmpeg; \
	rm -rf /var/lib/apt/lists/*; \
	pip install --no-cache-dir --index-url "${TORCH_INDEX_URL}" --extra-index-url "${PIP_INDEX_URL}" "torch==${TORCH_VERSION}"; \
	pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PORT=8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

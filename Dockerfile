ARG OSMIUM_VERSION=1.16.0

FROM --platform=linux/amd64 iboates/osmium:${OSMIUM_VERSION} AS osmium_builder

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    bash \
    build-base \
    python3-dev \
    boost-dev \
    expat-dev \
    cmake \
    bzip2-dev \
    zlib-dev && \
    pip3 install --no-cache-dir --break-system-packages \
    osmium \
    shapely

# Create working directory
WORKDIR /app

# Copy scripts
COPY reduce.py /app/reduce.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh /app/reduce.py

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
# The image this pool's check runs in: Proxima Fusion's ConStellaration scorer (MIT), pinned to the
# version its public leaderboard uses, installed into the image's own site-packages, outside /work.
# Thinkpool mounts the contribution's copy at /work with a read-only root and no network.
FROM python:3.12.11-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential cmake libnetcdf-dev git \
 && pip install --no-cache-dir constellaration==0.2.6 pytest==8.4.2 \
 && apt-get purge -y git && apt-get autoremove -y && rm -rf /var/lib/apt/lists/* \
 && useradd -m -u 1000 checker
ENV OMP_NUM_THREADS=2 MPLCONFIGDIR=/tmp
USER 1000:1000

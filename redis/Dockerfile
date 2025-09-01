FROM redis:7-alpine

# Set working directory
WORKDIR /data

# Copy Redis configuration
COPY redis.conf /usr/local/etc/redis/redis.conf

# Create Redis user and set permissions
RUN addgroup -g 999 redis && adduser -D -s /bin/sh -u 999 -G redis redis
RUN chown -R redis:redis /data
RUN chown redis:redis /usr/local/etc/redis/redis.conf

# Switch to Redis user
USER redis

# Expose port
EXPOSE 6379

# Start Redis with custom config
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
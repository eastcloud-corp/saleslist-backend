FROM postgres:15

# Set environment variables
ENV POSTGRES_DB=social_navigator
ENV POSTGRES_USER=social_navigator_user
ENV POSTGRES_PASSWORD=social_navigator_password
ENV PGDATA=/var/lib/postgresql/data/pgdata

# Create init directory
RUN mkdir -p /docker-entrypoint-initdb.d

# Copy initialization scripts
COPY init-scripts/ /docker-entrypoint-initdb.d/

# Create data directory and set permissions
RUN mkdir -p /var/lib/postgresql/data/pgdata
RUN chown -R postgres:postgres /var/lib/postgresql/data

# Expose port
EXPOSE 5432

# Configure PostgreSQL
RUN echo "listen_addresses = '*'" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "port = 5432" >> /usr/share/postgresql/postgresql.conf.sample

# Volume for persistent data
VOLUME ["/var/lib/postgresql/data"]
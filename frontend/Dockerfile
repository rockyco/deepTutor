FROM nginx:alpine

# Copy config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy static build output
COPY out /usr/share/nginx/html

# Expose port (Cloud Run expects 8080 by default)
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

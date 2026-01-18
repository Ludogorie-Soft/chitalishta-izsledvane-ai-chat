# Deployment Guide

## AWS EC2 Deployment

This guide covers deploying the Chitalishta AI Chat application to AWS EC2.

### Prerequisites

- Docker and Docker Compose installed on EC2 instance
- Docker Hub account for pulling images
- Environment variables configured

### Document Handling in Production

The application requires access to analysis documents (stored in the `documents/` folder). There are two approaches:

#### Option 1: Documents Baked into Docker Image (Recommended)

This is the default configuration for production. Documents are copied into the Docker image during build time.

**Advantages:**
- No need to manually copy documents to EC2
- Documents are version-controlled with the image
- Simpler deployment process

**Steps:**
1. Ensure `documents/` folder contains required files before building the image
2. Build and push the image:
   ```bash
   docker build -t your-registry/chitalishta_ai_chat_api:latest .
   docker push your-registry/chitalishta_ai_chat_api:latest
   ```

3. On EC2, the `docker-compose.prod.yml` file has the volume mount commented out by default:
   ```yaml
   volumes:
     - chroma_db_data:/app/chroma_db
     # Documents are included in the image - no mount needed
     # - ./documents:/app/documents:ro
   ```

4. Pull and start the container:
   ```bash
   docker-compose -f docker-compose.prod.yml pull
   docker-compose -f docker-compose.prod.yml up -d
   ```

**Note:** If you need to update documents, you must rebuild and redeploy the Docker image.

#### Option 2: Mount Documents from Host (For Frequent Updates)

If you need to frequently update documents without rebuilding the image, use volume mounting.

**Advantages:**
- Can update documents without rebuilding image
- Useful for development or frequent content changes

**Steps:**
1. Copy documents folder to EC2:
   ```bash
   # From your local machine
   scp -r documents/ ec2-user@your-ec2-ip:/home/ec2-user/chitalishta/
   ```

2. On EC2, uncomment the volume mount in `docker-compose.prod.yml`:
   ```yaml
   volumes:
     - chroma_db_data:/app/chroma_db
     - ./documents:/app/documents:ro  # Uncomment this line
   ```

3. Ensure the documents folder exists in the same directory as docker-compose.prod.yml:
   ```bash
   cd /home/ec2-user/chitalishta/
   ls -la documents/  # Verify files exist
   ```

4. Start the container:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Troubleshooting

#### Error: "Document file not found"

**Symptoms:**
```json
{
  "status": "error",
  "message": "Document file not found: Document not found: /app/documents/...",
}
```

**Cause:** The documents folder is not available in the container.

**Solution:**
1. Check if using Option 1 (baked into image):
   - Verify documents were in the build context when image was built
   - Verify volume mount is commented out in docker-compose.prod.yml
   - Rebuild and redeploy the image

2. Check if using Option 2 (volume mount):
   - Verify documents folder exists on EC2 host
   - Verify volume mount is uncommented in docker-compose.prod.yml
   - Verify correct file permissions (readable by container user)
   - Restart container: `docker-compose -f docker-compose.prod.yml restart app`

#### Verify Documents in Container

Check if documents are accessible inside the container:

```bash
# List files in documents directory
docker exec chitalishta_ai_chat_api ls -la /app/documents/

# Check specific file
docker exec chitalishta_ai_chat_api ls -la "/app/documents/Читалищната мрежа в България – анализ през призмата на данните.docx"
```

### Environment Variables

Create a `.env` file on EC2 with required variables:

```bash
# Database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=chitalishta_db
DATABASE_URL=postgresql://user:pass@db:5432/chitalishta_db

# OpenAI API
OPENAI_API_KEY=your_openai_key
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# JWT Keys (generate with scripts/generate_jwt_keys.py)
JWT_RSA_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
JWT_RSA_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"

# CORS
CORS_ORIGINS=https://your-frontend-domain.com,http://localhost:5173

# Ports
APP_PORT=8000
POSTGRES_PORT=5432
FRONTEND_PORT=3000
```

### Deployment Steps

1. **Prepare EC2 instance:**
   ```bash
   sudo yum update -y  # Amazon Linux
   sudo yum install -y docker
   sudo service docker start
   sudo usermod -a -G docker ec2-user

   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **Copy configuration files:**
   ```bash
   # Create project directory
   mkdir -p /home/ec2-user/chitalishta
   cd /home/ec2-user/chitalishta

   # Copy docker-compose.prod.yml and .env
   scp docker-compose.prod.yml ec2-user@your-ec2-ip:/home/ec2-user/chitalishta/
   scp .env ec2-user@your-ec2-ip:/home/ec2-user/chitalishta/

   # If using Option 2 (volume mount), copy documents too
   scp -r documents/ ec2-user@your-ec2-ip:/home/ec2-user/chitalishta/
   ```

3. **Start services:**
   ```bash
   cd /home/ec2-user/chitalishta
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Verify deployment:**
   ```bash
   # Check container status
   docker-compose -f docker-compose.prod.yml ps

   # Check logs
   docker-compose -f docker-compose.prod.yml logs -f app

   # Test health endpoint
   curl http://localhost:8000/health
   ```

5. **Initialize database (first time only):**
   ```bash
   # Create users table
   docker exec -it chitalishta_ai_chat_api python scripts/create_users_table.py

   # Create admin user
   docker exec -it chitalishta_ai_chat_api python scripts/create_user.py

   # Create other necessary tables
   docker exec -it chitalishta_ai_chat_api python scripts/init_db_additional_tables.py
   ```

### Updating the Application

```bash
cd /home/ec2-user/chitalishta

# Pull latest image
docker-compose -f docker-compose.prod.yml pull app

# Restart with new image
docker-compose -f docker-compose.prod.yml up -d

# Verify
docker-compose -f docker-compose.prod.yml logs -f app
```

### Security Considerations

1. **Use HTTPS:** Configure a reverse proxy (nginx/Caddy) with SSL certificates
2. **Firewall:** Restrict access to necessary ports only
3. **Environment Variables:** Never commit `.env` files to version control
4. **Database:** Use strong passwords and restrict network access
5. **API Keys:** Rotate regularly and use AWS Secrets Manager for production

### Monitoring

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker-compose -f docker-compose.prod.yml logs -f app

# Container resource usage
docker stats

# Check disk usage
docker system df
```

### Backup

```bash
# Backup PostgreSQL database
docker exec chitalishta_db_ai_chat pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d).sql

# Backup Chroma vector store
docker cp chitalishta_ai_chat_api:/app/chroma_db ./chroma_backup_$(date +%Y%m%d)
```


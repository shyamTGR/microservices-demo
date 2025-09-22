# Design Document

## Overview

This design outlines the completion of the Shopping Assistant service deployment for the Online Boutique application. The infrastructure is already in place (AlloyDB cluster, Kubernetes manifests, service accounts), but two critical components need implementation: database initialization with product embeddings and container image building/deployment.

The Shopping Assistant service uses Google's Gemini AI for image analysis and product recommendations, combined with AlloyDB's vector search capabilities to find relevant products based on room descriptions and user queries.

## Architecture

### Current State
- ✅ AlloyDB cluster "onlineboutique-cluster" deployed with primary and replica instances
- ✅ Kubernetes manifests configured for Shopping Assistant service
- ✅ Service accounts and IAM bindings configured
- ✅ Secret Manager integration for database credentials
- ❌ Database schema and product embeddings not populated
- ❌ Container image not built and pushed to registry

### Target Architecture
```
Frontend → Shopping Assistant Service → AlloyDB (Vector Store)
                ↓
            Gemini API (Image Analysis & Text Generation)
```

The service workflow:
1. Receives image + text prompt from frontend
2. Uses Gemini Vision to analyze room style
3. Performs vector similarity search in AlloyDB
4. Uses Gemini to generate recommendations
5. Returns formatted response with product IDs

## Components and Interfaces

### Database Schema Design
The AlloyDB setup requires two databases:
- **products**: Stores product catalog with vector embeddings
- **carts**: Stores cart data (replacing Redis functionality)

#### Products Database Schema
```sql
-- Table: catalog_items
CREATE TABLE catalog_items (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT NOT NULL,
    categories TEXT[],
    price_usd DECIMAL(10,2),
    picture VARCHAR,
    product_embedding VECTOR(768)  -- Gemini embedding dimension
);

-- Vector similarity index
CREATE INDEX ON catalog_items USING hnsw (product_embedding vector_cosine_ops);
```

### Container Build Process
The service uses a multi-stage Docker build:
- Base Python 3.12 slim image
- Builder stage installs dependencies from requirements.txt
- Final stage copies application code and dependencies
- Exposes port 8080 for HTTP traffic

### Integration Points
- **AlloyDB Connection**: Uses langchain-google-alloydb-pg for vector operations
- **Secret Manager**: Retrieves database password securely
- **Gemini API**: Uses provided API key for AI operations
- **Frontend Integration**: Service endpoint configured in frontend environment

## Data Models

### Product Data Structure
Based on existing products.json:
```json
{
    "id": "OLJCESPC7Z",
    "name": "Sunglasses", 
    "description": "Add a modern touch to your outfits with these sleek aviator sunglasses.",
    "picture": "/static/img/products/sunglasses.jpg",
    "priceUsd": {"currencyCode": "USD", "units": 19, "nanos": 990000000},
    "categories": ["accessories"]
}
```

### Vector Embedding Strategy
- Use Gemini's embedding-001 model for consistent embeddings
- Embed product descriptions for semantic search
- Store embeddings as 768-dimensional vectors in AlloyDB
- Include metadata (id, name, categories) for filtering

## Error Handling

### Database Connection Errors
- Implement retry logic with exponential backoff
- Graceful degradation if vector store unavailable
- Clear error messages for connection failures
- Health check endpoint for monitoring

### API Rate Limiting
- Batch embedding generation to avoid quota issues
- Implement request queuing for high load
- Monitor Gemini API usage to stay within limits
- Fallback responses if API unavailable

### Resource Constraints
- Use existing AlloyDB instance (no new resources)
- Optimize container resource requests/limits
- Efficient batch processing for database population
- Monitor memory usage during embedding generation

## Testing Strategy

### Database Verification
1. **Connection Test**: Verify AlloyDB connectivity using provided credentials
2. **Schema Validation**: Confirm tables created with correct structure
3. **Data Population**: Verify all products from products.json are embedded
4. **Vector Search**: Test similarity search returns relevant results

### Service Integration Testing
1. **Container Build**: Verify image builds successfully with Skaffold
2. **Deployment Test**: Confirm service starts and connects to database
3. **API Endpoint**: Test service responds to POST requests correctly
4. **Frontend Integration**: Verify frontend can communicate with service

### Quota Management Testing
1. **Resource Usage**: Monitor CPU/memory during deployment
2. **API Limits**: Track Gemini API calls during embedding generation
3. **Database Load**: Monitor AlloyDB performance during population
4. **Build Efficiency**: Optimize container build process for speed

## Implementation Approach

### Phase 1: Database Setup
1. Create database initialization script
2. Connect to AlloyDB using existing credentials
3. Create required databases and tables
4. Generate embeddings for products.json data
5. Populate database with product embeddings

### Phase 2: Container Deployment
1. Build Shopping Assistant service image using Skaffold
2. Push image to Google Artifact Registry
3. Update Kubernetes deployment to use built image
4. Verify service startup and database connectivity

### Phase 3: Integration Verification
1. Test service API endpoints
2. Verify vector search functionality
3. Confirm frontend integration works
4. Validate end-to-end user workflow

This phased approach minimizes resource usage while ensuring each component works before proceeding to the next phase.
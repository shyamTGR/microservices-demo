#!/usr/bin/env python3
"""
Product Embedding Generation Script

This script reads products from products.json and generates vector embeddings
using Google's Gemini embedding model. The embeddings are prepared for insertion
into the AlloyDB catalog_items table.

Usage:
    python generate_embeddings.py
"""

import os
import json
import time
import logging
from typing import List, Dict, Any
from decimal import Decimal

from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PRODUCTS_FILE = "src/productcatalogservice/products.json"
# Alternative path when running from VM
if not os.path.exists(PRODUCTS_FILE):
    PRODUCTS_FILE = "scripts/products.json"
EMBEDDINGS_OUTPUT_FILE = "scripts/product_embeddings.json"
BATCH_SIZE = 5  # Process products in small batches to avoid rate limits
RATE_LIMIT_DELAY = 1  # Seconds between API calls

def load_products() -> List[Dict[str, Any]]:
    """Load products from the products.json file."""
    try:
        logger.info(f"Loading products from {PRODUCTS_FILE}")
        
        if not os.path.exists(PRODUCTS_FILE):
            raise FileNotFoundError(f"Products file not found: {PRODUCTS_FILE}")
        
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        products = data.get('products', [])
        logger.info(f"Loaded {len(products)} products")
        
        return products
        
    except Exception as e:
        logger.error(f"Failed to load products: {e}")
        raise

def create_embedding_text(product: Dict[str, Any]) -> str:
    """Create a comprehensive text representation of a product for embedding."""
    # Combine name, description, and categories for rich semantic representation
    name = product.get('name', '')
    description = product.get('description', '')
    categories = product.get('categories', [])
    
    # Create a rich text representation
    category_text = ', '.join(categories) if categories else ''
    
    embedding_text = f"{name}. {description}"
    if category_text:
        embedding_text += f" Categories: {category_text}."
    
    return embedding_text

def convert_price_to_decimal(price_usd: Dict[str, Any]) -> float:
    """Convert price from the nested format to a decimal value."""
    try:
        units = price_usd.get('units', 0)
        nanos = price_usd.get('nanos', 0)
        
        # Convert nanos to decimal fraction (nanos are billionths)
        decimal_price = float(units) + (float(nanos) / 1_000_000_000)
        return round(decimal_price, 2)
        
    except Exception as e:
        logger.warning(f"Failed to convert price: {e}")
        return 0.0

def generate_embeddings_batch(products: List[Dict[str, Any]], 
                            embedding_service: GoogleGenerativeAIEmbeddings) -> List[Dict[str, Any]]:
    """Generate embeddings for a batch of products."""
    try:
        # Prepare texts for embedding
        texts = []
        for product in products:
            embedding_text = create_embedding_text(product)
            texts.append(embedding_text)
            logger.debug(f"Product {product['id']}: {embedding_text}")
        
        # Generate embeddings for the batch
        logger.info(f"Generating embeddings for {len(texts)} products...")
        embeddings = embedding_service.embed_documents(texts)
        
        # Prepare results with product data and embeddings
        results = []
        for i, product in enumerate(products):
            # Convert price to decimal
            price_decimal = convert_price_to_decimal(product.get('priceUsd', {}))
            
            result = {
                'id': product['id'],
                'name': product['name'],
                'description': product['description'],
                'categories': product.get('categories', []),
                'price_usd': price_decimal,
                'picture': product.get('picture', ''),
                'embedding_text': create_embedding_text(product),
                'product_embedding': embeddings[i]
            }
            results.append(result)
        
        logger.info(f"Successfully generated embeddings for {len(results)} products")
        return results
        
    except Exception as e:
        logger.error(f"Failed to generate embeddings for batch: {e}")
        raise

def generate_all_embeddings() -> List[Dict[str, Any]]:
    """Generate embeddings for all products with rate limiting."""
    # Check for API key
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    
    # Initialize embedding service
    logger.info("Initializing Gemini embedding service...")
    embedding_service = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )
    
    # Load products
    products = load_products()
    
    # Process products in batches to avoid rate limits
    all_results = []
    total_batches = (len(products) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(products), BATCH_SIZE):
        batch_num = (i // BATCH_SIZE) + 1
        batch = products[i:i + BATCH_SIZE]
        
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} products)")
        
        try:
            batch_results = generate_embeddings_batch(batch, embedding_service)
            all_results.extend(batch_results)
            
            # Rate limiting - wait between batches
            if i + BATCH_SIZE < len(products):  # Don't wait after the last batch
                logger.info(f"Waiting {RATE_LIMIT_DELAY} seconds before next batch...")
                time.sleep(RATE_LIMIT_DELAY)
                
        except Exception as e:
            logger.error(f"Failed to process batch {batch_num}: {e}")
            # Continue with next batch instead of failing completely
            continue
    
    logger.info(f"Completed embedding generation for {len(all_results)} products")
    return all_results

def save_embeddings(embeddings_data: List[Dict[str, Any]]) -> None:
    """Save embeddings data to a JSON file for inspection and backup."""
    try:
        logger.info(f"Saving embeddings to {EMBEDDINGS_OUTPUT_FILE}")
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(EMBEDDINGS_OUTPUT_FILE), exist_ok=True)
        
        # Convert numpy arrays to lists for JSON serialization
        serializable_data = []
        for item in embeddings_data:
            serializable_item = item.copy()
            # Convert embedding array to list
            if 'product_embedding' in serializable_item:
                serializable_item['product_embedding'] = serializable_item['product_embedding'].tolist()
            serializable_data.append(serializable_item)
        
        with open(EMBEDDINGS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully saved {len(embeddings_data)} product embeddings")
        
    except Exception as e:
        logger.error(f"Failed to save embeddings: {e}")
        raise

def validate_embeddings(embeddings_data: List[Dict[str, Any]]) -> None:
    """Validate the generated embeddings data."""
    logger.info("Validating embeddings data...")
    
    if not embeddings_data:
        raise ValueError("No embeddings data to validate")
    
    # Check each embedding
    for i, item in enumerate(embeddings_data):
        # Required fields
        required_fields = ['id', 'name', 'description', 'product_embedding']
        for field in required_fields:
            if field not in item:
                raise ValueError(f"Missing required field '{field}' in item {i}")
        
        # Check embedding dimensions
        embedding = item['product_embedding']
        if len(embedding) != 768:
            raise ValueError(f"Invalid embedding dimension for product {item['id']}: expected 768, got {len(embedding)}")
    
    logger.info(f"✓ Validation passed for {len(embeddings_data)} embeddings")

def main():
    """Main function to generate product embeddings."""
    logger.info("Starting product embedding generation...")
    
    try:
        # Generate embeddings
        embeddings_data = generate_all_embeddings()
        
        # Validate embeddings
        validate_embeddings(embeddings_data)
        
        # Save embeddings for backup and inspection
        save_embeddings(embeddings_data)
        
        logger.info("Product embedding generation completed successfully!")
        logger.info(f"Generated embeddings for {len(embeddings_data)} products")
        logger.info(f"Embeddings saved to: {EMBEDDINGS_OUTPUT_FILE}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Run: python scripts/populate_database.py")
        logger.info("2. Build and deploy the Shopping Assistant service")
        
        return embeddings_data
        
    except Exception as e:
        logger.error(f"Product embedding generation failed: {e}")
        raise

if __name__ == "__main__":
    main()
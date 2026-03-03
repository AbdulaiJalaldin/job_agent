from resumeUpload import DocumentData
import os
from dataclasses import dataclass
from typing import List
from pinecone import Pinecone,ServerlessSpec
from sentence_transformers import SentenceTransformer

@dataclass
class RetrievedChunk:
    text: str
    metadata: dict  # source, chunk_index, etc.
    score: float

class vectorservice:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

        self.index_name = "resume-index"

        if self.index_name not in self.pinecone_client.list_indexes().names():
            self.pinecone_client.create_index(
                name=self.index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        self.index = self.pinecone_client.Index(self.index_name)

    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
       
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
    
    def upload_chunks(self, chunks: List[DocumentData], namespace: str):
        print(f"--- VectorService: Embedding & Uploading {len(chunks)} chunks ---")
        
        # 1. Prepare texts for batch embedding
        texts = [chunk.text for chunk in chunks]
        
        # 2. Generate Vectors (Locally)
        vectors = self._get_embeddings_batch(texts)
        
        vectors_to_upsert = []
        
        # 3. Zip them together and prepare for Pinecone
        for i, chunk in enumerate(chunks):
            # Create Unique ID
            chunk_id = f"{chunk.metadata['source']}_{chunk.metadata['chunk_index']}"
            
            metadata = {
                "text": chunk.text,
                **chunk.metadata
            }
            
            vectors_to_upsert.append({
                "id": chunk_id,
                "values": vectors[i], # The 384-dim vector
                "metadata": metadata
            })
        
        # 4. Upsert
        # Pinecone recommends batches of 100
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i : i + batch_size]
            self.index.upsert(vectors=batch, namespace=namespace)
            
        print(f"--- Upload Complete to namespace: {namespace} ---")
    def search(self, query_text: str, namespace: str, k: int = 3) -> List[RetrievedChunk]:
        """Search for similar text in the vector store."""
        print(f"--- VectorService: Searching for '{query_text}' in namespace '{namespace}' ---")
        
        query_vector = self.model.encode(query_text).tolist()
        
        # Step 2: Query Pinecone
        results = self.index.query(
            namespace=namespace,
            vector=query_vector,
            top_k=k, 
            include_metadata=True 
        )
        
        # Debug: Print raw results to see what we get
        print(f"   > Raw results type: {type(results)}")
        print(f"   > Results: {results}")
        
        # Step 3: Extract the text
        # Handle both dict-style and object-style responses
        chunks=[]
        
        # Get matches - Pinecone v3+ returns object, older versions return dict
        matches = results.matches if hasattr(results, 'matches') else results.get('matches', [])
        
        print(f"   > Found {len(matches)} matches")
        
        for match in matches:
            # Handle both object-style and dict-style access
            if hasattr(match, 'metadata'):
                text_content = match.metadata.get('text', 'No text found')
                full_metadata = dict(match.metadata) 
                score = match.score
            else:
                text_content = match.get('metadata', {}).get('text', 'No text found')
                full_metadata = match.get('metadata', {})
                score = match.get('score', 0)
            
            print(f"   > Found Match (Score: {score:.2f}): {text_content[:50]}...")
            chunk_obj = RetrievedChunk(
            text=text_content,
            metadata=full_metadata,  # Now includes source, chunk_index, etc.
            score=score
        )
            chunks.append(chunk_obj)
        return chunks
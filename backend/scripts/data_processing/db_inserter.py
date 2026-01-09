#!/usr/bin/env python3
"""
   
  DB   
"""

import psycopg2
import psycopg2.extras


def insert_documents_to_db(documents_list, conn):
    """
      DB 
    
    Args:
        documents_list:   (  'doc_id', 'doc_type', 'title', 'chunks'  )
        conn: PostgreSQL  
    
    Returns:
        tuple: (  ,   )
    """
    cur = conn.cursor()
    
    inserted_docs = 0
    inserted_chunks = 0
    
    for doc_data in documents_list:
        doc_id = doc_data['doc_id']
        
        #    
        cur.execute("SELECT doc_id FROM documents WHERE doc_id = %s", (doc_id,))
        if cur.fetchone():
            print(f"      : {doc_id} ()")
            continue
        
        #  
        cur.execute("""
            INSERT INTO documents (doc_id, doc_type, title, source_org, category_path, url, collected_at, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            doc_data['doc_id'],
            doc_data['doc_type'],
            doc_data['title'],
            doc_data.get('source_org'),
            doc_data.get('category_path'),
            doc_data.get('url'),
            doc_data.get('collected_at'),
            psycopg2.extras.Json(doc_data.get('metadata', {}))
        ))
        inserted_docs += 1
        
        #  
        for chunk in doc_data['chunks']:
            cur.execute("""
                INSERT INTO chunks (chunk_id, doc_id, chunk_index, chunk_total, chunk_type, content, content_length, embedding, embedding_model, drop)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                chunk['chunk_id'],
                doc_data['doc_id'],
                chunk['chunk_index'],
                chunk['chunk_total'],
                chunk.get('chunk_type'),
                chunk['content'],
                chunk.get('content_length', len(chunk['content'])),
                None,  # embedding  
                'KURE-v1',
                chunk.get('drop', False)
            ))
            inserted_chunks += 1
    
    conn.commit()
    return inserted_docs, inserted_chunks

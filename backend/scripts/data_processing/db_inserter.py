#!/usr/bin/env python3
"""
데이터베이스 삽입 공통 유틸리티
문서와 청크를 DB에 삽입하는 공통 로직
"""

import psycopg2
import psycopg2.extras


def insert_documents_to_db(documents_list, conn):
    """
    문서와 청크를 DB에 삽입
    
    Args:
        documents_list: 문서 리스트 (각 문서는 'doc_id', 'doc_type', 'title', 'chunks' 등을 포함)
        conn: PostgreSQL 연결 객체
    
    Returns:
        tuple: (삽입된 문서 수, 삽입된 청크 수)
    """
    cur = conn.cursor()
    
    inserted_docs = 0
    inserted_chunks = 0
    
    for doc_data in documents_list:
        doc_id = doc_data['doc_id']
        
        # 문서가 이미 존재하는지 확인
        cur.execute("SELECT doc_id FROM documents WHERE doc_id = %s", (doc_id,))
        if cur.fetchone():
            print(f"  ⚠️  문서 이미 존재: {doc_id} (스킵)")
            continue
        
        # 문서 삽입
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
        
        # 청크 삽입
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
                None,  # embedding은 나중에 생성
                'KURE-v1',
                chunk.get('drop', False)
            ))
            inserted_chunks += 1
    
    conn.commit()
    return inserted_docs, inserted_chunks

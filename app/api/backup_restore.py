from fastapi import APIRouter, File, UploadFile, Depends
from fastapi.responses import StreamingResponse
import subprocess
import tempfile
import os
from app.database import get_db
from sqlalchemy.orm import Session
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["backup"])

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("POSTGRES_DB")

# Validate all required env vars are set
required_vars = {
    "POSTGRES_USER": DB_USER,
    "POSTGRES_PASSWORD": DB_PASSWORD,
    "DB_HOST": DB_HOST,
    "DB_PORT": DB_PORT,
    "POSTGRES_DB": DB_NAME
}

for var_name, var_value in required_vars.items():
    if not var_value:
        raise RuntimeError(f"Environment variable {var_name} is required")


@router.get("/backup")
async def backup_database():
    """Export entire database as SQL dump"""
    try:
        # Create temp file for the dump
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sql') as tmp:
            temp_path = tmp.name
        
        # Run pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = DB_PASSWORD
        
        cmd = [
            'pg_dump',
            '-h', DB_HOST,
            '-U', DB_USER,
            '-d', DB_NAME,
            '-v'
        ]
        
        logger.info(f"[BACKUP] Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            stdout=open(temp_path, 'w'),
            stderr=subprocess.PIPE,
            env=env,
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.decode() if result.stderr else "Unknown error"
            logger.error(f"[BACKUP] pg_dump failed: {error_msg}")
            os.unlink(temp_path)
            raise Exception(f"pg_dump failed: {error_msg}")
        
        logger.info(f"[BACKUP] Dump successful, size: {os.path.getsize(temp_path)} bytes")
        
        # Stream the file and delete after sending
        def file_iterator():
            with open(temp_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    yield chunk
            os.unlink(temp_path)
        
        return StreamingResponse(
            file_iterator(),
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=p1meter_backup.sql"}
        )
    
    except Exception as e:
        logger.error(f"[BACKUP] Error: {e}")
        raise Exception(f"Backup failed: {str(e)}")


@router.post("/restore")
async def restore_database(file: UploadFile = File(...)):
    """Restore database from SQL dump - drops all existing tables first"""
    temp_path = None
    try:
        # Read file content
        content = await file.read()
        sql_content = content.decode()
        
        logger.info(f"[RESTORE] Received file: {file.filename}, size: {len(content)} bytes")
        
        # Filter out incompatible PostgreSQL settings
        lines = sql_content.split('\n')
        filtered_lines = []
        for line in lines:
            # Skip lines with incompatible settings
            if 'transaction_timeout' in line.lower():
                logger.info(f"[RESTORE] Filtering incompatible setting: {line[:80]}")
                continue
            filtered_lines.append(line)
        
        filtered_sql = '\n'.join(filtered_lines)
        
        # Save filtered content to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.sql', mode='w') as tmp:
            temp_path = tmp.name
            tmp.write(filtered_sql)
        
        # Step 1: Drop all existing tables (clean restore)
        logger.info(f"[RESTORE] Dropping all existing tables...")
        env = os.environ.copy()
        env['PGPASSWORD'] = DB_PASSWORD
        
        drop_cmd = [
            'psql',
            '-h', DB_HOST,
            '-U', DB_USER,
            '-d', DB_NAME,
            '-c', 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
        ]
        
        drop_result = subprocess.run(
            drop_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=30
        )
        
        if drop_result.returncode != 0:
            error_msg = drop_result.stderr.decode() if drop_result.stderr else "Unknown error"
            logger.error(f"[RESTORE] Failed to drop schema: {error_msg}")
            # Continue anyway - schema might already exist
        
        # Step 2: Restore from file
        logger.info(f"[RESTORE] Restoring database from backup...")
        
        cmd = [
            'psql',
            '-h', DB_HOST,
            '-U', DB_USER,
            '-d', DB_NAME,
            '-f', temp_path,
            '-v', 'ON_ERROR_STOP=1'
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=60
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.decode() if result.stderr else "Unknown error"
            logger.error(f"[RESTORE] psql restore failed: {error_msg}")
            raise Exception(f"Restore failed: {error_msg}")
        
        output = result.stdout.decode() if result.stdout else ""
        logger.info(f"[RESTORE] Restore successful")
        logger.debug(f"[RESTORE] Output: {output}")
        
        return {"status": "ok", "message": "Database restored successfully"}
    
    except Exception as e:
        logger.error(f"[RESTORE] Error: {e}")
        raise Exception(f"Restore failed: {str(e)}")
    
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

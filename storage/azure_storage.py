"""
Azure Data Lake Storage (ADLS Gen2) utilities for job_intelligent.
Handles Bronze/Silver/Gold layer operations with Medallion Architecture.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, List

from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import (
    DataLakeServiceClient,
    DataLakeDirectoryClient,
    FileSystemClient
)

logger = logging.getLogger(__name__)

class AzureDataLake:
    """Production-ready ADLS Gen2 client for Medallion Architecture."""
    
    def __init__(
        self,
        account_name: Optional[str] = None,
        container_name: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        region: str = "norwayeast"
    ):
        # Load from env vars if not provided
        self.account_name = account_name or os.getenv("AZURE_STORAGE_ACCOUNT")
        self.container_name = container_name or os.getenv("AZURE_STORAGE_CONTAINER")
        self.region = region or os.getenv("AZURE_STORAGE_REGION", "norwayeast")
        
        # Auth credentials
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("AZURE_CLIENT_SECRET")
        
        if not all([self.account_name, self.container_name, self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Missing Azure credentials. Set env vars or pass to constructor.")
        
        # Initialize clients
        self.credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        self.service_client = DataLakeServiceClient(
            account_url=f"https://{self.account_name}.dfs.core.windows.net",
            credential=self.credential
        )
        self.file_system: FileSystemClient = self.service_client.get_file_system_client(self.container_name)
        
        logger.info(f"✅ Connected to ADLS Gen2: {self.account_name}/{self.container_name} ({self.region})")
    
    def upload_bronze(
        self,
        data: Union[dict, list, str, bytes],
        source: str,
        execution_date: Optional[datetime] = None,
        file_name: Optional[str] = None
    ) -> str:
        """Upload raw data to Bronze layer: /bronze/raw/{source}/{date}/{file}"""
        exec_date = execution_date or datetime.utcnow()
        date_path = exec_date.strftime("%Y/%m/%d")
        
        if not file_name:
            timestamp = exec_date.strftime("%Y%m%d_%H%M%S")
            file_name = f"{source}_{timestamp}.json"
        
        bronze_path = f"bronze/raw/{source}/{date_path}/{file_name}"
        
        if isinstance(data, (dict, list)):
            content = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        elif isinstance(data, str):
            content = data.encode("utf-8")
        else:
            content = data
        
        file_client = self.file_system.get_file_client(bronze_path)
        file_client.upload_data(content, overwrite=True)
        
        logger.info(f"📤 Bronze upload: {bronze_path} ({len(content)} bytes)")
        return bronze_path
    
    def list_bronze_files(
        self,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[str]:
        """List files in Bronze layer with optional filters."""
        prefix = "bronze/raw"
        if source:
            prefix += f"/{source}"
        
        paths = []
        for item in self.file_system.get_paths(path=prefix, recursive=True):
            if item["is_directory"]:
                continue
            paths.append(item["name"])
        return sorted(paths)
    
    def upload_silver(
        self,
        data: Union[dict, list],
        entity_type: str,
        execution_date: Optional[datetime] = None
    ) -> str:
        """Upload cleaned data to Silver layer as JSON (Parquet in production)."""
        exec_date = execution_date or datetime.utcnow()
        timestamp = exec_date.strftime("%Y%m%d_%H%M%S")
        silver_path = f"silver/cleaned/{entity_type}/{entity_type}_{timestamp}.json"
        
        content = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        file_client = self.file_system.get_file_client(silver_path)
        file_client.upload_data(content, overwrite=True)
        
        logger.info(f"📤 Silver upload: {silver_path}")
        return silver_path
    
    def upload_gold(
        self,
        data: Union[dict, list],
        aggregation_name: str,
        execution_date: Optional[datetime] = None
    ) -> str:
        """Upload aggregated data to Gold layer."""
        exec_date = execution_date or datetime.utcnow()
        date_path = exec_date.strftime("%Y/%m/%d")
        timestamp = exec_date.strftime("%Y%m%d_%H%M%S")
        
        gold_path = f"gold/aggregated/{aggregation_name}/{date_path}/{aggregation_name}_{timestamp}.json"
        
        content = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        file_client = self.file_system.get_file_client(gold_path)
        file_client.upload_data(content, overwrite=True)
        
        logger.info(f"📤 Gold upload: {gold_path}")
        return gold_path
    
    def download_file(self, adls_path: str, local_path: Optional[str] = None) -> bytes:
        """Download a file from ADLS to memory or local disk."""
        file_client = self.file_system.get_file_client(adls_path)
        stream = file_client.download_file()
        content = stream.readall()
        
        if local_path:
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(content)
            logger.info(f"📥 Downloaded: {adls_path} → {local_path}")
        
        return content
    
    def delete_file(self, adls_path: str) -> bool:
        """Delete a file from ADLS."""
        try:
            file_client = self.file_system.get_file_client(adls_path)
            file_client.delete_file()
            logger.info(f"🗑️  Deleted: {adls_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Delete failed: {adls_path} — {e}")
            return False


def get_azure_client() -> AzureDataLake:
    """Factory function to create ADLS client from env vars."""
    return AzureDataLake()


def upload_scraper_output_to_bronze(
    data: Union[dict, list],
    source: str,
    execution_date: Optional[datetime] = None
) -> str:
    """Airflow-friendly wrapper: upload scraper output to Bronze layer."""
    client = get_azure_client()
    return client.upload_bronze(data, source, execution_date)

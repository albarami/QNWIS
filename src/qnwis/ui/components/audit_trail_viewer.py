"""
Audit Trail Viewer for QNWIS UI (H8).

Provides ministerial-grade audit trail viewing with:
- Query history tracking
- Data lineage display
- Verification results
- Export capabilities
- Compliance tracking

Designed for Qatar Ministry of Labour regulatory compliance.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditTrailViewer:
    """
    Displays audit trails for completed queries.
    
    Shows:
    - Query history
    - Data sources used
    - Agent execution
    - Verification results
    - Citations and provenance
    """
    
    def __init__(self, audit_dir: str = "audit_packs"):
        """
        Initialize audit trail viewer.
        
        Args:
            audit_dir: Directory where audit packs are stored
        """
        self.audit_dir = Path(audit_dir)
        logger.info(f"AuditTrailViewer initialized with dir: {audit_dir}")
    
    def list_recent_audits(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent audit entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of audit summary dictionaries
        """
        if not self.audit_dir.exists():
            logger.warning(f"Audit directory not found: {self.audit_dir}")
            return []
        
        audits = []
        
        # Find all audit manifest files
        for audit_pack in sorted(self.audit_dir.iterdir(), reverse=True):
            if not audit_pack.is_dir():
                continue
            
            manifest_path = audit_pack / "audit_manifest.json"
            if not manifest_path.exists():
                continue
            
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                audits.append({
                    "audit_id": manifest.get("audit_id", "unknown"),
                    "request_id": manifest.get("request_id", "unknown"),
                    "created_at": manifest.get("created_at", ""),
                    "query_count": len(manifest.get("query_ids", [])),
                    "data_sources": len(manifest.get("data_sources", [])),
                    "pack_path": str(audit_pack)
                })
                
                if len(audits) >= limit:
                    break
            
            except Exception as e:
                logger.error(f"Failed to read audit manifest {manifest_path}: {e}")
                continue
        
        return audits
    
    def get_audit_details(self, audit_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed audit information.
        
        Args:
            audit_id: Audit ID to retrieve
            
        Returns:
            Audit manifest dictionary or None
        """
        # Search for audit pack with this ID
        for audit_pack in self.audit_dir.iterdir():
            if not audit_pack.is_dir():
                continue
            
            manifest_path = audit_pack / "audit_manifest.json"
            if not manifest_path.exists():
                continue
            
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                if manifest.get("audit_id") == audit_id:
                    return manifest
            
            except Exception as e:
                logger.error(f"Failed to read manifest {manifest_path}: {e}")
                continue
        
        return None
    
    def render_audit_summary(self, audit_id: str) -> str:
        """
        Render audit trail summary as markdown.
        
        Args:
            audit_id: Audit ID to display
            
        Returns:
            Markdown-formatted audit summary
        """
        manifest = self.get_audit_details(audit_id)
        
        if not manifest:
            return f"## Audit Trail Not Found\n\nAudit ID: `{audit_id}`"
        
        output = f"## 📋 Audit Trail: {audit_id[:8]}...\n\n"
        
        # Basic info
        output += "### Request Information\n\n"
        output += f"- **Audit ID**: `{manifest.get('audit_id')}`\n"
        output += f"- **Request ID**: `{manifest.get('request_id')}`\n"
        output += f"- **Created**: {manifest.get('created_at')}\n"
        output += f"- **Registry Version**: `{manifest.get('registry_version')}`\n\n"
        
        # Data sources
        sources = manifest.get('data_sources', [])
        if sources:
            output += "### 📊 Data Sources\n\n"
            output += f"Used {len(sources)} data sources:\n"
            for source in sources[:10]:  # Top 10
                output += f"- `{source}`\n"
            if len(sources) > 10:
                output += f"\n*... and {len(sources) - 10} more*\n"
            output += "\n"
        
        # Query IDs
        query_ids = manifest.get('query_ids', [])
        if query_ids:
            output += "### 🔍 Queries Executed\n\n"
            output += f"Executed {len(query_ids)} queries:\n"
            for qid in query_ids[:10]:
                output += f"- `{qid}`\n"
            if len(query_ids) > 10:
                output += f"\n*... and {len(query_ids) - 10} more*\n"
            output += "\n"
        
        # Verification
        verification = manifest.get('verification', {})
        if verification:
            output += "### ✅ Verification Results\n\n"
            passed = verification.get('passed', False)
            status = "✅ Passed" if passed else "⚠️ Issues Found"
            output += f"- **Status**: {status}\n"
            
            issues = verification.get('issues', [])
            if issues:
                output += f"- **Issues**: {len(issues)}\n"
                for issue in issues[:5]:
                    level = issue.get('level', 'unknown')
                    code = issue.get('code', 'unknown')
                    output += f"  - `{level.upper()}`: {code}\n"
            output += "\n"
        
        # Citations
        citations = manifest.get('citations', {})
        if citations:
            output += "### 📚 Citations\n\n"
            output += f"- **Total Claims**: {citations.get('total_claims', 0)}\n"
            output += f"- **Verified**: {citations.get('verified_claims', 0)}\n"
            output += f"- **Missing Citations**: {citations.get('missing_citations', 0)}\n\n"
        
        # Orchestration
        orchestration = manifest.get('orchestration', {})
        if orchestration:
            output += "### 🤖 Execution Details\n\n"
            agents = orchestration.get('agents', [])
            if agents:
                output += f"- **Agents**: {', '.join(agents)}\n"
            
            total_time = orchestration.get('total_latency_ms', 0)
            if total_time:
                output += f"- **Total Time**: {total_time:.0f}ms ({total_time/1000:.1f}s)\n"
            output += "\n"
        
        # Data freshness
        freshness = manifest.get('freshness', {})
        if freshness:
            output += "### ⏰ Data Freshness\n\n"
            dates = list(freshness.values())
            if dates:
                oldest = min(dates)
                newest = max(dates)
                output += f"- **Oldest**: {oldest}\n"
                output += f"- **Newest**: {newest}\n"
            output += "\n"
        
        # Reproducibility
        repro = manifest.get('reproducibility', {})
        if repro:
            output += "### 🔄 Reproducibility\n\n"
            params_hash = repro.get('params_hash', '')
            if params_hash:
                output += f"- **Parameters Hash**: `{params_hash}`\n"
            output += "- **Reproducible**: Yes (with audit pack)\n\n"
        
        # Integrity
        if manifest.get('digest_sha256'):
            output += "### 🔐 Integrity\n\n"
            output += f"- **SHA-256**: `{manifest['digest_sha256'][:16]}...`\n"
            if manifest.get('hmac_sha256'):
                output += f"- **HMAC**: `{manifest['hmac_sha256'][:16]}...`\n"
            output += "- **Tamper-Evident**: Yes\n\n"
        
        return output
    
    def render_query_history(self, limit: int = 10) -> str:
        """
        Render recent query history.
        
        Args:
            limit: Number of recent queries to show
            
        Returns:
            Markdown-formatted query history
        """
        audits = self.list_recent_audits(limit=limit)
        
        if not audits:
            return "## 📋 Query History\n\nNo audit records found."
        
        output = f"## 📋 Recent Query History ({len(audits)} records)\n\n"
        
        for idx, audit in enumerate(audits, 1):
            audit_id = audit['audit_id'][:8]
            created = audit['created_at']
            queries = audit['query_count']
            sources = audit['data_sources']
            
            # Parse timestamp
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                time_str = created
            
            output += f"### {idx}. Query Session `{audit_id}...`\n\n"
            output += f"- **Time**: {time_str}\n"
            output += f"- **Queries**: {queries}\n"
            output += f"- **Data Sources**: {sources}\n"
            output += f"- **Audit ID**: `{audit['audit_id']}`\n\n"
        
        return output
    
    def export_audit_trail(self, audit_id: str, format: str = "json") -> Optional[str]:
        """
        Export audit trail in specified format.
        
        Args:
            audit_id: Audit ID to export
            format: Export format (json, markdown)
            
        Returns:
            Exported content as string, or None if not found
        """
        manifest = self.get_audit_details(audit_id)
        
        if not manifest:
            return None
        
        if format == "json":
            return json.dumps(manifest, indent=2)
        
        elif format == "markdown":
            return self.render_audit_summary(audit_id)
        
        else:
            logger.error(f"Unsupported export format: {format}")
            return None


def format_audit_panel_for_ui(viewer: AuditTrailViewer, audit_id: Optional[str] = None) -> str:
    """
    Format audit trail panel for UI display.
    
    Args:
        viewer: AuditTrailViewer instance
        audit_id: Optional specific audit to display (shows history if None)
        
    Returns:
        Markdown-formatted audit panel
    """
    if audit_id:
        # Show specific audit details
        return viewer.render_audit_summary(audit_id)
    else:
        # Show recent history
        return viewer.render_query_history(limit=10)


def get_audit_stats(viewer: AuditTrailViewer) -> Dict[str, Any]:
    """
    Get audit trail statistics.
    
    Args:
        viewer: AuditTrailViewer instance
        
    Returns:
        Dictionary of statistics
    """
    audits = viewer.list_recent_audits(limit=100)
    
    if not audits:
        return {
            "total_audits": 0,
            "total_queries": 0,
            "unique_sources": 0
        }
    
    total_queries = sum(a['query_count'] for a in audits)
    all_sources = set()
    
    for audit in audits:
        manifest = viewer.get_audit_details(audit['audit_id'])
        if manifest:
            all_sources.update(manifest.get('data_sources', []))
    
    return {
        "total_audits": len(audits),
        "total_queries": total_queries,
        "unique_sources": len(all_sources),
        "oldest_audit": audits[-1]['created_at'] if audits else None,
        "newest_audit": audits[0]['created_at'] if audits else None
    }

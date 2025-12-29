"""
EnrichmentContext: 補完処理のコンテキスト（途中結果を保持）

Phase 2: 相互補完設計のためのデータ構造
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EnrichmentContext:
    """補完処理のコンテキスト（途中結果を保持）"""
    # 基本情報
    company_id: int
    company_name: str
    
    # gBizINFO APIの結果
    gbizinfo_corporate_number: Optional[str] = None
    gbizinfo_official_name: Optional[str] = None
    gbizinfo_address: Optional[str] = None
    gbizinfo_prefecture: Optional[str] = None
    gbizinfo_success: bool = False
    
    # AI補完の結果
    ai_findings: Optional[Dict[str, Any]] = None
    ai_official_name_candidates: List[str] = field(default_factory=list)
    ai_website_url: Optional[str] = None
    ai_person_name: Optional[str] = None
    ai_role: Optional[str] = None
    ai_english_name: Optional[str] = None
    ai_success: bool = False
    
    # 検索ヒント（次の探索に使用）
    search_hints: Dict[str, List[str]] = field(default_factory=lambda: {
        "name_variants": [],
        "address_hints": []
    })
    
    # 信頼度
    confidence: Dict[str, float] = field(default_factory=dict)
    
    # メタ情報
    status: str = "pending"  # pending, success, partial, failed
    skip_reason: Optional[str] = None
    
    def add_gbizinfo_result(self, result: Dict[str, Any]) -> None:
        """
        gBizINFO APIの結果をコンテキストに追加
        
        Args:
            result: gBizINFO APIの結果（corporate_number_client.pyのsearch()の戻り値形式）
        """
        if result.get("corporate_number"):
            self.gbizinfo_corporate_number = result["corporate_number"]
        if result.get("name"):
            self.gbizinfo_official_name = result["name"]
        if result.get("address"):
            self.gbizinfo_address = result["address"]
        if result.get("prefecture"):
            self.gbizinfo_prefecture = result["prefecture"]
        self.gbizinfo_success = True
    
    def add_ai_findings(self, findings: Dict[str, Any]) -> None:
        """
        AI補完の結果をコンテキストに追加
        
        Args:
            findings: AI補完の結果（JSON形式）
        """
        self.ai_findings = findings
        # 正式法人名候補を抽出（AI出力から）
        self.ai_official_name_candidates = findings.get("official_name_candidates", [])
        # その他のAI補完結果
        self.ai_website_url = findings.get("website_url", "") or findings.get("会社HP", "")
        self.ai_person_name = findings.get("contact_person_name", "") or findings.get("担当者名", "")
        self.ai_role = findings.get("contact_person_position", "") or findings.get("担当者役職", "")
        self.ai_english_name = findings.get("english_name", "")
        self.ai_success = bool(findings)
        
        # 検索ヒントを更新
        if self.ai_official_name_candidates:
            self.search_hints["name_variants"].extend(self.ai_official_name_candidates)
        if self.ai_english_name:
            self.search_hints["name_variants"].append(self.ai_english_name)
    
    def get_constraints_for_prompt(self) -> List[str]:
        """
        AIプロンプトに含める制約条件を取得
        
        Returns:
            制約条件のリスト
        """
        constraints = []
        if self.gbizinfo_official_name:
            constraints.append(f"- 正式法人名: {self.gbizinfo_official_name}")
        if self.gbizinfo_address:
            constraints.append(f"- 所在地: {self.gbizinfo_address}")
        if self.gbizinfo_corporate_number:
            constraints.append(f"- 法人番号: {self.gbizinfo_corporate_number}")
        return constraints
    
    def has_gbizinfo_constraints(self) -> bool:
        """gBizINFOの制約があるかどうか"""
        return bool(self.gbizinfo_official_name or self.gbizinfo_address or self.gbizinfo_corporate_number)
    
    def has_ai_hints_for_retry(self) -> bool:
        """gBizINFO再探索に使用できるAIのヒントがあるかどうか"""
        return bool(self.ai_official_name_candidates and not self.gbizinfo_success)

import os
import json
import logging
import re
from typing import Dict, Any, Optional
from backend.core.config import get_llm, extract_json, get_course_path, format_docs
from backend.core.prompts import MINDMAP_PROMPT
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

class MindmapGenerator:
    def __init__(self, rag_chains):
        self.rag = rag_chains
        self.course_id = rag_chains.course_id
        self.vectorstore = rag_chains.vectorstore

    def generate_mindmap(self, max_depth: int = 3) -> Dict[str, Any]:
        """Tạo cấu trúc Mindmap JSON từ tài liệu."""
        self.rag._require_ready()
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 15})
        context_query = "cấu trúc tài liệu và các luận điểm chính hệ thống hóa"
        docs = retriever.invoke(context_query)
        context = format_docs(docs)
        citations = []
        for doc in docs:
            citations.append({
                "page": doc.metadata.get("page", "N/A"),
                "source": os.path.basename(doc.metadata.get("source_file", doc.metadata.get("source", "unknown"))),
                "chunk_id": doc.metadata.get("chunk_id", f"chunk_{hash(doc.page_content) % 10000}")
            })
        llm = get_llm(temperature=0.2)
        prompt = ChatPromptTemplate.from_messages([
            ("system", MINDMAP_PROMPT),
            ("human", "Tạo bản đồ tư duy cho tài liệu này."),
        ])
        
        chain = prompt | llm | StrOutputParser()
        
        try:
            raw_res = chain.invoke({
                "context": context, 
                "max_depth": max_depth 
            })
            
            clean_json = extract_json(raw_res)
            mindmap_dict = json.loads(clean_json)

            final_response = {
                "course_id": self.course_id,
                "mindmap": mindmap_dict,
                "citations": citations[:5]
            }

            # Lưu file
            paths = get_course_path(self.course_id)
            save_dir = paths["mindmaps"]
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, "mindmap.json")
            
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(final_response, f, indent=2, ensure_ascii=False)
            
            return final_response
        except Exception as e:
            logger.warning("Mindmap generation failed, using fallback: %s", e)
            branches = []
            for index, doc in enumerate(docs[: max_depth * 3], 1):
                text = doc.page_content
                text = re.sub(r"===\s*BẮT ĐẦU.*?===", " ", text, flags=re.IGNORECASE | re.DOTALL)
                text = re.sub(r"===\s*KẾT THÚC.*?===", " ", text, flags=re.IGNORECASE | re.DOTALL)
                text = re.sub(r"\[MÃ ĐỊNH DANH TRANG:\s*\d+\]", " ", text, flags=re.IGNORECASE)
                text = re.sub(r"\bNỘI DUNG:\s*", " ", text, flags=re.IGNORECASE)
                text = re.sub(r"\bMã định danh trang\s+\d+\s+nội dung\b", " ", text, flags=re.IGNORECASE)
                text = re.sub(r"\s+", " ", text).strip()
                words = re.findall(r"\w+", text, flags=re.UNICODE)
                title = " ".join(words[:8]).strip() or f"Ý chính {index}"
                branches.append({"title": title.capitalize(), "children": []})

            mindmap_dict = {
                "central_topic": "Tài liệu học tập",
                "branches": branches or [{"title": "Nội dung chính", "children": []}],
            }
            final_response = {
                "course_id": self.course_id,
                "mindmap": mindmap_dict,
                "citations": citations[:5],
            }

            try:
                paths = get_course_path(self.course_id)
                save_dir = paths["mindmaps"]
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, "mindmap.json")
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(final_response, f, indent=2, ensure_ascii=False)
            except Exception as save_error:
                logger.warning("Could not save fallback mindmap: %s", save_error)

            return final_response

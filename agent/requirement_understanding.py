"""LLM-powered requirement understanding for PM Copilot."""

import json

from pydantic import ValidationError

from llm.client import LLMClient, create_llm_client
from llm.config import LLMConfig
from models.understanding import ClarificationQuestion, RequirementUnderstandingResult


class RequirementUnderstandingService:
    """Converts a user request into a structured understanding result."""

    def __init__(self) -> None:
        """Initialize the configured LLM client."""
        config = LLMConfig.from_env()
        self.llm_client: LLMClient = create_llm_client(config)

    def understand(self, user_request: str) -> RequirementUnderstandingResult:
        """Analyze a product request or return the local empty-input fallback."""
        if not user_request.strip():
            return RequirementUnderstandingResult(
                missing_information=["原始产品需求"],
                need_clarification=True,
                questions=[
                    ClarificationQuestion(
                        question="你希望我帮你规划什么产品或功能？",
                        reason="需要先明确产品任务，才能开始后续分析。",
                    )
                ],
            )

        system_prompt = """你是一名专业产品经理，负责分析用户输入的模糊产品需求。
当前是第一轮需求理解阶段，目标只是理解产品问题，不是设计完整方案，也不要过度扩展需求。
你必须只返回合法 JSON，不要输出 Markdown，也不要输出 JSON 之外的说明文字。
JSON 结构必须严格为：
{
  "known_facts": ["..."],
  "missing_information": ["..."],
  "need_clarification": true,
  "questions": [
    {
      "question": "...",
      "reason": "..."
    }
  ]
}
规则：
1. known_facts 只能来自用户明确说过的内容。禁止把行业常识、推测或推荐方案写成事实。
2. missing_information 只保留会显著影响产品方向的信息。检查当前业务现状、核心问题或产品目标、目标用户、核心使用场景、产品范围或关键约束；这些信息不要求全部存在。
3. 除非用户原始需求明确提到，否则不要优先展开技术架构、数据库、ERP/MES 集成、权限系统、多工厂、API 或自动化硬件。
4. 根据需求完整程度动态生成 0～4 个问题。信息已足够时 questions 必须为空且 need_clarification 必须为 false；只缺一个关键条件时只问 1 个问题。禁止为了凑数量提问。
5. 只询问缺失后会明显影响产品规划的内容，优先询问影响最大的未知信息，并合并重复或高度相关的问题。
6. 不要把解决方案选项提前塞进问题。应优先问“目前刀具是如何管理的？”，避免问“是只做库存，还是做修磨、寿命、涂层、报废？”这类带方案预设的问题。
7. question 必须简洁。reason 必须解释为什么这个答案会改变后续产品方案。
8. 不询问能从原始需求、已知事实、用户已选内部知识或已有上下文合理获得的信息，也不询问对当前规划没有明显影响的细节。
9. 当前阶段不要讨论数据库表结构、技术选型或研发周期。
10. 每个 question 必须包含 reason，按重要程度从高到低排列，所有字段都必须存在并符合上述 JSON 类型。"""
        user_prompt = f"请分析以下产品需求：\n{user_request}"
        response = self.llm_client.generate(system_prompt, user_prompt)

        try:
            parsed_response = json.loads(response)
            result = RequirementUnderstandingResult.model_validate(parsed_response)
            questions = []
            seen_questions: set[str] = set()
            for item in result.questions:
                normalized_question = "".join(item.question.split())
                if not normalized_question or normalized_question in seen_questions:
                    continue
                seen_questions.add(normalized_question)
                questions.append(item)
                if len(questions) == 4:
                    break

            need_clarification = result.need_clarification and bool(questions)
            return result.model_copy(
                update={
                    "need_clarification": need_clarification,
                    "questions": questions if need_clarification else [],
                }
            )
        except (json.JSONDecodeError, ValidationError) as error:
            raise ValueError("Invalid LLM understanding response") from error

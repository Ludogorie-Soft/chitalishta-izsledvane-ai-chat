# Sample RAG Questions for Chitalishta System

This document provides sample questions that can be answered using the RAG (Retrieval-Augmented Generation) system. These questions are designed to test semantic understanding and retrieval capabilities.

## LLM Selection Strategy

The system uses a **two-tier LLM approach** for cost optimization:

1. **Basic LLM (e.g., `gpt-4o-mini`)**: Used for ALL initial queries
   - Fast and cost-effective
   - Handles most questions when relevant documents are retrieved
   - Should work for straightforward questions with clear answers in the documents

2. **Fallback LLM (e.g., `gpt-4o`)**: Only used when basic LLM returns "no information"
   - More powerful and expensive
   - Automatically triggered if initial answer contains "Нямам информация за тази заявка"
   - Used for complex questions requiring deeper reasoning or better context understanding

**When Fallback is Triggered:**
- Initial answer indicates "no information" (even if documents were retrieved)
- Basic LLM couldn't extract answer from context (requires better reasoning)
- Question is ambiguous or requires synthesis across multiple document chunks

**When Basic LLM Should Work:**
- Question has clear answer in retrieved documents
- Documents are semantically similar to the question
- Answer can be directly extracted from context
- Question is straightforward and well-formed

**Note**: With a properly indexed vector database, most questions should work with the basic LLM. The fallback is a safety net for edge cases.

## Questions About Financing and Income

1. **"Може ли читалищата да имат собствени приходи?"**
   - **Expected LLM**: Basic (should work if documents are indexed)
   - Expected answer: Yes, based on the paragraph mentioning "собствени приходи на читалищата"
   - Tests: Semantic matching of "собствени приходи" (own income)
   - **Note**: If basic LLM says "no information", fallback will retry. This should work with basic LLM if documents contain the relevant paragraph.

2. **"Как се финансират читалищата?"**
   - **Expected LLM**: Basic (should work if documents are indexed)
   - Expected answer: Information about state financing, delegated to municipalities, and own income
   - Tests: General understanding of financing mechanisms
   - **Note**: Straightforward question - basic LLM should handle this if relevant documents are retrieved.

3. **"Откъде идват средствата за функциониране на читалищата?"**
   - **Expected LLM**: Basic (should work if documents are indexed)
   - Expected answer: Combination of state subsidies, municipal subsidies, and own income
   - Tests: Multiple source understanding
   - **Note**: Similar to question #2 - should work with basic LLM.

4. **"Какво е единният разходен стандарт?"**
   - **Expected LLM**: Basic (should work if documents are indexed)
   - Expected answer: The standard that determines funding amount each year
   - Tests: Definition retrieval
   - **Note**: Definition question - basic LLM should extract this from context if document mentions it.

## Questions About Structure and Organization

5. **"Каква е структурата на читалищата?"**
   - **Expected LLM**: Basic (if structure info exists) or Fallback (if requires synthesis)
   - Expected answer: Information about organizational structure, if available in documents
   - Tests: Structural information retrieval
   - **Note**: May need fallback if answer requires combining multiple document sections.

6. **"Какви са основните дейности на читалищата?"**
   - **Expected LLM**: Basic (should work if documents list activities)
   - Expected answer: Activities like library services, cultural events, education, etc.
   - Tests: Activity description retrieval
   - **Note**: Should work with basic LLM if documents contain activity lists.

7. **"Какво е ролята на общините спрямо читалищата?"**
   - **Expected LLM**: Basic (should work if documents explain relationship)
   - Expected answer: Municipalities receive delegated activity from the state
   - Tests: Relationship understanding
   - **Note**: Relationship question - basic LLM should handle if context is clear.

## Questions About History and Context

8. **"Каква е историята на читалищното движение в България?"**
   - **Expected LLM**: Fallback (likely requires synthesis across multiple sections)
   - Expected answer: Historical context about chitalishta movement
   - Tests: Historical information retrieval
   - **Note**: Complex question requiring narrative synthesis - may need fallback LLM.

9. **"Кога са създадени първите читалища?"**
   - **Expected LLM**: Basic (if date is in documents)
   - Expected answer: Historical dates and context
   - Tests: Specific fact retrieval
   - **Note**: Specific fact - basic LLM should work if date is mentioned in documents.

10. **"Какво е значението на читалищата за българската култура?"**
    - **Expected LLM**: Fallback (conceptual question requiring deeper understanding)
    - Expected answer: Cultural significance and role
    - Tests: Conceptual understanding
    - **Note**: Abstract/conceptual question - may need fallback for better reasoning.

## Questions About Operations

11. **"Как се управляват читалищата?"**
    - **Expected LLM**: Basic (if management info exists) or Fallback (if requires synthesis)
    - Expected answer: Management structure and processes
    - Tests: Operational information
    - **Note**: May need fallback if answer requires combining multiple document parts.

12. **"Какви са изискванията за откриване на читалище?"**
    - **Expected LLM**: Basic (if requirements are listed)
    - Expected answer: Requirements and procedures
    - Tests: Procedural information
    - **Note**: Should work with basic LLM if documents contain requirements list.

13. **"Какво е единният разходен стандарт?"**
    - **Expected LLM**: Basic (definition question)
    - Expected answer: The standard that determines funding amount each year
    - Tests: Definition and explanation retrieval
    - **Note**: Definition question - basic LLM should extract from context.

## Questions About Legal and Regulatory Framework

14. **"Какви са правните рамки за читалищата?"**
    - **Expected LLM**: Basic (if legal info exists) or Fallback (if requires synthesis)
    - Expected answer: Legal framework and regulations
    - Tests: Legal information retrieval
    - **Note**: May need fallback if legal information is scattered across documents.

15. **"Какви са задълженията на читалищата?"**
    - **Expected LLM**: Basic (if obligations are listed)
    - Expected answer: Obligations and responsibilities
    - Tests: Requirement understanding
    - **Note**: Should work with basic LLM if documents contain obligations list.

## Questions About Programs and Activities

16. **"Какви програми предлагат читалищата?"**
    - **Expected LLM**: Basic (if programs are listed)
    - Expected answer: Programs and services offered
    - Tests: Service description retrieval
    - **Note**: Should work with basic LLM if documents list programs.

17. **"Какви са основните културни дейности?"**
    - **Expected LLM**: Basic (if activities are listed)
    - Expected answer: Cultural activities and events
    - Tests: Activity categorization
    - **Note**: Should work with basic LLM if documents contain activity information.

## Questions Requiring Synthesis

18. **"Обясни как работи финансирането на читалищата."**
    - **Expected LLM**: Fallback (requires comprehensive synthesis)
    - Expected answer: Comprehensive explanation combining multiple sources
    - Tests: Multi-document synthesis
    - **Note**: Complex synthesis question - likely needs fallback LLM for better reasoning.

19. **"Каква е връзката между държавата, общините и читалищата?"**
    - **Expected LLM**: Fallback (requires understanding relationships across multiple concepts)
    - Expected answer: Relationship between different levels
    - Tests: Relationship mapping
    - **Note**: Multi-entity relationship question - may need fallback for better understanding.

20. **"Разкажи за читалищното движение в България."**
    - **Expected LLM**: Fallback (requires narrative synthesis)
    - Expected answer: Comprehensive narrative about the movement
    - Tests: Narrative generation from multiple sources
    - **Note**: Narrative question requiring synthesis - likely needs fallback LLM.

## LLM Selection Summary

### Questions That Should Work with Basic LLM (gpt-4o-mini):

✅ **Simple factual questions** with clear answers in documents:
- "Може ли читалищата да имат собствени приходи?" (if documents contain this info)
- "Как се финансират читалищата?" (if documents explain financing)
- "Какво е единният разходен стандарт?" (if definition exists)
- "Какво е ролята на общините спрямо читалищата?" (if relationship is explained)
- "Кога са създадени първите читалища?" (if date is mentioned)
- "Какви са изискванията за откриване на читалище?" (if requirements are listed)

✅ **Definition questions** with direct answers:
- Questions asking "Какво е...?" (What is...?)
- Questions asking "Какво означава...?" (What does... mean?)

✅ **List questions** with enumerated answers:
- "Какви са основните дейности?" (What are the main activities?)
- "Какви програми предлагат?" (What programs do they offer?)

### Questions That May Need Fallback LLM (gpt-4o):

⚠️ **Complex synthesis questions** requiring combining multiple sources:
- "Обясни как работи финансирането..." (Explain how financing works...)
- "Разкажи за читалищното движение..." (Tell about the chitalishta movement...)
- "Каква е връзката между..." (What is the relationship between...)

⚠️ **Abstract/conceptual questions** requiring deeper reasoning:
- "Какво е значението на читалищата за културата?" (What is the significance...?)
- Questions requiring interpretation and analysis

⚠️ **Ambiguous questions** where context is unclear:
- Questions that could have multiple interpretations
- Questions where retrieved documents don't directly answer

### Important Notes:

1. **With properly indexed documents**, most straightforward questions should work with the basic LLM
2. **Fallback is automatic** - you don't need to configure which questions use it
3. **Fallback only triggers** when basic LLM returns "no information"
4. **If basic LLM finds relevant documents but can't extract answer**, fallback will retry
5. **Cost optimization**: Most queries use cheap model, expensive model only when needed

## Tips for Better RAG Results

1. **Use natural language**: Questions should be phrased naturally, not as keyword searches
2. **Ask conceptual questions**: RAG works best with questions about concepts, explanations, and relationships
3. **Avoid exact matches**: The system should find semantically similar content even if wording differs
4. **Use Bulgarian**: All questions should be in Bulgarian to match the document language
5. **Be specific but not too narrow**: Questions should be specific enough to find relevant content but broad enough to allow semantic matching

## Expected Behavior

- **Semantic matching**: The system should find relevant content even when exact words don't match
- **Context understanding**: The system should understand context and relationships
- **Multi-document synthesis**: The system should combine information from multiple document chunks when needed
- **Bulgarian language support**: The system should handle Bulgarian language nuances and variations
- **Automatic fallback**: System automatically uses more powerful LLM when basic LLM can't find answer


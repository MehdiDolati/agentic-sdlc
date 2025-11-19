# A Test project for LLM usage

## Problem
This project aims to assess the capabilities and limitations of Large Language Models (LLMs) in generating structured planning documents, specifically PRDs, OpenAPI specifications, and detailed implementation plans, based on a succinct prompt. The current manual process for creating these documents is time-consuming and prone to inconsistencies, hindering rapid development cycles.

## Goals
*   To successfully generate a comprehensive Product Requirements Document (PRD) from a high-level project description.
*   To accurately develop a valid OpenAPI 3.1 specification for a hypothetical API endpoint related to the project.
*   To produce a detailed, prioritized, and logically sequenced implementation plan with size estimates and acceptance criteria for both plans and individual features.
*   To evaluate the LLM's ability to adhere to strict JSON output formatting requirements.

## Non-Goals
*   Actual software development or deployment of the described features.
*   Performance testing or optimization of the hypothetical API.
*   Deep domain-specific feature definition beyond what is implied by the prompt.
*   User interface design or implementation.

## Success Criteria
*   The generated output is a single, valid JSON object as per the problem description.
*   The `prd_markdown` key contains a well-structured markdown document with the specified sections (H1 title, problem, goals, non-goals, success criteria).
*   The `openapi_yaml` key contains a minimal, valid OpenAPI 3.1 YAML specification.
*   The `implementation_plan` array contains at least one plan, and each plan and feature object within it adheres strictly to the defined schema regarding keys, types, and allowed values (e.g., priority levels, integer estimates).
*   All plans and features within the `implementation_plan` are explicitly assigned a priority.
*   `size_estimate_days` for plans and `size_estimate_hours` for features are positive integers.
*   Each feature includes a non-empty `acceptance_criteria` array with bullet strings.

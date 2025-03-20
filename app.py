import os
from openai import AzureOpenAI
import json
import re

def get_azure_client():
    """Initialize and return the Azure OpenAI client."""
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    
    client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=api_key,
        api_version="2024-10-01-preview",
    )
    return client

def validate_trademark_relevance(conflicts_array, proposed_goods_services):
    """
    Pre-filter trademarks that don't have similar or identical goods/services
    This function is implemented in code rather than relying on GPT
    
    Args:
        conflicts_array: List of trademark conflicts
        proposed_goods_services: Goods/services of the proposed trademark
        
    Returns:
        filtered_conflicts: List of relevant trademark conflicts
        excluded_count: Number of trademarks excluded
    """
    # Parse conflicts_array if it's a string (assuming JSON format)
    if isinstance(conflicts_array, str):
        try:
            conflicts = json.loads(conflicts_array)
        except json.JSONDecodeError:
            # If it's not valid JSON, try to parse it as a list of dictionaries
            conflicts = eval(conflicts_array) if conflicts_array.strip().startswith("[") else []
    else:
        conflicts = conflicts_array
    
    # Initialize lists for relevant and excluded trademarks
    relevant_conflicts = []
    excluded_count = 0
    
    # Define a function to check similarity between goods/services
    def is_similar_goods_services(existing_goods, proposed_goods):
        # Convert to lowercase for case-insensitive comparison
        existing_lower = existing_goods.lower()
        proposed_lower = proposed_goods.lower()
        
        # Check for exact match
        if existing_lower == proposed_lower:
            return True
        
        # Check if one contains the other
        if existing_lower in proposed_lower or proposed_lower in existing_lower:
            return True
        
        # Check for overlapping keywords
        # Extract significant keywords from both descriptions
        existing_keywords = set(re.findall(r'\b\w+\b', existing_lower))
        proposed_keywords = set(re.findall(r'\b\w+\b', proposed_lower))
        
        # Remove common stop words
        stop_words = {'and', 'or', 'the', 'a', 'an', 'in', 'on', 'for', 'of', 'to', 'with'}
        existing_keywords = existing_keywords - stop_words
        proposed_keywords = proposed_keywords - stop_words
        
        # Calculate keyword overlap
        if len(existing_keywords) > 0 and len(proposed_keywords) > 0:
            overlap = len(existing_keywords.intersection(proposed_keywords))
            overlap_ratio = overlap / min(len(existing_keywords), len(proposed_keywords))
            
            # If significant overlap (more than 30%), consider them similar
            if overlap_ratio > 0.3:
                return True
        
        return False
    
    # Process each conflict
    for conflict in conflicts:
        # Ensure conflict has goods/services field
        if 'goods_services' in conflict:
            if is_similar_goods_services(conflict['goods_services'], proposed_goods_services):
                relevant_conflicts.append(conflict)
            else:
                excluded_count += 1
        else:
            # If no goods/services field, include it for safety
            relevant_conflicts.append(conflict)
    
    return relevant_conflicts, excluded_count

def filter_by_gpt_response(conflicts, gpt_json):
    """
    Removes trademarks that GPT flagged as lacking goods/services overlap.
    
    Args:
        conflicts: Original list of trademark conflicts
        gpt_json: JSON object from GPT with 'results' key
    
    Returns:
        Filtered list of conflicts that GPT identified as overlapping
    """
    # Parse the GPT response if it's a string
    if isinstance(gpt_json, str):
        try:
            gpt_json = json.loads(gpt_json)
        except json.JSONDecodeError:
            # If JSON is invalid, keep original conflicts
            return conflicts
    
    gpt_results = gpt_json.get("results", [])
    
    # Build a set of marks with overlap for quick membership checking
    overlapping_marks = {
        result["mark"]
        for result in gpt_results
        if result.get("overlap") is True
    }
    
    # Retain conflicts only if they appear in overlapping_marks
    filtered_conflicts = [
        c for c in conflicts
        if c.get("mark") in overlapping_marks
    ]
    
    return filtered_conflicts

def initial_mark_analysis(conflicts_array, proposed_name, proposed_class, proposed_goods_services):
    """
    Perform Steps 1-6: Initial Mark Analysis
    - First filter out irrelevant trademarks
    - Then send only relevant trademarks to GPT for analysis
    """
    # Pre-filter trademarks before sending to GPT
    relevant_conflicts, excluded_count = validate_trademark_relevance(conflicts_array, proposed_goods_services)
    
    # Create the system prompt with clearer instructions
    system_prompt = """
    You are a trademark expert attorney specializing in trademark opinion writing. Analyze the provided trademark data and provide a professional opinion on registration and use risks.
    
    Follow these steps for your analysis:
    
    Step 1: Verify and Deconstruct the Compound Mark
    - Confirm if the proposed trademark is a compound mark (combination of words/elements).
    - Deconstruct it into its formative components.
    - Example: "MOUNTAIN FRESH" → "MOUNTAIN" and "FRESH"
    
    Step 2: Identify Identical Trademarks
    - List existing trademarks with identical names to the proposed trademark.
    - Only consider trademarks with identical or similar goods/services.
    
    Step 3: Identify Phonetically/Semantically Equivalent Marks
    - List marks that sound similar or have similar meanings to the proposed trademark.
    - Only consider trademarks with identical or similar goods/services.
    
    Step 4: Identify Marks with One-Letter Differences
    - List similar marks that differ by one letter from the proposed trademark.
    - Only consider trademarks with identical or similar goods/services.
    
    Step 5: Identify Marks with Two-Letter Differences
    - List similar marks that differ by two letters from the proposed trademark.
    - Only consider trademarks with identical or similar goods/services.
    
    Step 6: Perform Crowded Field Analysis
    - If Steps 4 and 5 yield more than 20 marks, check their ownership.
    - If more than `50%` have different owners, consider it a crowded field.
    - If it's a crowded field, the final risk assessment should be reduced by one level.
    
    IMPORTANT: We have already filtered out trademarks with unrelated goods/services. All trademarks in your input ARE relevant to the proposed trademark's goods/services. You do not need to filter them further.
    
    YOUR RESPONSE MUST END WITH A JSON SUMMARY in this exact format:
    {
      "results": [
        {
          "mark": "[TRADEMARK NAME]",
          "similarity_type": "[IDENTICAL|PHONETIC|ONE_LETTER|TWO_LETTER]",
          "overlap": true,
          "risk_level": "[HIGH|MEDIUM|LOW]",
          "class_match": true|false,
          "goods_services_match": true|false
        },
        ...additional marks...
      ],
      "summary": {
        "identical_count": [NUMBER],
        "phonetic_count": [NUMBER],
        "one_letter_count": [NUMBER],
        "two_letter_count": [NUMBER],
        "crowded_field": [true|false]
      }
    }
    """
    
    client = get_azure_client()
    
    # Construct a message that includes the pre-filtering information
    user_message = f"""
    Trademark Details:
    {json.dumps(relevant_conflicts, indent=2)}
    
    Analyze the Proposed Trademark "{proposed_name}" focusing on Steps 1-6: Initial mark analysis.
    Mark Searched = {proposed_name}
    Classes Searched = {proposed_class}
    Goods and Services = {proposed_goods_services}
    
    Note: {excluded_count} trademarks with unrelated goods/services have already been filtered out.
    
    For each mark, determine:
    - "Class Match" (True/False): Whether the mark's class exactly matches the proposed class "{proposed_class}".
    - "Goods & Services Match" (True/False): Whether the mark's goods/services are similar to the proposed goods/services "{proposed_goods_services}".
    
    REMEMBER: End your response with the JSON summary as specified in the instructions.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0,
        )
        
        # Extract and return the response content
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            
            # Extract JSON summary for further processing
            json_match = re.search(r'```json\s*({[\s\S]*?})\s*```|({[\s\S]*?"summary"\s*:[\s\S]*?})', content)
            if json_match:
                json_str = json_match.group(1) or json_match.group(2)
                try:
                    json_data = json.loads(json_str)
                    # Store the structured data for later filtering
                    return {
                        "analysis": content,
                        "json_data": json_data
                    }
                except json.JSONDecodeError:
                    pass
            
            return content
        else:
            return "Error: No response received from the language model."
    except Exception as e:
        return f"Error during initial mark analysis: {str(e)}"

def overall_compound_mark_analysis(conflicts_array, proposed_name, proposed_class, proposed_goods_services):
    """
    Perform Step 7: Overall Compound Mark Analysis
    - Pre-filter trademarks before sending to GPT
    """
    # Pre-filter trademarks before sending to GPT
    relevant_conflicts, excluded_count = validate_trademark_relevance(conflicts_array, proposed_goods_services)
    
    # Create a clearer system prompt
    system_prompt = """
    You are a trademark expert attorney specializing in trademark opinion writing.
    
    Perform Step 7: Overall Compound Mark Analysis using the following structure:
    
    a. Identical Trademarks
    - List trademarks that are identical to the proposed trademark.
    - Assess their potential for confusion or conflict.
    
    b. Phonetic and Semantic Equivalents
    - List trademarks that are phonetically or semantically similar to the proposed trademark.
    - Example: For "AQUASHINE," similar marks might include "AQUASHINE," "AQUACHINE," or "AKWASHINE."
    - Evaluate the likelihood of confusion.
    
    c. Marks with Letter Differences
    Step 7.c.1: One-Letter Differences
    - List trademarks that differ by one letter from the proposed trademark.
    - Example: For "AQUASHINE," consider marks like "AQUASHINC" or "AQUATHINE."
    - Assess the impact on consumer perception.
    
    Step 7.c.2: Two-Letter Differences
    - List trademarks that differ by two letters from the proposed trademark.
    - Example: For "AQUASHINE," consider "AQUASHAME" or "AQUASLINE."
    - Evaluate whether these differences create confusion.
    
    d. Crowded Field Analysis
    - If Steps (b) and (c) return more than 20 similar marks, analyze ownership patterns.
    - If over `50%` are owned by different entities, classify the field as crowded.
    - If it's a crowded field, reduce the overall risk assessment by one level.
    
    e. Aggressive Enforcement and Litigious Behavior
    - Investigate whether owners of similar trademarks have a history of aggressive enforcement.
    - Document any patterns of enforcement behavior.
    
    IMPORTANT: We have already filtered out trademarks with unrelated goods/services. All trademarks in your input ARE relevant to the proposed trademark's goods/services. You do not need to filter them further.
    
    YOUR RESPONSE MUST END WITH A JSON SUMMARY in this exact format:
    {
      "results": [
        {
          "mark": "[TRADEMARK NAME]",
          "similarity_type": "[IDENTICAL|PHONETIC|ONE_LETTER|TWO_LETTER]",
          "overlap": true,
          "risk_level": "[HIGH|MEDIUM|LOW]"
        },
        ...additional marks...
      ],
      "summary": {
        "identical_count": [NUMBER],
        "phonetic_count": [NUMBER],
        "one_letter_count": [NUMBER],
        "two_letter_count": [NUMBER],
        "crowded_field": [true|false],
        "aggressive_enforcement": [true|false]
      }
    }
    """

    client = get_azure_client()
    
    # Construct a message that includes the pre-filtering information
    user_message = f"""
    Trademark Details:
    {json.dumps(relevant_conflicts, indent=2)}
    
    Analyze the Proposed Trademark "{proposed_name}" focusing on Step 7: Overall Compound Mark Analysis.
    Mark Searched = {proposed_name}
    Classes Searched = {proposed_class}
    Goods and Services = {proposed_goods_services}
    
    Note: {excluded_count} trademarks with unrelated goods/services have already been filtered out.
    
    REMEMBER: End your response with the JSON summary as specified in the instructions.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0,
        )
        
        # Extract and return the response content
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            
            # Extract JSON summary for further processing
            json_match = re.search(r'```json\s*({[\s\S]*?})\s*```|({[\s\S]*?"summary"\s*:[\s\S]*?})', content)
            if json_match:
                json_str = json_match.group(1) or json_match.group(2)
                try:
                    json_data = json.loads(json_str)
                    # Store the structured data for later filtering
                    return {
                        "analysis": content,
                        "json_data": json_data
                    }
                except json.JSONDecodeError:
                    pass
            
            return content
        else:
            return "Error: No response received from the language model."
    except Exception as e:
        return f"Error during overall compound mark analysis: {str(e)}"

def component_formative_mark_analysis(conflicts_array, proposed_name, proposed_class, proposed_goods_services):
    """
    Perform Step 8: Component (Formative) Mark Analysis
    - Pre-filter trademarks before sending to GPT
    """
    # Pre-filter trademarks before sending to GPT
    relevant_conflicts, excluded_count = validate_trademark_relevance(conflicts_array, proposed_goods_services)
    
    # Create a clearer system prompt
    system_prompt = """
    You are a trademark expert attorney specializing in trademark opinion writing.
    
    Perform Step 8: Component (Formative) Mark Analysis using the following structure:
    
    Step 8.a: Identify and Deconstruct the Compound Mark
    - Confirm if the proposed trademark is a compound mark (combination of words/elements).
    - Deconstruct it into its formative components.
    - Example: For "POWERHOLD," identify the components "POWER" and "HOLD".
    
    FOR EACH FORMATIVE COMPONENT, perform the following detailed analysis:
    
    Step 8.b: Identical Marks Analysis for Each Component
    - Only list trademarks that are identical to each individual formative component AND cover identical or similar goods/services.
    - Example: For "POWERHOLD," analyze "POWER" trademarks and "HOLD" trademarks separately.
    - If no identical marks pass validation for a component, state: "No identical trademarks covering similar goods/services were identified for [COMPONENT]."
    
    Step 8.c: Phonetic and Semantic Equivalents for Each Component
    - Only list trademarks that are phonetically or semantically similar to each formative component AND cover identical or similar goods/services.
    - Example: For "POWER," phonetically similar marks might include "POWR," "POWUR," or "PAWER." 
    - Evaluate whether these similar marks overlap in goods/services and assess the likelihood of confusion.
    
    Step 8.d: Marks with Letter Differences for Each Component
    Step 8.d.1: One-Letter Differences
    - Only list trademarks that differ by one letter from each formative component AND cover identical or similar goods/services.
    - Example: For "POWER," consider marks like "POWIR" or "POSER."
    - Assess the impact of these differences on consumer perception and the likelihood of confusion.
    
    Step 8.d.2: Two-Letter Differences
    - List ONLY trademarks that differ by two letters from each formative component AND cover relevant goods/services.
    - Example: For "POWER," consider "POWTR" or "PIWER."
    - Evaluate whether these differences create confusion in meaning or pronunciation.
    
    Step 8.e: Component Distinctiveness Analysis
    - For each component, classify its distinctiveness as Generic, Descriptive, Suggestive, Arbitrary, or Fanciful.
    - Consider the component in relation to the specific goods/services.
    - Example: For "POWER" in electrical equipment, it would be descriptive; for food services, it would be arbitrary.
    
    Step 8.f: Functional/Conceptual Relationship Analysis
    - For compound marks, analyze how the meaning of one component might relate functionally to another component in EXISTING marks.
    - Example: For "MIRAGRIP," identify marks where a component has a functional relationship similar to how "MIRA" relates to "GRIP" (e.g., "VISIONHOLD," "WONDERCLUTCH").
    - Only include marks with relevant goods/services.
    - Document the functional relationship between components and why they create similar commercial impressions.
     
    Step 8.g: Overall Component Risk Assessment
    - Provide a summary table with findings on each component:
      * Component name
      * Identical marks found
      * Phonetically/semantically similar marks found
      * Marks with letter differences found
      * Distinctiveness rating
      * Component-specific risk level (Low, Low-Medium, Medium, Medium-High, High)
    - Summarize key findings about the risks associated with each individual component.
    
    IMPORTANT: We have already filtered out ALL trademarks with unrelated goods/services. Your analysis should ONLY include trademarks with goods/services relevant to the proposed trademark.
    
    YOUR RESPONSE MUST END WITH A JSON SUMMARY in this exact format:
    {
      "components": [
        {
          "component": "[COMPONENT NAME]",
          "results": [
            {
              "mark": "[TRADEMARK NAME]",
              "similarity_type": "[IDENTICAL|PHONETIC|ONE_LETTER|TWO_LETTER]",
              "overlap": true,
              "risk_level": "[HIGH|MEDIUM|LOW]"
            },
            ...additional marks for this component...
          ],
          "distinctiveness": "[GENERIC|DESCRIPTIVE|SUGGESTIVE|ARBITRARY|FANCIFUL]",
          "risk_level": "[HIGH|MEDIUM-HIGH|MEDIUM|LOW-MEDIUM|LOW]"
        },
        ...additional components...
      ]
    }
    """
    
    client = get_azure_client()
    
    # Construct a message that includes the pre-filtering information
    user_message = f"""
    Trademark Details:
    {json.dumps(relevant_conflicts, indent=2)}
    
    Analyze the Proposed Trademark "{proposed_name}" focusing on Step 8: Component (Formative) Mark Analysis.
    Mark Searched = {proposed_name}
    Classes Searched = {proposed_class}
    Goods and Services = {proposed_goods_services}
    
    Note: {excluded_count} trademarks with unrelated goods/services have already been filtered out.
    
    REMEMBER: End your response with the JSON summary as specified in the instructions.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0,
        )
        
        # Extract and return the response content
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            
            # Extract JSON summary for further processing
            json_match = re.search(r'```json\s*({[\s\S]*?})\s*```|({[\s\S]*?"components"\s*:[\s\S]*?})', content)
            if json_match:
                json_str = json_match.group(1) or json_match.group(2)
                try:
                    json_data = json.loads(json_str)
                    # Store the structured data for later filtering
                    return {
                        "analysis": content,
                        "json_data": json_data
                    }
                except json.JSONDecodeError:
                    pass
            
            return content
        else:
            return "Error: No response received from the language model."
    except Exception as e:
        return f"Error during component formative mark analysis: {str(e)}"

def final_validation_and_assessment(conflicts_array, proposed_name, proposed_class, proposed_goods_services, step7_results, step8_results, excluded_count):
    """
    Perform Steps 9-11: Final Validation, Overall Risk Assessment, and Summary of Findings
    - Pass the excluded_count to inform GPT about pre-filtering
    """
    # Create a clearer system prompt
    system_prompt = """
    You are a trademark expert attorney specializing in trademark opinion writing.
    
    Perform Steps 9-11: Final Validation, Overall Risk Assessment, and Summary of Findings using the following structure:
    
    Step 9: Final Validation Check
    - All trademarks with unrelated goods/services have already been filtered out. No further filtering is needed.
    
    Step 10: Overall Risk Assessment
    - Integrate all findings from previous steps (Steps 1-8) to provide a single, comprehensive risk assessment.
    - Assess the trademark's overall viability and risk on this scale:
      * Low: Very few/no conflicts, highly distinctive mark
      * Low-Medium: Some minor conflicts, moderately distinctive mark
      * Medium: Several potential conflicts, average distinctiveness
      * Medium-High: Numerous conflicts, limited distinctiveness
      * High: Significant conflicts, minimal distinctiveness
    - Consider these factors:
      * Number and similarity of identical marks
      * Number and similarity of phonetically/semantically equivalent marks
      * Presence of marks with one or two-letter differences
      * Crowded field status (if applicable, reduce risk by one level)
      * Evidence of aggressive enforcement by owners of similar marks
      * Distinctiveness of the compound mark and its components
    - Provide a detailed explanation of the risk level, including specific reasons for the assessment.
    
    Step 11: Summary of Findings
    - Summarize the overall trademark analysis, including:
      * Likelihood of Conflicts
      * Crowded Field Status
      * Enforcement Landscape
      * Distinctiveness Assessment
    - Provide final strategic recommendations for registration or further steps.
    - Include a note about the number of trademarks excluded from analysis due to unrelated goods/services.
    
    YOUR RESPONSE MUST END WITH A JSON SUMMARY in this exact format:
    {
      "final_assessment": {
        "overall_risk_level": "[HIGH|MEDIUM-HIGH|MEDIUM|LOW-MEDIUM|LOW]",
        "crowded_field": [true|false],
        "identical_mark_count": [NUMBER],
        "similar_mark_count": [NUMBER],
        "key_conflicts": ["[TRADEMARK1]", "[TRADEMARK2]", ...],
        "recommendations": ["[RECOMMENDATION1]", "[RECOMMENDATION2]", ...]
      }
    }
    """
    
    client = get_azure_client()
    
    # Extract JSON data from previous steps if available
    step7_json = step7_results.get("json_data", {}) if isinstance(step7_results, dict) else {}
    step8_json = step8_results.get("json_data", {}) if isinstance(step8_results, dict) else {}
    
    # Extract analysis text
    step7_analysis = step7_results.get("analysis", step7_results) if isinstance(step7_results, dict) else step7_results
    step8_analysis = step8_results.get("analysis", step8_results) if isinstance(step8_results, dict) else step8_results
    
    # Construct a message that includes the pre-filtering information and previous results
    user_message = f"""
    Trademark Details:
    - Proposed Trademark: {proposed_name}
    - Classes Searched: {proposed_class}
    - Goods and Services: {proposed_goods_services}
    
    Previous Analysis Results:
    
    --- Step 7 Results ---
    {step7_analysis}
    
    --- Step 8 Results ---
    {step8_analysis}
    
    Please complete the trademark analysis by performing Steps 9-11: Final Validation Check, Overall Risk Assessment, and Summary of Findings.
    
    Note: {excluded_count} trademarks with unrelated goods/services were excluded from this analysis through pre-filtering.
    
    REMEMBER: End your response with the JSON summary as specified in the instructions.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0,
        )
        
        # Extract and return the response content
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            
            # Extract JSON summary for further processing
            json_match = re.search(r'```json\s*({[\s\S]*?})\s*```|({[\s\S]*?"final_assessment"\s*:[\s\S]*?})', content)
            if json_match:
                json_str = json_match.group(1) or json_match.group(2)
                try:
                    json_data = json.loads(json_str)
                    # Store the structured data for later filtering
                    return {
                        "analysis": content,
                        "json_data": json_data
                    }
                except json.JSONDecodeError:
                    pass
            
            return content
        else:
            return "Error: No response received from the language model."
    except Exception as e:
        return f"Error during final validation and assessment: {str(e)}"

def clean_and_format_opinion(comprehensive_opinion, json_data=None):
    """
    Process the comprehensive trademark opinion to:
    1. Maintain comprehensive listing of all relevant trademark hits
    2. Remove duplicated content while preserving all unique trademark references
    3. Format the opinion for better readability
    4. Ensure consistent structure with clear sections
    
    Args:
        comprehensive_opinion: Raw comprehensive opinion from previous steps
        json_data: Optional structured JSON data from previous steps
        
    Returns:
        A cleaned, formatted, and optimized trademark opinion
    """
    client = get_azure_client()
    
    system_prompt = """
    You are a trademark attorney specializing in clear, comprehensive trademark opinions.
    
    FORMAT THE TRADEMARK OPINION USING THE EXACT STRUCTURE PROVIDED BELOW:
    
    ```
REFINED TRADEMARK OPINION: [MARK NAME]
Class: [Class Number]
Goods and Services: [Goods/Services Description]
________________________________________

## BRIEF OVERVIEW
The mark "[MARK NAME]" has been analyzed for its descriptive and formative characteristics. The analysis considers distinctiveness, market positioning, and likelihood of confusion with existing marks. Overall, the mark's characteristics suggest [risk level] with [distinctiveness level].

Further details include identical mark comparisons, phonetic and semantic similarities, and component analysis.

________________________________________

## I. COMPREHENSIVE TRADEMARK HIT ANALYSIS

### A. Identical Marks
| Trademark | Status | Class | Similarity Description | Class Match | Goods & Services Match |
|------------|--------|------|------------------------|-------------|------------------------|
| [Mark 1] | [Status] | [Class] | [Similarity Description] | [True/False] | [True/False] |
| [Mark 2] | [Status] | [Class] | [Similarity Description] | [True/False] | [True/False] |

### B. Phonetically/Semantically Similar Marks
| Trademark | Status | Class | Similarity Description | Class Match | Goods & Services Match |
|------------|--------|------|------------------------|-------------|------------------------|
| [Mark 1] | [Status] | [Class] | [Similarity Description] | [True/False] | [True/False] |
| [Mark 2] | [Status] | [Class] | [Similarity Description] | [True/False] | [True/False] |

________________________________________

## II. COMPONENT ANALYSIS (FOR COMPOUND MARKS)

### Component 1: [First Component]
#### Identical Marks
| Trademark | Status | Class | Similarity Description | Class Match | Goods & Services Match |
|-----------|--------|-------|------------------------|-------------|------------------------|
| [Mark 1] | [Status] | [Class] | [Similarity Description] | [True/False] | [True/False] |

#### Phonetic and Semantic Equivalents
| Trademark | Status | Class | Similarity Description | Class Match | Goods & Services Match |
|-----------|--------|-------|------------------------|-------------|------------------------|
| [Mark 1] | [Status] | [Class] | [Similarity Description] | [True/False] | [True/False] |

### Component 2: [Second Component]
#### Identical Marks
| Trademark | Status | Class | Similarity Description | Class Match | Goods & Services Match |
|-----------|--------|-------|------------------------|-------------|------------------------|
| [Mark 1] | [Status] | [Class] | [Similarity Description] | [True/False] | [True/False] |

#### Phonetic and Semantic Equivalents
| Trademark | Status | Class | Similarity Description | Class Match | Goods & Services Match |
|-----------|--------|-------|------------------------|-------------|------------------------|
| [Mark 1] | [Status] | [Class] | [Similarity Description] | [True/False] | [True/False] |

________________________________________

## III. RISK ASSESSMENT AND SUMMARY

### Likelihood of Confusion
- [KEY POINT ABOUT LIKELIHOOD OF CONFUSION]
- [ADDITIONAL POINT ABOUT LIKELIHOOD OF CONFUSION]

### Descriptiveness
- [KEY POINT ABOUT DESCRIPTIVENESS]

### Overall Risk Level
- **[OVERALL RISK LEVEL: HIGH/MEDIUM-HIGH/MEDIUM/LOW-MEDIUM/LOW]**
- [EXPLANATION OF RISK LEVEL]

### Crowded Field Analysis
- **[CROWDED FIELD STATUS: YES/NO]**
- [EXPLANATION OF CROWDED FIELD ANALYSIS]

### Enforcement Landscape
- [KEY POINT ABOUT ENFORCEMENT LANDSCAPE]
- [ADDITIONAL POINT ABOUT ENFORCEMENT LANDSCAPE]

### Recommendations
1. [PRIMARY RECOMMENDATION]
2. [SECONDARY RECOMMENDATION]
3. [ADDITIONAL RECOMMENDATION]
________________________________________

**IMPORTANT INSTRUCTIONS:**
1. Maintain ALL unique trademark references from the original opinion.
2. Present trademarks in clear, easy-to-read tables following the format above.
3. Ensure ALL findings from the original opinion are preserved but avoid redundancy.
4. Use bullet points for key findings and numbered lists for recommendations.
5. Include trademark search exclusions in the summary section.
6. Ensure the final opinion is comprehensive yet concise.
7. For each section, include all relevant trademarks without omission.
8. Maintain the exact structure provided above with clear section headings.
9. For each mark, determine and include:
   - "Class Match" (True/False): Whether the mark's class exactly matches the proposed trademark's class.
   - "Goods & Services Match" (True/False): Whether the mark's goods/services are similar to the proposed trademark's goods/services. Use semantic similarity to determine this.
    """
    
    # Send the original opinion to be reformatted
    user_message = f"""
    Please reformat the following comprehensive trademark opinion for clarity and readability:
    
    Proposed Trademark: {json_data.get('proposed_name', 'N/A')}
    Class: {json_data.get('proposed_class', 'N/A')}
    Goods and Services: {json_data.get('proposed_goods_services', 'N/A')}
    
    Original Opinion:
    {comprehensive_opinion}
    
    Follow the exact structure provided in the instructions, ensuring all trademark references are maintained.
    
    For each mark in the tables, you must evaluate and include:
    1. Class Match (True/False): Compare the mark's class to the proposed class "{json_data.get('proposed_class', 'N/A')}" and mark True only if they exactly match.
    2. Goods & Services Match (True/False): Compare the mark's goods/services to the proposed goods/services "{json_data.get('proposed_goods_services', 'N/A')}" and mark True if they are semantically similar.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0,
        )
        
        # Extract and return the formatted opinion
        if response.choices and len(response.choices) > 0:
            formatted_opinion = response.choices[0].message.content
            
            # Filter out rows where both "Class Match" and "Goods & Services Match" are False
            filtered_opinion = []
            for line in formatted_opinion.splitlines():
                if "|" in line:  # Check if the line is part of a table
                    parts = line.split("|")
                    if len(parts) >= 6:  # Ensure the line has enough columns
                        class_match = parts[4].strip().lower() == "true"
                        goods_services_match = parts[5].strip().lower() == "true"
                        if class_match or goods_services_match:
                            filtered_opinion.append(line)
                else:
                    filtered_opinion.append(line)
            
            # Join the filtered lines back into a single string
            filtered_opinion = "\n".join(filtered_opinion)
            
            return filtered_opinion
        else:
            return "Error: No response received from the language model."
    except Exception as e:
        return f"Error during opinion formatting: {str(e)}"


def generate_trademark_opinion(conflicts_array, proposed_name, proposed_class, proposed_goods_services):
    """
    Generate a comprehensive trademark opinion by running the entire analysis process.
    
    Args:
        conflicts_array: List of potential trademark conflicts
        proposed_name: Name of the proposed trademark
        proposed_class: Class of the proposed trademark
        proposed_goods_services: Goods and services description
        
    Returns:
        A comprehensive trademark opinion
    """
    # Pre-filter trademarks to get the excluded count
    relevant_conflicts, excluded_count = validate_trademark_relevance(conflicts_array, proposed_goods_services)
    
    # Step 1-6: Initial Mark Analysis
    print("Performing Initial Mark Analysis...")
    step1_6_results = initial_mark_analysis(conflicts_array, proposed_name, proposed_class, proposed_goods_services)
    
    # Step 7: Overall Compound Mark Analysis
    print("Performing Overall Compound Mark Analysis...")
    step7_results = overall_compound_mark_analysis(conflicts_array, proposed_name, proposed_class, proposed_goods_services)
    
    # Step 8: Component (Formative) Mark Analysis
    print("Performing Component (Formative) Mark Analysis...")
    step8_results = component_formative_mark_analysis(conflicts_array, proposed_name, proposed_class, proposed_goods_services)
    
    # Steps 9-11: Final Validation, Risk Assessment, and Summary
    print("Performing Final Validation and Assessment...")
    final_results = final_validation_and_assessment(
        conflicts_array, 
        proposed_name, 
        proposed_class, 
        proposed_goods_services, 
        step7_results, 
        step8_results, 
        excluded_count
    )
    
    # Clean and format the final opinion
    print("Cleaning and formatting the final opinion...")
    opinion_data = {
        "proposed_name": proposed_name,
        "proposed_class": proposed_class,
        "proposed_goods_services": proposed_goods_services
    }
    
    # Combine all results into a comprehensive opinion
    comprehensive_opinion = f"""
    --- Step 1-6: Initial Mark Analysis ---
    {step1_6_results.get('analysis', step1_6_results) if isinstance(step1_6_results, dict) else step1_6_results}
    
    --- Step 7: Overall Compound Mark Analysis ---
    {step7_results.get('analysis', step7_results) if isinstance(step7_results, dict) else step7_results}
    
    --- Step 8: Component (Formative) Mark Analysis ---
    {step8_results.get('analysis', step8_results) if isinstance(step8_results, dict) else step8_results}
    
    --- Steps 9-11: Final Validation, Risk Assessment, and Summary ---
    {final_results.get('analysis', final_results) if isinstance(final_results, dict) else final_results}
    """
    
    formatted_opinion = clean_and_format_opinion(comprehensive_opinion, opinion_data)
    
    return formatted_opinion

# Example usage function
def run_trademark_analysis(proposed_name, proposed_class, proposed_goods_services, conflicts_data):
    """
    Run a complete trademark analysis with proper error handling.
    
    Args:
        proposed_name: Name of the proposed trademark
        proposed_class: Class of the proposed trademark
        proposed_goods_services: Goods and services of the proposed trademark
        conflicts_data: Array of potential conflict trademarks
        
    Returns:
        A comprehensive trademark opinion
    """
    try:
        # Validate input data
        if not proposed_name or not proposed_class or not proposed_goods_services:
            return "Error: Missing required trademark information."
            
        if not conflicts_data:
            return "Error: No conflict data provided for analysis."
            
        # Run the analysis
        opinion = generate_trademark_opinion(conflicts_data, proposed_name, proposed_class, proposed_goods_services)
        return opinion
        
    except Exception as e:
        return f"Error running trademark analysis: {str(e)}"

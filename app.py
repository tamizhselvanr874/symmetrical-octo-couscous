# TAMIL CODE START'S HERE-------------------------------------------------------------------------------------------------------------------------

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

Section I: Comprehensive Trademark Hit Analysis
(a) Identical Marks:
| Trademark | Owner | Goods & Services | Status | Class | Class Match | Goods & Services Match |
|------------|--------|------------------|--------|------|-------------|------------------------|
| [Mark 1] | [Owner] | [Goods/Services] | [Status] | [Class] | [True/False] | [True/False] |

(b) One Letter and Two Letter Analysis:
| Trademark | Owner | Goods & Services | Status | Class | Difference Type | Class Match | Goods & Services Match |
|------------|--------|------------------|--------|------|----------------|-------------|------------------------|
| [Mark 1] | [Owner] | [Goods/Services] | [Status] | [Class] | [One/Two Letter] | [True/False] | [True/False] |

(c) Phonetically, Semantically & Functionally Similar Analysis:
| Trademark | Owner | Goods & Services | Status | Class | Similarity Type | Class Match | Goods & Services Match |
|------------|--------|------------------|--------|------|-----------------|-------------|------------------------|
| [Mark 1] | [Owner] | [Goods/Services] | [Status] | [Class] | [Phonetic/Semantic/Functional] | [True/False] | [True/False] |

Section II: Component Analysis
(a) Component Analysis:

Component 1: [First Component]
| Trademark | Owner | Goods & Services | Status | Class | Class Match | Goods & Services Match |
|-----------|--------|------------------|--------|-------|-------------|------------------------|
| [Mark 1] | [Owner] | [Goods/Services] | [Status] | [Class] | [True/False] | [True/False] |

Component A: [Second Component]
| Trademark | Owner | Goods & Services | Status | Class | Class Match | Goods & Services Match |
|-----------|--------|------------------|--------|-------|-------------|------------------------|
| [Mark 1] | [Owner] | [Goods/Services] | [Status] | [Class] | [True/False] | [True/False] |

(b) Crowded Field Analysis:
- **Total compound mark hits found**: [NUMBER]
- **Marks with different owners**: [NUMBER] ([PERCENTAGE]%)
- **Crowded Field Status**: [YES/NO]
- **Analysis**: 
  [DETAILED EXPLANATION OF FINDINGS INCLUDING RISK IMPLICATIONS IF FIELD IS CROWDED]

Section III: Risk Assessment and Summary

Descriptiveness:
- [KEY POINT ABOUT DESCRIPTIVENESS]

Aggressive Enforcement and Litigious Behavior:
- **Known Aggressive Owners**:
  * [Owner 1]: [Enforcement patterns]
  * [Owner 2]: [Enforcement patterns]
- **Enforcement Landscape**:
  * [KEY POINT ABOUT ENFORCEMENT LANDSCAPE]
  * [ADDITIONAL POINT ABOUT ENFORCEMENT LANDSCAPE]

Risk Category for Registration:
- **[REGISTRATION RISK LEVEL: HIGH/MEDIUM-HIGH/MEDIUM/MEDIUM-LOW/LOW]**
- [EXPLANATION OF REGISTRATION RISK LEVEL WITH FOCUS ON CROWDED FIELD ANALYSIS]

Risk Category for Use:
- **[USE RISK LEVEL: HIGH/MEDIUM-HIGH/MEDIUM/MEDIUM-LOW/LOW]**
- [EXPLANATION OF USE RISK LEVEL]
    ```

    **IMPORTANT INSTRUCTIONS:**
    1. Maintain ALL unique trademark references from the original opinion.
    2. Present trademarks in clear, easy-to-read tables following the format above.
    3. Ensure ALL findings from the original opinion are preserved but avoid redundancy.
    4. Include owner names and goods/services details for each mark.
    5. Include trademark search exclusions in the summary section.
    6. Ensure the final opinion is comprehensive yet concise.
    7. For each section, include all relevant trademarks without omission.
    8. Maintain the exact structure provided above with clear section headings.
    9. For each mark, determine and include:
       - "Class Match" (True/False): Whether the mark's class exactly matches the proposed trademark's class OR is in a coordinated/related class group.
       - "Goods & Services Match" (True/False): Whether the mark's goods/services are similar to the proposed trademark's goods/services.
    10. Follow the specified structure exactly:
        - Section I focuses on overall hits, including One/Two Letter Analysis
        - Section II focuses only on component hits
        - In Section II, perform Crowded Field Analysis focusing on owner diversity
    11. State "None" when no results are found for a particular subsection
    12. Do NOT include recommendations in the summary
    13. Include aggressive enforcement analysis in Section III with details on any owners known for litigious behavior
    14. IMPORTANT: When assessing "Class Match", consider not only exact class matches but also coordinated or related classes based on the goods/services.
    15. NEVER replace full goods/services descriptions with just class numbers in the output tables. Always include the complete goods/services text.
    """
    
    # Send the original opinion to be reformatted
    user_message = f"""
    Please reformat the following comprehensive trademark opinion according to the refined structure:
    
    Proposed Trademark: {json_data.get('proposed_name', 'N/A')}
    Class: {json_data.get('proposed_class', 'N/A')}
    Goods and Services: {json_data.get('proposed_goods_services', 'N/A')}
    
    Original Opinion:
    {comprehensive_opinion}
    
    Follow the exact structure provided in the instructions, ensuring all trademark references are maintained.
    
    For each mark in the tables, you must evaluate and include:
    1. Owner name
    2. Goods & Services description - ALWAYS include the FULL goods/services text, not just class numbers
    3. Class Match (True/False): 
       - Mark True if the mark's class exactly matches the proposed class "{json_data.get('proposed_class', 'N/A')}"
       - ALSO mark True if the mark's class is in a coordinated or related class grouping with the proposed class
       - First identify all coordinated classes based on the proposed goods/services: "{json_data.get('proposed_goods_services', 'N/A')}"
       - Then mark True for any mark in those coordinated classes
    4. Goods & Services Match (True/False): Compare the mark's goods/services to the proposed goods/services "{json_data.get('proposed_goods_services', 'N/A')}" and mark True if they are semantically similar.
    
    IMPORTANT REMINDERS FOR CROWDED FIELD ANALYSIS:
    - Include exact counts and percentages for:
      * Total compound mark hits found
      * Number and percentage of marks with different owners
      * Crowded Field Status (YES if >50% have different owners)
    - Clearly explain risk implications if field is crowded
    - Section I should include ALL hits (overall hits), not just compound mark hits
    - Section II should focus ONLY on compound mark hits
    - One and Two Letter Analysis should ONLY be in Section I, not Section II
    - If no results are found for a particular subsection, state "None"
    - Do NOT include recommendations in the summary
    - Include aggressive enforcement analysis in Section III with details on any owners known for litigious behavior
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
                    if len(parts) >= 7:  # Ensure the line has enough columns
                        # Check if this is a header row by looking for specific column header text
                        if "Class Match" in line or "Trademark" in line:
                            filtered_opinion.append(line)
                        else:
                            # For data rows, check the Class Match and Goods & Services Match values
                            class_match_idx = -3  # Second to last column
                            goods_services_match_idx = -1  # Last column
                            
                            class_match = "true" in parts[class_match_idx].strip().lower()
                            goods_services_match = "true" in parts[goods_services_match_idx].strip().lower()
                            
                            if class_match or goods_services_match:
                                filtered_opinion.append(line)
                    else:
                        # Include table formatting lines and other table parts
                        filtered_opinion.append(line)
                else:
                    # Include all non-table lines
                    filtered_opinion.append(line)

            # Join the filtered lines back into a single string
            filtered_opinion = "\n".join(filtered_opinion)
            
            return filtered_opinion
        else:
            return "Error: No response received from the language model."
    except Exception as e:
        return f"Error during opinion formatting: {str(e)}"
    
def levenshtein_distance(a: str, b: str) -> int:  
    """Compute the Levenshtein distance between strings a and b."""  
    if a == b:  
        return 0  
    if len(a) == 0:  
        return len(b)  
    if len(b) == 0:  
        return len(a)  
    # Initialize DP table.  
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]  
    for i in range(len(a) + 1):  
        dp[i][0] = i  
    for j in range(len(b) + 1):  
        dp[0][j] = j  
    for i in range(1, len(a) + 1):  
        for j in range(1, len(b) + 1):  
            if a[i - 1] == b[j - 1]:  
                dp[i][j] = dp[i - 1][j - 1]  
            else:  
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])  
    return dp[len(a)][len(b)]  
  
def consistency_check(proposed_mark: str, classification: dict) -> dict:  
    """Reclassify marks based on Levenshtein distance."""  
    corrected = {  
        "identical_marks": [],  
        "one_letter_marks": [],  
        "two_letter_marks": [],  
        "similar_marks": classification.get("similar_marks", [])[:]  # Copy similar marks as is  
    }  
  
    # Process marks from the 'identical_marks' bucket.  
    for entry in classification.get("identical_marks", []):  
        candidate = entry.get("mark", "")  
        diff = levenshtein_distance(proposed_mark, candidate)  
        if diff == 0:  
            corrected["identical_marks"].append(entry)  
        elif diff == 1:  
            corrected["one_letter_marks"].append(entry)  
        elif diff == 2:  
            corrected["two_letter_marks"].append(entry)  
        else:  
            corrected["similar_marks"].append(entry)  
  
    # Process marks from the 'one_two_letter_marks' bucket.  
    for entry in classification.get("one_two_letter_marks", []):  
        candidate = entry.get("mark", "")  
        diff = levenshtein_distance(proposed_mark, candidate)  
        if diff == 0:  
            corrected["identical_marks"].append(entry)  
        elif diff == 1:  
            corrected["one_letter_marks"].append(entry)  
        elif diff == 2:  
            corrected["two_letter_marks"].append(entry)  
        else:  
            corrected["similar_marks"].append(entry)  
  
    return corrected  


def section_one_analysis(mark, class_number, goods_services, relevant_conflicts):  
    """
    Perform Section I: Comprehensive Trademark Hit Analysis using chain of thought prompting.
    This approach explicitly walks through the analysis process to ensure consistent results.
    """  
    client = get_azure_client()  
  
    system_prompt = """
You are a highly experienced trademark attorney specializing in trademark conflict analysis and opinion writing. Your task is to assess potential trademark conflicts using detailed, step-by-step chain of thought reasoning.

Follow this structure precisely:

1. STEP 1 - COORDINATED CLASS ANALYSIS:
   a) Carefully analyze the proposed goods/services: "{goods_services}"
   b) Determine which additional trademark classes are considered related or coordinated with the primary class {class_number}
   c) Provide detailed justification for each coordinated class selected
   d) Produce a finalized list of all trademark classes that should be included in the conflict assessment

2. STEP 2 - IDENTICAL MARK ANALYSIS:
   a) Identify all trademarks that are an EXACT match to the proposed mark "{mark}" (case-insensitive)
   b) For each identical mark, assess:
      - Is the mark registered in the SAME class as the proposed mark?
      - Is it registered in any of the COORDINATED classes from Step 1?
      - Are the goods/services similar, related, or overlapping with the proposed goods/services?
   c) Clearly specify `class_match` and `goods_services_match` values for each mark

3. STEP 3 - ONE LETTER DIFFERENCE ANALYSIS:
   a) Identify trademarks that differ from the proposed mark by only ONE letter
   b) Acceptable variations include one-letter substitution, addition, or deletion
   c) For each mark, specify the `class_match` and `goods_services_match` values, and document the type of variation

4. STEP 4 - TWO LETTER DIFFERENCE ANALYSIS:
   a) Identify trademarks that differ from the proposed mark by exactly TWO letters
   b) These may be substitutions, additions, deletions, or a combination thereof
   c) For each mark, specify the `class_match` and `goods_services_match` values, and document the type of variation

5. STEP 5 - SIMILAR MARK ANALYSIS:
   a) First identify trademarks that share substantial portions with the proposed mark or contain key distinctive elements of the proposed mark
   b) Then analyze these marks for similarity to the proposed mark "{mark}" in:
      - Phonetic Similarity:
        1) Analyze how the trademarks sound when spoken aloud
        2) Consider similar pronunciation patterns, rhythm, cadence, syllable stress, and overall sound impression
        3) Pay particular attention to marks that share significant sound patterns with the proposed mark
        4) Example: "FRESH BURST" would be phonetically similar to "COOL MINT FRESH STRIPS" as they share the distinctive "FRESH" element and similar explosive ending concepts ("BURST"/"STRIPS")
      - Semantic Similarity:
        1) Examine the meanings, concepts, and commercial impressions conveyed by each trademark
        2) Consider marks that convey the same or similar meaning, even if using different words
        3) Identify marks that create similar mental associations or refer to similar attributes/qualities
        4) Example: A mark like "FRESH BURST" conveys a similar concept to "COOL MINT FRESH STRIPS" as both suggest refreshing/cooling product experiences
      - Commercial Impression:
        1) Assess the overall commercial impression each mark makes on consumers
        2) Consider how consumers might remember or perceive the marks
        3) Evaluate whether the marks create similar overall commercial impressions despite differences in specific wording
        4) Example: Both "FRESH BURST" and "COOL MINT FRESH STRIPS" create the impression of breath-freshening products with an energetic sensation
   c) Important: When evaluating similarity, consider the mark as a whole but also pay attention to dominant elements that consumers are likely to remember
   d) Clearly explain your similarity reasoning for each identified mark
   e) For each mark, specify the `class_match` and `goods_services_match` values

6. STEP 6 - CROWDED FIELD ANALYSIS:
   a) Calculate the total number of potentially conflicting marks identified
       b) Calculate what percentage of these marks have different owners
       c) Determine if the field is "crowded" (>50% different owners)
       d) Explain the implications for trademark protection

FOR EACH POTENTIAL CONFLICTING MARK, INCLUDE:
- The exact mark name
- The owner's name
- A full description of goods/services
- Registration status (LIVE/DEAD)
- Class number
- Whether there is a class match (true/false)
- Whether there is a goods/services match (true/false)

FORMAT YOUR RESPONSE STRICTLY IN JSON:

{
  "identified_coordinated_classes": [LIST OF RELATED CLASS NUMBERS],
  "coordinated_classes_explanation": "[DETAILED EXPLANATION OF COORDINATED CLASSES]",
  "identical_marks": [
    {
      "mark": "[TRADEMARK NAME]",
      "owner": "[OWNER NAME]",
      "goods_services": "[FULL GOODS/SERVICES DESCRIPTION]",
      "status": "[LIVE/DEAD]",
      "class": "[CLASS NUMBER]",
      "class_match": true|false,
      "goods_services_match": true|false
    }
  ],
  "one_letter_marks": [
    {
      "mark": "[TRADEMARK NAME]",
      "owner": "[OWNER NAME]",
      "goods_services": "[FULL GOODS/SERVICES DESCRIPTION]",
      "status": "[LIVE/DEAD]",
      "class": "[CLASS NUMBER]",
      "difference_type": "One Letter",
      "class_match": true|false,
      "goods_services_match": true|false
    }
  ],
  "two_letter_marks": [
    {
      "mark": "[TRADEMARK NAME]",
      "owner": "[OWNER NAME]",
      "goods_services": "[FULL GOODS/SERVICES DESCRIPTION]",
      "status": "[LIVE/DEAD]",
      "class": "[CLASS NUMBER]",
      "difference_type": "Two Letter",
      "class_match": true|false,
      "goods_services_match": true|false
    }
  ],
  "similar_marks": [
    {
      "mark": "[TRADEMARK NAME]",
      "owner": "[OWNER NAME]",
      "goods_services": "[FULL GOODS/SERVICES DESCRIPTION]",
      "status": "[LIVE/DEAD]",
      "class": "[CLASS NUMBER]",
      "similarity_type": "[Phonetic|Semantic|Functional]",
      "class_match": true|false,
      "goods_services_match": true|false
    }
  ],
  "crowded_field": {
    "is_crowded": true|false,
    "percentage": [PERCENTAGE],
    "explanation": "[CLEAR EXPLANATION OF CROWDING AND ITS IMPLICATIONS]"
  }
}
""" 
  
    user_message = f""" 
    Proposed Trademark: {mark}
    Class: {class_number}
    Goods/Services: {goods_services}
    
    Trademark Conflicts:
    {json.dumps(relevant_conflicts, indent=2)}
    
    Analyze ONLY Section I: Comprehensive Trademark Hit Analysis. Proceed step by step with clear reasoning and structured output:
    
    STEP 1: Coordinated Class Analysis  
    - Carefully examine the proposed goods/services.  
    - Identify ALL classes that are coordinated or closely related to the primary class "{class_number}".  
    - Justify each coordinated class you identify with reasoning based on commercial relationship or consumer perception.  
    - Provide a complete list of all classes relevant to the conflict analysis.
    
    STEP 2: Identical Mark Analysis  
    - Identify all trademarks that EXACTLY match the proposed mark "{mark}" (case-insensitive).  
    - For each mark, check:  
      * Is it in the SAME class?  
      * Is it in a COORDINATED class (from Step 1)?  
      * Are the goods/services related or overlapping?  
    - Clearly state `class_match` and `goods_services_match` values for each mark.
    
    STEP 3: One Letter Difference Analysis  
    - Identify marks with only ONE letter difference (substitution, addition, or deletion).  
    - For each, determine whether there's a `class_match` and `goods_services_match`.
    
    STEP 4: Two Letter Difference Analysis  
    - Identify marks that differ by exactly TWO letters (substitution, addition, deletion, or a mix).  
    - For each, indicate `class_match` and `goods_services_match`.
    
    STEP 5: Similar Mark Analysis  
    - Identify marks similar to "{mark}" in any of the following ways:  
      * Phonetic (sounds similar)  
      * Semantic (has similar meaning)  
      * Functional (conveys similar commercial impression)  
    - Justify the type of similarity for each mark and assess `class_match` and `goods_services_match`.
    
    STEP 6: Crowded Field Analysis  
    - Count the total number of potentially conflicting marks identified.  
    - Calculate what percentage have DIFFERENT owners.  
    - Determine if the field is “crowded” (over 50% owned by different parties).  
    - Explain the trademark protection implications in a crowded field context.
    
    IMPORTANT REMINDERS:  
    - Focus on the full trademark, not just partial or component words.  
    - Always include full owner names and full goods/services descriptions.  
    - For `class_match`:  
      * Mark as True if in class "{class_number}"  
      * OR if in a coordinated class identified in Step 1  
    - For `goods_services_match`:  
      * Compare the mark’s goods/services directly to the proposed goods/services.  
    - Ensure letter difference analysis is exact (i.e., exactly one or two letters, not more).  
    - In Similar Mark Analysis, explicitly label the similarity type: Phonetic, Semantic, or Functional.
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
  
        if response.choices and len(response.choices) > 0:  
            content = response.choices[0].message.content  
  
            # Extract JSON data  
            json_match = re.search(r'```json\s*(.*?)\s*```|({[\s\S]*})', content, re.DOTALL)  
            if json_match:  
                json_str = json_match.group(1) or json_match.group(2)  
                try:  
                    raw_results = json.loads(json_str)  
                    # Apply consistency checking  
                    corrected_results = consistency_check(mark, raw_results)  
                    return corrected_results  
                except json.JSONDecodeError:  
                    return {  
                        "identified_coordinated_classes": [],
                        "coordinated_classes_explanation": "Unable to identify coordinated classes",
                        "identical_marks": [],  
                        "one_letter_marks": [],  
                        "two_letter_marks": [],  
                        "similar_marks": [],
                        "crowded_field": {
                            "is_crowded": False,
                            "percentage": 0,
                            "explanation": "Unable to determine crowded field status"
                        }
                    }  
            else:  
                return {  
                    "identified_coordinated_classes": [],
                    "coordinated_classes_explanation": "Unable to identify coordinated classes",
                    "identical_marks": [],  
                    "one_letter_marks": [],  
                    "two_letter_marks": [],  
                    "similar_marks": [],
                    "crowded_field": {
                        "is_crowded": False,
                        "percentage": 0,
                        "explanation": "Unable to determine crowded field status"
                    }
                }  
        else:  
            return {  
                "identified_coordinated_classes": [],
                "coordinated_classes_explanation": "Unable to identify coordinated classes",
                "identical_marks": [],  
                "one_letter_marks": [],  
                "two_letter_marks": [],  
                "similar_marks": [],
                "crowded_field": {
                    "is_crowded": False,
                    "percentage": 0,
                    "explanation": "Unable to determine crowded field status"
                }
            }  
    except Exception as e:  
        print(f"Error in section_one_analysis: {str(e)}")  
        return {  
            "identified_coordinated_classes": [],
            "coordinated_classes_explanation": "Error occurred during analysis",
            "identical_marks": [],  
            "one_letter_marks": [],  
            "two_letter_marks": [],  
            "similar_marks": [],
            "crowded_field": {
                "is_crowded": False,
                "percentage": 0,
                "explanation": "Error occurred during analysis"
            }
        }


def component_consistency_check(mark, results):
    """
    Verify component analysis results for consistency and correctness.
    
    Args:
        mark: The proposed trademark
        results: Raw component analysis results
        
    Returns:
        Validated and corrected component analysis results
    """
    corrected_results = results.copy()
    
    # Ensure coordinated classes exist
    if "identified_coordinated_classes" not in corrected_results:
        corrected_results["identified_coordinated_classes"] = []
    
    if "coordinated_classes_explanation" not in corrected_results:
        corrected_results["coordinated_classes_explanation"] = "No coordinated classes identified"
    
    # Check components field
    if "components" not in corrected_results:
        corrected_results["components"] = []
    
    # Validate each component and its marks
    for i, component in enumerate(corrected_results.get("components", [])):
        # Ensure component has name and marks fields
        if "component" not in component:
            component["component"] = f"Component {i+1}"
        
        if "marks" not in component:
            component["marks"] = []
        
        # Ensure component distinctiveness
        if "distinctiveness" not in component:
            # Default to descriptive if not specified
            component["distinctiveness"] = "DESCRIPTIVE"
        
        # Check each mark in the component
        for j, mark_entry in enumerate(component.get("marks", [])):
            # Ensure all required fields exist
            required_fields = ['mark', 'owner', 'goods_services', 'status', 'class', 'class_match', 'goods_services_match']
            for field in required_fields:
                if field not in mark_entry:
                    if field == 'class_match' or field == 'goods_services_match':
                        corrected_results["components"][i]["marks"][j][field] = False
                    else:
                        corrected_results["components"][i]["marks"][j][field] = "Unknown"
    
    # Validate crowded field analysis
    if "crowded_field" not in corrected_results:
        corrected_results["crowded_field"] = {
            "total_hits": 0,
            "distinct_owner_percentage": 0,
            "is_crowded": False,
            "explanation": "Unable to determine crowded field status"
        }
    else:
        # Ensure all required crowded field fields exist
        if "total_hits" not in corrected_results["crowded_field"]:
            corrected_results["crowded_field"]["total_hits"] = 0
            
        if "distinct_owner_percentage" not in corrected_results["crowded_field"]:
            corrected_results["crowded_field"]["distinct_owner_percentage"] = 0
            
        if "is_crowded" not in corrected_results["crowded_field"]:
            corrected_results["crowded_field"]["is_crowded"] = False
            
        if "explanation" not in corrected_results["crowded_field"]:
            corrected_results["crowded_field"]["explanation"] = "Unable to determine crowded field status"
    
    return corrected_results


def section_two_analysis(mark, class_number, goods_services, relevant_conflicts):  
    """Perform Section II: Component Analysis."""  
    client = get_azure_client()  
  
    system_prompt = """
You are a trademark attorney and expert in trademark opinion writing. Your task is to conduct **Section II: Component Analysis** for a proposed trademark. Please follow these structured steps and format your entire response in JSON.

🔍 COMPONENT ANALYSIS REQUIREMENTS:

(a) Break the proposed trademark into individual components (if compound).  
(b) For each component, identify relevant conflict marks that incorporate that component.  
(c) For each conflict, provide the following details:  
    - Full mark  
    - Owner name  
    - Goods/services (FULL description)  
    - Class number  
    - Registration status (LIVE or DEAD)  
    - Flags for:  
        * `class_match`: True if in the same or coordinated class  
        * `goods_services_match`: True if similar or overlapping goods/services  
(d) Evaluate the distinctiveness of each component:  
    - Use one of: `GENERIC`, `DESCRIPTIVE`, `SUGGESTIVE`, `ARBITRARY`, `FANCIFUL`

📘 COORDINATED CLASS ANALYSIS (CRITICAL):

You **must** identify not only exact class matches but also any coordinated or related classes. Use trademark practice and industry standards to determine which classes relate to the proposed goods/services. 

✅ Example coordinated class groupings (not exhaustive):  
- **Food & Beverage**: 29, 30, 31, 32, 35, 43  
- **Furniture/Home Goods**: 20, 35, 42  
- **Fashion**: 18, 25, 35  
- **Technology/Software**: 9, 38, 42  
- **Health/Beauty**: 3, 5, 44  
- **Entertainment**: 9, 41, 42

You are expected to go **beyond** this list and apply expert reasoning based on the proposed trademark’s actual goods/services. Clearly explain **why** the identified classes are relevant.

⚠️ KEY REMINDERS:
- If ANY component appears in ANY other class—even outside the exact class—it must be flagged.
- Do not overlook conflicts in **related/coordinated classes**—mark `class_match = true` for all those.
- Include full goods/services text. Avoid summarizing.

📊 CROWDED FIELD ANALYSIS:

Provide a statistical overview:
- Count the total number of relevant marks identified across components  
- Calculate the percentage owned by distinct owners  
- Determine if the field is "crowded" (typically over 50% from different owners)  
- Explain how a crowded field may reduce trademark risk

🧾 OUTPUT FORMAT (REQUIRED: JSON ONLY):

{
  "identified_coordinated_classes": [LIST OF CLASS NUMBERS],
  "coordinated_classes_explanation": "[DETAILED EXPLANATION]",
  "components": [
    {
      "component": "[COMPONENT NAME]",
      "marks": [
        {
          "mark": "[CONFLICTING TRADEMARK]",
          "owner": "[OWNER NAME]",
          "goods_services": "[FULL GOODS/SERVICES DESCRIPTION]",
          "status": "[LIVE/DEAD]",
          "class": "[CLASS NUMBER]",
          "class_match": true|false,
          "goods_services_match": true|false
        }
      ],
      "distinctiveness": "[GENERIC|DESCRIPTIVE|SUGGESTIVE|ARBITRARY|FANCIFUL]"
    }
  ],
  "crowded_field": {
    "total_hits": [NUMBER],
    "distinct_owner_percentage": [PERCENTAGE],
    "is_crowded": true|false,
    "explanation": "[EXPLAIN IMPACT OF A CROWDED FIELD ON RISK]"
  }
}
⭐ IMPORTANT: Sort all identified conflicting marks alphabetically by mark name under each component.
"""
  
  
    user_message = f"""
Proposed Trademark: {mark}
Class: {class_number}
Goods/Services: {goods_services}

Trademark Conflicts:
{json.dumps(relevant_conflicts, indent=2)}

Analyze ONLY Section II: Component Analysis.

IMPORTANT REMINDERS:

- Break the proposed trademark into components (if compound) and analyze conflicts that contain each component.
- For each conflicting mark:
  * Include the full mark, owner name, class, status (LIVE/DEAD), and FULL goods/services description.
  * Set `class_match = True` if:
      - The conflicting mark is in the same class as "{class_number}", OR
      - The conflicting mark is in a related or coordinated class based on the proposed goods/services "{goods_services}"
  * Set `goods_services_match = True` if the conflicting mark covers similar or overlapping goods/services to "{goods_services}"

- For coordinated class analysis:
  * Identify ALL classes that are related or coordinated to the proposed class.
  * Provide reasoning for why each class is coordinated, based on standard groupings and your analysis of "{goods_services}"

- Crowded Field Analysis:
  1. Show the total number of compound mark hits involving ANY component of the proposed trademark.
  2. Count how many distinct owners are represented among those marks.
  3. Calculate the percentage of marks owned by different parties.
  4. If more than 50% of the marks have different owners, set `is_crowded = true` and explain how this reduces potential risk.

- Output must be detailed, thorough, and clearly structured. Ensure that all logic is explicitly shown and justified.
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
  
        if response.choices and len(response.choices) > 0:  
            content = response.choices[0].message.content  
  
            # Extract JSON data  
            json_match = re.search(r'```json\s*(.*?)\s*```|({[\s\S]*})', content, re.DOTALL)  
            if json_match:  
                json_str = json_match.group(1) or json_match.group(2)  
                try:  
                    raw_results = json.loads(json_str)
                    # Apply consistency checking
                    corrected_results = component_consistency_check(mark, raw_results)
                    return corrected_results
                except json.JSONDecodeError:  
                    return {
                        "identified_coordinated_classes": [],
                        "coordinated_classes_explanation": "Unable to identify coordinated classes",
                        "components": [],  
                        "crowded_field": {  
                            "total_hits": 0,
                            "distinct_owner_percentage": 0,
                            "is_crowded": False,
                            "explanation": "Unable to determine crowded field status."  
                        }  
                    }  
            else:  
                return {
                    "identified_coordinated_classes": [],
                    "coordinated_classes_explanation": "Unable to identify coordinated classes",
                    "components": [],  
                    "crowded_field": {  
                        "total_hits": 0,
                        "distinct_owner_percentage": 0,
                        "is_crowded": False,
                        "explanation": "Unable to determine crowded field status."  
                    }  
                }  
        else:  
            return {
                "identified_coordinated_classes": [],
                "coordinated_classes_explanation": "Unable to identify coordinated classes",
                "components": [],  
                "crowded_field": {  
                    "total_hits": 0,
                    "distinct_owner_percentage": 0,
                    "is_crowded": False,
                    "explanation": "Unable to determine crowded field status."  
                }  
            }  
    except Exception as e:  
        print(f"Error in section_two_analysis: {str(e)}")  
        return {
            "identified_coordinated_classes": [],
            "coordinated_classes_explanation": "Error occurred during analysis",
            "components": [],  
            "crowded_field": {  
                "total_hits": 0,
                "distinct_owner_percentage": 0,
                "is_crowded": False,
                "explanation": "Error occurred during analysis"  
            }  
        }


def section_three_analysis(mark, class_number, goods_services, section_one_results, section_two_results=None):
    """
    Perform Section III: Risk Assessment and Summary
    
    Args:
        mark: The proposed trademark
        class_number: The class of the proposed trademark
        goods_services: The goods and services of the proposed trademark
        section_one_results: Results from Section I
        section_two_results: Results from Section II (may be None if Section II was skipped)
        
    Returns:
        A structured risk assessment and summary
    """
    client = get_azure_client()
    
    # Check if we should skip Section Two analysis and directly set risk to medium-high
    skip_section_two = False
    skip_reason = ""
    
    # Check for phonetic or semantic marks with class match and goods/services match
    for mark_entry in section_one_results.get("similar_marks", []):
        if mark_entry.get("similarity_type") in ["Phonetic", "Semantic"]:
            if mark_entry.get("class_match") and mark_entry.get("goods_services_match"):
                skip_section_two = True
                skip_reason = "Found a Phonetic or Semantic similar mark with both class match and goods/services match"
                break
            elif mark_entry.get("class_match"):
                skip_section_two = True
                skip_reason = "Found a Phonetic or Semantic similar mark with coordinated class match"
                break
    
    system_prompt = """
You are a trademark expert attorney specializing in trademark opinion writing.

Please analyze the results from Sections I and II to create Section III: Risk Assessment and Summary. Your analysis should address the following elements in detail:

1. Likelihood of Confusion:
   • Evaluate potential consumer confusion between the proposed trademark and any conflicting marks.
   • Take into account both exact class matches and coordinated/related class conflicts.
   • Discuss phonetic, visual, or conceptual similarities, and overlapping goods/services.

2. Descriptiveness:
   • Analyze whether the proposed trademark is descriptive in light of the goods/services and compared to existing conflicts.
   • Note whether any conflicts suggest a common industry term or generic language.

3. Aggressive Enforcement and Litigious Behavior:
   • Identify any conflicting mark owners with a history of enforcement or litigation.
   • Extract and summarize patterns such as frequent oppositions, cease-and-desist actions, or broad trademark portfolios.

4. Overall Risk Rating:
   • Provide risk ratings for Registration and Use separately:
     - For Registration: MEDIUM-HIGH when identical marks are present
     - For Use: MEDIUM-HIGH when identical marks are present
     - When no identical marks exist but similar marks are found:
       * Start with MEDIUM-HIGH risk level
       * If crowded field exists (>50% different owners), reduce risk by one level:
         - MEDIUM-HIGH → MEDIUM-LOW
         - MEDIUM → LOW (but never go below MEDIUM-LOW)
   • Justify the rating using findings from:
     - Class and goods/services overlap (including coordinated class logic)
     - Crowded field metrics (e.g., distinct owner percentage)
     - Descriptiveness and enforceability of components
     - History of enforcement activity

IMPORTANT:
- When determining likelihood of confusion, incorporate coordinated class analysis.
- Crowded field data from Section II must be factored into risk mitigation. If >50% of conflicting marks are owned by unrelated entities, that reduces enforceability and legal risk by one level.
- For identical marks, ALWAYS rate risk as MEDIUM-HIGH for Registration and MEDIUM-HIGH for Use, regardless of crowded field percentage.
- When no identical marks exist but similar marks are found in a crowded field (>50% different owners), reduce risk by one level.
- Do NOT increase risk to HIGH even when identical marks are present.
- Do NOT reduce risk level below MEDIUM-LOW.

Your output MUST be returned in the following JSON format:

{
  "likelihood_of_confusion": [
    "[KEY POINT ABOUT LIKELIHOOD OF CONFUSION]",
    "[ADDITIONAL POINT ABOUT LIKELIHOOD OF CONFUSION]"
  ],
  "descriptiveness": [
    "[KEY POINT ABOUT DESCRIPTIVENESS]"
  ],
  "aggressive_enforcement": {
    "owners": [
      {
        "name": "[OWNER NAME]",
        "enforcement_patterns": [
          "[PATTERN 1]",
          "[PATTERN 2]"
        ]
      }
    ],
    "enforcement_landscape": [
      "[KEY POINT ABOUT ENFORCEMENT LANDSCAPE]",
      "[ADDITIONAL POINT ABOUT ENFORCEMENT LANDSCAPE]"
    ]
  },
  "overall_risk": {
    "level_registration": "MEDIUM-HIGH",
    "explanation_registration": "[EXPLANATION OF RISK LEVEL WITH FOCUS ON IDENTICAL MARKS]",
    "level_use": "MEDIUM-HIGH",
    "explanation_use": "[EXPLANATION OF RISK LEVEL]",
    "crowded_field_percentage": [PERCENTAGE],
    "crowded_field_impact": "[EXPLANATION OF HOW CROWDED FIELD AFFECTED RISK LEVEL]"
  }
}
"""
    
    # Prepare the user message based on whether Section II was skipped
    if skip_section_two:
        user_message = f"""
Proposed Trademark: {mark}
Class: {class_number}
Goods and Services: {goods_services}

Section I Results:
{json.dumps(section_one_results, indent=2)}

SPECIAL INSTRUCTION: Section II analysis was skipped because: {skip_reason}. According to our risk assessment rules, when a Phonetic or Semantic mark is identified with a class match (and either goods/services match or coordinated class match), the risk level is automatically set to MEDIUM-HIGH for both Registration and Use.

Create Section III: Risk Assessment and Summary.

IMPORTANT REMINDERS:
- SET the risk level to MEDIUM-HIGH for both Registration and Use
- Include an explanation that this risk level is due to the presence of a Phonetic or Semantic similar mark with class match
- Focus the risk discussion on the similar marks identified in Section I
- For aggressive enforcement analysis, examine the owners of similar marks
- Specifically analyze coordinated class conflicts
"""
    else:
        user_message = f"""
Proposed Trademark: {mark}
Class: {class_number}
Goods and Services: {goods_services}

Section I Results:
{json.dumps(section_one_results, indent=2)}

Section II Results:
{json.dumps(section_two_results, indent=2)}

Create Section III: Risk Assessment and Summary.

IMPORTANT REMINDERS:
- Focus the risk discussion on crowded field analysis and identical marks
- Include the percentage of overlapping marks from crowded field analysis
- For identical marks specifically, ALWAYS set risk level to:
  * MEDIUM-HIGH for Registration
  * MEDIUM-HIGH for Use
- When no identical marks exist but similar marks are found:
  * Start with MEDIUM-HIGH risk level
  * If crowded field exists (>50% different owners), reduce risk by one level:
    - MEDIUM-HIGH → MEDIUM-LOW
    - MEDIUM → LOW (but never go below MEDIUM-LOW)
- Never increase risk to HIGH even with identical marks present
- For aggressive enforcement analysis, examine the owners of similar marks
- Specifically analyze coordinated class conflicts
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
        
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            
            # Extract JSON data
            json_match = re.search(r'```json\s*(.*?)\s*```|({[\s\S]*})', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1) or json_match.group(2)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    return {
                        "likelihood_of_confusion": ["Unable to determine likelihood of confusion."],
                        "descriptiveness": ["Unable to determine descriptiveness."],
                        "aggressive_enforcement": {
                            "owners": [],
                            "enforcement_landscape": ["Unable to determine enforcement patterns."]
                        },
                        "overall_risk": {
                            "level_registration": "MEDIUM-HIGH" if skip_section_two else "MEDIUM-LOW",
                            "explanation_registration": f"Risk level set to MEDIUM-HIGH due to {skip_reason}" if skip_section_two else "Unable to determine precise risk level.",
                            "level_use": "MEDIUM-HIGH" if skip_section_two else "MEDIUM-LOW",
                            "explanation_use": f"Risk level set to MEDIUM-HIGH due to {skip_reason}" if skip_section_two else "Unable to determine precise risk level.",
                            "crowded_field_percentage": 0,
                            "crowded_field_impact": "Section II analysis was skipped due to high-risk marks in Section I" if skip_section_two else "Unable to determine crowded field impact"
                        }
                    }
            else:
                return {
                    "likelihood_of_confusion": ["Unable to determine likelihood of confusion."],
                    "descriptiveness": ["Unable to determine descriptiveness."],
                    "aggressive_enforcement": {
                        "owners": [],
                        "enforcement_landscape": ["Unable to determine enforcement patterns."]
                    },
                    "overall_risk": {
                        "level_registration": "MEDIUM-HIGH" if skip_section_two else "MEDIUM-LOW",
                        "explanation_registration": f"Risk level set to MEDIUM-HIGH due to {skip_reason}" if skip_section_two else "Unable to determine precise risk level.",
                        "level_use": "MEDIUM-HIGH" if skip_section_two else "MEDIUM-LOW",
                        "explanation_use": f"Risk level set to MEDIUM-HIGH due to {skip_reason}" if skip_section_two else "Unable to determine precise risk level.",
                        "crowded_field_percentage": 0,
                        "crowded_field_impact": "Section II analysis was skipped due to high-risk marks in Section I" if skip_section_two else "Unable to determine crowded field impact"
                    }
                }
        else:
            return {
                "likelihood_of_confusion": ["Unable to determine likelihood of confusion."],
                "descriptiveness": ["Unable to determine descriptiveness."],
                "aggressive_enforcement": {
                    "owners": [],
                    "enforcement_landscape": ["Unable to determine enforcement patterns."]
                },
                "overall_risk": {
                    "level_registration": "MEDIUM-HIGH" if skip_section_two else "MEDIUM-LOW",
                    "explanation_registration": f"Risk level set to MEDIUM-HIGH due to {skip_reason}" if skip_section_two else "Unable to determine precise risk level.",
                    "level_use": "MEDIUM-HIGH" if skip_section_two else "MEDIUM-LOW",
                    "explanation_use": f"Risk level set to MEDIUM-HIGH due to {skip_reason}" if skip_section_two else "Unable to determine precise risk level.",
                    "crowded_field_percentage": 0,
                    "crowded_field_impact": "Section II analysis was skipped due to high-risk marks in Section I" if skip_section_two else "Unable to determine crowded field impact"
                }
            }
    except Exception as e:
        print(f"Error in section_three_analysis: {str(e)}")
        return {
            "likelihood_of_confusion": ["Unable to determine likelihood of confusion."],
            "descriptiveness": ["Unable to determine descriptiveness."],
            "aggressive_enforcement": {
                "owners": [],
                "enforcement_landscape": ["Unable to determine enforcement patterns."]
            },
            "overall_risk": {
                "level_registration": "MEDIUM-HIGH" if skip_section_two else "MEDIUM-LOW",
                "explanation_registration": f"Risk level set to MEDIUM-HIGH due to {skip_reason}" if skip_section_two else "Unable to determine precise risk level.",
                "level_use": "MEDIUM-HIGH" if skip_section_two else "MEDIUM-LOW",
                "explanation_use": f"Risk level set to MEDIUM-HIGH due to {skip_reason}" if skip_section_two else "Unable to determine precise risk level.",
                "crowded_field_percentage": 0,
                "crowded_field_impact": "Section II analysis was skipped due to high-risk marks in Section I" if skip_section_two else "Unable to determine crowded field impact"
            }
        }

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
    
    print("Performing Section I: Comprehensive Trademark Hit Analysis...")
    section_one_results = section_one_analysis(proposed_name, proposed_class, proposed_goods_services, relevant_conflicts)
    
    print("Performing Section II: Component Analysis...")
    section_two_results = section_two_analysis(proposed_name, proposed_class, proposed_goods_services, relevant_conflicts)
    
    print("Performing Section III: Risk Assessment and Summary...")
    section_three_results = section_three_analysis(proposed_name, proposed_class, proposed_goods_services, section_one_results, section_two_results)
    
    # Create a comprehensive opinion structure
    opinion_structure = {
        "proposed_name": proposed_name,
        "proposed_class": proposed_class,
        "proposed_goods_services": proposed_goods_services,
        "excluded_count": excluded_count,
        "section_one": section_one_results,
        "section_two": section_two_results,
        "section_three": section_three_results
    }
    
    # Format the opinion in a structured way
    comprehensive_opinion = f"""
    REFINED TRADEMARK OPINION: {proposed_name}
    Class: {proposed_class}
    Goods and Services: {proposed_goods_services}

    Section I: Comprehensive Trademark Hit Analysis
    
    (a) Identical Marks:
    {json.dumps(section_one_results.get('identical_marks', []), indent=2)}
    
    (b) One Letter and Two Letter Analysis:
    {json.dumps({
        'one_letter_marks': section_one_results.get('one_letter_marks', []),
        'two_letter_marks': section_one_results.get('two_letter_marks', [])
    }, indent=2)}
    
    (c) Phonetically, Semantically & Functionally Similar Analysis:
    {json.dumps(section_one_results.get('similar_marks', []), indent=2)}
    
    (d) Crowded Field Analysis:
    {json.dumps(section_one_results.get('crowded_field', {}), indent=2)}

    Section II: Component Analysis
    
    (a) Component Analysis:
    {json.dumps(section_two_results.get('components', []), indent=2)}
    
    (b) Crowded Field Analysis:
    {json.dumps(section_two_results.get('crowded_field', {}), indent=2)}

    Section III: Risk Assessment and Summary
    
    Likelihood of Confusion:
    {json.dumps(section_three_results.get('likelihood_of_confusion', []), indent=2)}
    
    Descriptiveness:
    {json.dumps(section_three_results.get('descriptiveness', []), indent=2)}
    
    Overall Risk Level:
    {json.dumps(section_three_results.get('overall_risk', {}), indent=2)}
    
    Note: {excluded_count} trademarks with unrelated goods/services were excluded from this analysis.
    """
    
    # Clean and format the final opinion
    print("Cleaning and formatting the final opinion...")
    formatted_opinion = clean_and_format_opinion(comprehensive_opinion, opinion_structure)
    
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
        if not proposed_name or not proposed_class or not proposed_goods_services:
            return "Error: Missing required trademark information."
            
        if not conflicts_data:
            return "Error: No conflict data provided for analysis."
            
        opinion = generate_trademark_opinion(conflicts_data, proposed_name, proposed_class, proposed_goods_services)
        return opinion
        
    except Exception as e:
        return f"Error running trademark analysis: {str(e)}"

# TAMIL CODE END'S HERE ---------------------------------------------------------------------------------------------------------------------------

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def export_trademark_opinion_to_word(trademark_output, web_common_law_output=None):
    """
    Export trademark opinion to Word document (updated to optionally handle web common law opinion)
    Maintains all original functionality while adding web common law support
    """
    document = Document()
    
    # Add main title
    title = document.add_heading('Trademark Analysis Report', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Process trademark opinion (original functionality)
    document.add_heading('Trademark Office Opinion', level=1)
    process_opinion_content(document, trademark_output)
    
    # Conditionally add web common law opinion if provided
    if web_common_law_output:
        document.add_heading('Web Common Law Opinion', level=1)
        process_opinion_content(document, web_common_law_output)
    
    # Save the document
    filename = "Trademark_Opinion.docx" if not web_common_law_output else "Combined_Trademark_Opinion.docx"
    document.save(filename)
    return filename

def process_opinion_content(document, content):
    """
    Helper function to process opinion content (trademark or web common law)
    Maintains original table handling logic while improving formatting
    """
    lines = content.split('\n')
    current_table = None
    
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
            
        # Handle section headers
        if line.startswith(('Section', 'WEB COMMON LAW OPINION')):
            document.add_heading(line, level=2)
            continue
            
        # Original table handling logic (preserved exactly)
        if '|' in line and '---' not in line:
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            
            if current_table is None:
                current_table = document.add_table(rows=1, cols=len(cells))
                current_table.style = 'Table Grid'
                hdr_cells = current_table.rows[0].cells
                for i, cell in enumerate(cells):
                    hdr_cells[i].text = cell
            else:
                row_cells = current_table.add_row().cells
                for i, cell in enumerate(cells):
                    row_cells[i].text = cell
        else:
            current_table = None
            p = document.add_paragraph(line)
            
            # Enhanced formatting for risk assessment
            if any(keyword in line for keyword in ['Risk Category', 'Overall Risk']):
                p.runs[0].bold = True
                p.runs[0].font.size = Pt(12)

# ------- 

from typing import List  
import fitz  # PyMuPDF  
from PIL import Image  
import io  
  
  
def Web_CommonLaw_Overview_List(document: str, start_page: int, pdf_document: fitz.Document) -> List[int]:  
    """  
    Extract the page numbers for the 'Web Common Law Overview List' section.  
    """  
    pages_with_overview = []  
    for i in range(start_page, min(start_page + 2, pdf_document.page_count)):  
        page = pdf_document.load_page(i)  
        page_text = page.get_text()  
        if "Record Nr." in page_text:  # Check for "Record Nr." in the text  
            pages_with_overview.append(i + 1)  # Use 1-based indexing for page numbers  
    return pages_with_overview  
  
  
def convert_pages_to_pil_images(pdf_document: fitz.Document, page_numbers: List[int]) -> List[Image.Image]:  
    """  
    Convert the specified pages of the PDF to PIL images and return them as a list of PIL Image objects.  
    """  
    images = []  
    for page_num in page_numbers:  
        page = pdf_document.load_page(page_num - 1)  # Convert 1-based index to 0-based  
        pix = page.get_pixmap()  # Render the page to a pixmap  
        img = Image.open(io.BytesIO(pix.tobytes("png")))  # Convert pixmap to PIL Image  
        images.append(img)  # Add the PIL Image object to the list  
    return images  
  
  
def web_law_page(document_path: str) -> List[Image.Image]:  
    """  
    Return PIL Image objects of the pages where either:  
    1. "Web Common Law Summary Page:" appears, or  
    2. Both "Web Common Law Overview List" and "Record Nr." appear.  
    """  
    matching_pages = []  # List to store matching page numbers  
  
    with fitz.open(document_path) as pdf_document:  
        for page_num in range(pdf_document.page_count):  
            page = pdf_document.load_page(page_num)  
            page_text = page.get_text()  
            print(page_text)  
              
            # Check for "Web Common Law Summary Page:"  
            if "Web Common Law Page:" in page_text:  
                matching_pages.append(page_num + 1)  
  
  
            # Check for "Web Common Law Overview List" and "Record Nr."  
            if "WCL-" in page_text:  
                matching_pages.append(page_num + 1)  
            # if "Web Common Law Overview List" in page_text and "Record Nr." in page_text:  
            #     overview_pages = Web_CommonLaw_Overview_List(  
            #         page_text, page_num, pdf_document  
            #     )  
            #     matching_pages.extend(overview_pages)  
  
  
        # Remove duplicates and sort the page numbers  
        matching_pages = sorted(set(matching_pages))  
  
        # Convert matching pages to PIL images  
        images = convert_pages_to_pil_images(pdf_document, matching_pages)  
  
    return images  
                
# ---- extraction logic

import io  
import base64  
import cv2  
import json  
import requests  
import os
from PIL import Image  
from typing import List  
import numpy as np
  
# Function to encode images using OpenCV  
def encode_image(image: Image.Image) -> str:  
    """  
    Encode a PIL Image as Base64 string using OpenCV.  
    """  
    # Convert PIL Image to numpy array for OpenCV  
    image_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)  
    buffered = cv2.imencode(".jpg", image_np)[1]  
    return base64.b64encode(buffered).decode("utf-8")  
  
  
# Function to process a single image and get the response from LLM  
def process_single_image(image: Image.Image, proposed_name: str) -> dict:  
    """  
    Process a single image by sending it to Azure OpenAI API.  
    Cited term: Check for {proposed_name} in the image.
    """        
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    model="gpt-4o"  

    # Encode the image into Base64 using OpenCV  
    base64_image = encode_image(image)  
  
    # Prepare the prompt for the LLM  
    prompt = f"""Extract the following details from the given image: Cited term, Owner name, Goods & services.\n\n
    
                Cited Term:\n
                - This is the snippet in the product/site text that *fully or partially matches* the physically highlighted or searched trademark name: {proposed_name}.
                - You must prioritize any match that closely resembles '{proposed_name}' — e.g., 'ColorGrip', 'COLORGRIP', 'Color self Grip' , 'Grip Colour', 'color-grip', 'Grip' , or minor variations in spacing/punctuation.

                Owner Name (Brand):\n
                - Identify the name of the individual or entity that owns or manufactures the product.
                - Look for indicators like "Owner:," "Brand:," "by:," or "Manufacturer:."
                - If none are found, return "Not specified."
                
                Goods & Services:\n
                - Extract the core goods and services associated with the trademark or product.  
                - Provide relevant detail (e.g., "permanent hair color," "nail care polish," "hair accessories," or "hair styling tools").
    
                Return output only in the exact below-mentioned format:  
                Example output format:  
                    Cited_term: ColourGrip,\n  
                    Owner_name: Matrix, \n 
                    Goods_&_services: Hair color products,\n    
"""
  
    # Prepare the API payload  
    data = {  
        "model": model,  
        "messages": [  
            {  
                "role": "system",  
                "content": "You are a helpful assistant for extracting Meta Data based on the given Images [Note: Only return the required extracted data in the exact format mentioned].",  
            },  
            {  
                "role": "user",  
                "content": [  
                    {"type": "text", "text": prompt},  
                    {  
                        "type": "image_url",  
                        "image_url": {  
                            "url": f"data:image/png;base64,{base64_image}"  
                        },  
                    },  
                ],  
            },  
        ],  
        "max_tokens": 200,  
        "temperature": 0,  
    }  
  
    # Send the API request  
    headers = {"Content-Type": "application/json", "api-key": api_key}  
    response = requests.post(  
        f"{azure_endpoint}/openai/deployments/{model}/chat/completions?api-version=2024-10-01-preview",  
        headers=headers,  
        data=json.dumps(data),  
    )  
  
    # Parse the response  
    if response.status_code == 200:  
        extracted_data = response.json()["choices"][0]["message"]["content"]  
    else:  
        extracted_data = "Failed to extract data"    
    # Return the extracted data  
    return {extracted_data.strip()}  
  
  
# Function to process all images one by one  
def extract_web_common_law(page_images: List[Image.Image], proposed_name: str) -> List[dict]:  
    """  
    Send images one by one to Azure OpenAI GPT models,  
    and collect the responses into a single array.  
    """    
    # Process each image and collect the results  
    results = []  
    for idx, image in enumerate(page_images):  
        result = process_single_image(image, proposed_name)  
        results.append(result)  
  
    # Return the collected results as a single array  
    return results  

def analyze_web_common_law(extracted_data: List[str], proposed_name: str) -> str:
    """
    Comprehensive analysis of web common law trademark data through three specialized stages.
    Returns a professional opinion formatted according to legal standards.
    """
    # Stage 1: Cited Term Analysis
    cited_term_analysis = section_four_analysis(extracted_data, proposed_name)
    
    # Stage 2: Component Analysis
    component_analysis = section_five_analysis(extracted_data, proposed_name)
    
    # Stage 3: Final Risk Assessment
    risk_assessment = section_six_analysis(cited_term_analysis, component_analysis, proposed_name)
    
    # Combine all sections into final report
    final_report = f"""
WEB COMMON LAW OPINION: {proposed_name} 

{cited_term_analysis}

{component_analysis}

{risk_assessment}
"""
    return final_report

def section_four_analysis(extracted_data: List[str], proposed_name: str) -> str:
    """
    Perform Section IV: Comprehensive Cited Term Analysis
    """
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    model = "gpt-4o"

    extracted_text = "\n".join([str(item) for item in extracted_data])
    
    prompt = f"""You are a trademark attorney analyzing web common law trademark data.
Perform Section IV analysis (Comprehensive Cited Term Analysis) with these subsections:

1. Identical Cited Terms
2. One Letter and Two Letter Differences
3. Phonetically/Semantically/Functionally Similar Terms

Analyze this web common law data against proposed trademark: {proposed_name}

Extracted Data:
{extracted_text}

Perform comprehensive analysis:
1. Check for identical cited terms
2. Analyze one/two letter differences
3. Identify similar terms (phonetic/semantic/functional)
4. For each, determine if goods/services are similar

Return results in EXACTLY this format:

Section IV: Comprehensive Cited Term Analysis
(a) Identical Cited Terms:
| Cited Term | Owner | Goods & Services | Goods & Services Match |
| [Term 1] | [Owner] | [Goods/Services] | [True/False] |

(b) One Letter and Two Letter Analysis:
| Cited Term | Owner | Goods & Services | Difference Type | Goods & Services Match |
| [Term 1] | [Owner] | [Goods/Services] | [One/Two Letter] | [True/False] |

(c) Phonetically, Semantically & Functionally Similar Analysis:
| Cited Term | Owner | Goods & Services | Similarity Type | Goods & Services Match |
| [Term 1] | [Owner] | [Goods/Services] | [Phonetic/Semantic/Functional] | [True/False] |

Evaluation Guidelines:
- Goods/services match if they overlap with proposed trademark's intended use
- One letter difference = exactly one character changed/added/removed
- Two letter difference = exactly two characters changed/added/removed
- Phonetic similarity = sounds similar when spoken
- Semantic similarity = similar meaning
- Functional similarity = similar purpose/use
- State "None" when no results are found
- Filter out rows where both match criteria are False
- Always include complete goods/services text
"""

    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a trademark attorney specializing in comprehensive trademark analysis. Provide precise, professional analysis in the exact requested format.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "max_tokens": 2000,
        "temperature": 0.1,
    }

    headers = {"Content-Type": "application/json", "api-key": api_key}
    response = requests.post(
        f"{azure_endpoint}/openai/deployments/{model}/chat/completions?api-version=2024-10-01-preview",
        headers=headers,
        data=json.dumps(data),
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    return "Failed to generate cited term analysis"

def section_five_analysis(extracted_data: List[str], proposed_name: str) -> str:
    """
    Perform Section V: Component Analysis and Crowded Field Assessment
    (Skips entire section if identical hits exist in cited term analysis)
    """
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    model = "gpt-4o"

    extracted_text = "\n".join([str(item) for item in extracted_data])
    
    prompt = f"""You are a trademark attorney analyzing web common law components.
First check if there are any identical cited terms to '{proposed_name}' in this data:

Extracted Data:
{extracted_text}

IF IDENTICAL TERMS EXIST:
- Skip entire Section V analysis
- Return this exact text:
  "Section V omitted due to identical cited terms"

IF NO IDENTICAL TERMS EXIST:
Perform Section V analysis (Component Analysis) with these subsections:
1. Component Breakdown
2. Crowded Field Analysis

Return results in EXACTLY this format:

Section V: Component Analysis
(a) Component Analysis:

Component 1: [First Component]
| Cited Term | Owner | Goods & Services | Goods & Services Match |
| [Term 1] | [Owner] | [Goods/Services] | [True/False] |

(b) Crowded Field Analysis:
- **Total component hits found**: [NUMBER]
- **Terms with different owners**: [NUMBER] ([PERCENTAGE]%)
- **Crowded Field Status**: [YES/NO]
- **Analysis**: 
  [DETAILED EXPLANATION OF FINDINGS]

IMPORTANT:
1. First check for identical terms before any analysis
2. If identical terms exist, skip entire Section V
3. Only perform component and crowded field analysis if NO identical terms exist
4. Never show any analysis if identical terms are found
"""

    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a trademark attorney who FIRST checks for identical terms before deciding whether to perform any Section V analysis.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "max_tokens": 2000,
        "temperature": 0.1,  # Low temperature for strict rule following
    }

    headers = {"Content-Type": "application/json", "api-key": api_key}
    response = requests.post(
        f"{azure_endpoint}/openai/deployments/{model}/chat/completions?api-version=2024-10-01-preview",
        headers=headers,
        data=json.dumps(data),
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    return "Failed to generate component analysis"

def section_six_analysis(cited_term_analysis: str, component_analysis: str, proposed_name: str) -> str:
    """
    Perform Section VI: Final Risk Assessment with strict rules:
    - Skip crowded field analysis if identical hits exist
    - Risk levels only MEDIUM-HIGH or MEDIUM-LOW
    """
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    model = "gpt-4o"

    prompt = f"""You are a senior trademark attorney preparing a final risk assessment for {proposed_name}.

**STRICT RULES TO FOLLOW:**
1. **Identical Hits Take Precedence**:
   - If ANY identical cited terms exist in Section IV(a), IMMEDIATELY set risk to MEDIUM-HIGH
   - SKIP ENTIRELY any crowded field analysis in this case
   - Include note: "Crowded field analysis omitted due to identical cited terms"

2. **Crowded Field Analysis ONLY When**:
   - NO identical cited terms exist
   - Then analyze crowded field from Section V(b)
   - If crowded field exists (>50% different owners), set risk to MEDIUM-LOW

3. **Risk Level Restrictions**:
   - Maximum risk: MEDIUM-HIGH (never HIGH)
   - Minimum risk: MEDIUM-LOW (never LOW)
   - Only these two possible outcomes

**Analysis Sections:**
Cited Term Analysis:
{cited_term_analysis}

Component Analysis:
{component_analysis}

**Required Output Format:**

Section VI: Web Common Law Risk Assessment

Market Presence:
- [Brief market overview based on findings]

Enforcement Patterns:
- [List any concerning enforcement patterns if found]

Risk Category for Use:
- **[MEDIUM-HIGH or MEDIUM-LOW]**
- [Clear justification based on strict rules above]

III. COMBINED RISK ASSESSMENT

Overall Risk Category:
- **[MEDIUM-HIGH or MEDIUM-LOW]**
- [Detailed explanation following these guidelines:
   - If identical terms: "Identical cited term(s) found, elevating risk to MEDIUM-HIGH. Crowded field analysis not performed."
   - If crowded field: "No identical terms found. Crowded field (X% different owners) reduces risk to MEDIUM-LOW."
   - If neither: "No identical terms and no crowded field, maintaining MEDIUM-LOW risk."]

**Critical Instructions:**
1. NEVER show crowded field analysis if identical terms exist
2. ALWAYS use specified risk level terminology
3. Keep explanations concise but legally precise
4. Maintain strict adherence to the rules above
"""

    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a trademark risk assessment expert who STRICTLY follows rules about identical hits and crowded fields. Never deviate from the specified risk levels.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "max_tokens": 1500,
        "temperature": 0.1,  # Low temperature for consistent rule-following
    }

    headers = {"Content-Type": "application/json", "api-key": api_key}
    response = requests.post(
        f"{azure_endpoint}/openai/deployments/{model}/chat/completions?api-version=2024-10-01-preview",
        headers=headers,
        data=json.dumps(data),
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    return "Failed to generate risk assessment"

# -------------------

# Streamlit App
st.title("Trademark Document Parser Version 6.9")

# File upload
uploaded_files = st.sidebar.file_uploader(
    "Choose PDF files", type="pdf", accept_multiple_files=True
)

if uploaded_files:
    if st.sidebar.button("Check Conflicts", key="check_conflicts"):
        total_files = len(uploaded_files)
        progress_bar = st.progress(0)
        # progress_label.text(f"Progress: 0%")  --- Needed to set

        for i, uploaded_file in enumerate(uploaded_files):
            # Save uploaded file to a temporary file path
            temp_file_path = f"temp_{uploaded_file.name}"
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.read())

            start_time = time.time()

            sp = True
            proposed_trademark_details = extract_proposed_trademark_details(
                temp_file_path
            )

            if proposed_trademark_details:
                proposed_name = proposed_trademark_details.get(
                    "proposed_trademark_name", "N"
                )
                proposed_class = proposed_trademark_details.get(
                    "proposed_nice_classes_number"
                )
                proposed_goods_services = proposed_trademark_details.get(
                    "proposed_goods_services", "N"
                )
                if proposed_goods_services != "N":
                    with st.expander(
                        f"Proposed Trademark Details for {uploaded_file.name}"
                    ):
                        st.write(f"Proposed Trademark name: {proposed_name}")
                        st.write(f"Proposed class-number: {proposed_class}")
                        st.write(
                            f"Proposed Goods & Services: {proposed_goods_services}"
                        )
                    class_list = list_conversion(proposed_class)
                else:
                    st.write(
                        "______________________________________________________________________________________________________________________________"
                    )
                    st.write(
                        f"Sorry, unable to generate report due to insufficient information about goods & services in the original trademark report : {uploaded_file.name}"
                    )
                    st.write(
                        "______________________________________________________________________________________________________________________________"
                    )
                    sp = False
            else:

                proposed_trademark_details = extract_proposed_trademark_details2(
                    temp_file_path
                )

                if proposed_trademark_details:
                    proposed_name = proposed_trademark_details.get(
                        "proposed_trademark_name", "N"
                    )
                    proposed_class = proposed_trademark_details.get(
                        "proposed_nice_classes_number"
                    )
                    proposed_goods_services = proposed_trademark_details.get(
                        "proposed_goods_services", "N"
                    )
                    if proposed_goods_services != "N":
                        with st.expander(
                            f"Proposed Trademark Details for {uploaded_file.name}"
                        ):
                            st.write(f"Proposed Trademark name: {proposed_name}")
                            st.write(f"Proposed class-number: {proposed_class}")
                            st.write(
                                f"Proposed Goods & Services: {proposed_goods_services}"
                            )
                        class_list = list_conversion(proposed_class)
                    else:
                        st.write(
                            "______________________________________________________________________________________________________________________________"
                        )
                        st.write(
                            f"Sorry, unable to generate report due to insufficient information about goods & services in the original trademark report : {uploaded_file.name}"
                        )
                        st.write(
                            "______________________________________________________________________________________________________________________________"
                        )
                        sp = False
                else:
                    st.error(
                        f"Unable to extract Proposed Trademark Details for {uploaded_file.name}"
                    )
                    sp = False
                    continue

            if sp:
                progress_bar.progress(25)
                # Initialize AzureChatOpenAI

                # s_time = time.time()

                existing_trademarks = parse_trademark_details(temp_file_path)
                st.write(len(existing_trademarks))
                # for i in range(25,46):
                #     progress_bar.progress(i)


# PRAVEEN WEB COMMON LAW CODE START'S HERE-------------------------------------------------------------------------------------------------------------------------

                # Updated usage in your Streamlit code would look like:
                # !!! Function used extract the web common law pages into images
                full_web_common_law = web_law_page(temp_file_path)                

                progress_bar.progress(50)
                st.success(
                    f"Existing Trademarks Data Extracted Successfully for {uploaded_file.name}!"
                )

                # !!! Function used extract the web common law details from the images using LLM 
                extracted_web_law = extract_web_common_law(full_web_common_law, proposed_name)  

                # New comprehensive analysis
                analysis_result = analyze_web_common_law(extracted_web_law, proposed_name)

                # Display results
                with st.expander("Extracted Web Common Law Data"):
                    st.write(extracted_web_law)

                with st.expander("Trademark Legal Analysis"):
                    st.markdown(analysis_result)  # Using markdown for better formatting

                # extracted_web_law ----- Web common law stored in this variable 

# PRAVEEN WEB COMMON LAW CODE END'S HERE-------------------------------------------------------------------------------------------------------------------------


                # e_time = time.time()
                # elap_time = e_time - s_time
                # elap_time = elap_time // 60
                # st.write(f"Time taken for extraction: {elap_time} mins")

                # e_time = time.time()
                # elap_time = e_time - s_time
                # st.write(f"Time taken: {elap_time} seconds")

                # Display extracted details

                nfiltered_list = []
                unsame_class_list = []

                # Iterate over each JSON element in trademark_name_list
                for json_element in existing_trademarks:
                    class_numbers = json_element["international_class_number"]
                    # Check if any of the class numbers are in class_list
                    if any(number in class_list for number in class_numbers):
                        nfiltered_list.append(json_element)
                    else:
                        unsame_class_list.append(json_element)

                existing_trademarks = nfiltered_list
                existing_trademarks_unsame = unsame_class_list

                high_conflicts = []
                moderate_conflicts = []
                low_conflicts = []
                Name_Matchs = []
                no_conflicts = []

                lt = len(existing_trademarks)

                for existing_trademark in existing_trademarks:
                    conflict = compare_trademarks(
                        existing_trademark,
                        proposed_name,
                        proposed_class,
                        proposed_goods_services,
                    )
                    if conflict is not None:
                        if conflict["conflict_grade"] == "High":
                            high_conflicts.append(conflict)
                        elif conflict["conflict_grade"] == "Moderate":
                            moderate_conflicts.append(conflict)
                        elif conflict["conflict_grade"] == "Low":
                            low_conflicts.append(conflict)
                        else:
                            no_conflicts.append(conflict)

                for existing_trademarks in existing_trademarks_unsame:
                    if existing_trademarks["international_class_number"] != []:
                        conflict = assess_conflict(
                            existing_trademarks,
                            proposed_name,
                            proposed_class,
                            proposed_goods_services,
                        )

                        if conflict["conflict_grade"] == "Name-Match":
                            # conflict_validation = compare_trademarks2(existing_trademarks, proposed_name, proposed_class, proposed_goods_services)
                            # if conflict_validation == "Name-Match":
                            Name_Matchs.append(conflict)
                        else:
                            print("Low")
                            # low_conflicts.append(conflict)

                st.sidebar.write("_________________________________________________")
                st.sidebar.subheader("\n\nConflict Grades : \n")
                st.sidebar.markdown(f"File: {proposed_name}")
                st.sidebar.markdown(
                    f"Total number of conflicts: {len(high_conflicts) + len(moderate_conflicts) + len(Name_Matchs) + len(low_conflicts)}"
                )
                st.sidebar.markdown(f"3 conditions satisfied:  {len(high_conflicts)}")
                st.sidebar.markdown(f"2 conditions satisfied:  {len(moderate_conflicts)}")
                st.sidebar.markdown(f"Name Match's Conflicts: {len(Name_Matchs)}")
                st.sidebar.markdown(f"1 condition satisfied: {len(low_conflicts)}")
                st.sidebar.write("_________________________________________________")

                document = Document()

                # Set page size to landscape  
                section = document.sections[0]  
                new_width, new_height = section.page_height, section.page_width  
                section.page_width = new_width  
                section.page_height = new_height  

                document.add_heading(
                    f"Trademark Conflict List for {proposed_name} (VERSION - 6.9) :"
                )

                document.add_heading("Dashboard :", level=2)
                # document.add_paragraph(f"\n\nTotal number of conflicts: {len(high_conflicts) + len(moderate_conflicts) + len(Name_Matchs) + len(low_conflicts)}\n- High Conflicts: {len(high_conflicts)}\n- Moderate Conflicts: {len(moderate_conflicts)}\n- Name Match's Conflicts: {len(Name_Matchs)}\n- Low Conflicts: {len(low_conflicts)}\n")

                # Updated Calculate the number of conflicts
                total_conflicts = (
                    len(high_conflicts)
                    + len(moderate_conflicts)
                    + len(Name_Matchs)
                    + len(low_conflicts)
                )

                # Create a table with 5 rows (including the header) and 2 columns
                table = document.add_table(rows=5, cols=2)

                # Set the table style and customize the borders
                table.style = "TableGrid"

                tbl = table._tbl
                tblBorders = OxmlElement("w:tblBorders")

                for border in ["top", "left", "bottom", "right", "insideH", "insideV"]:
                    border_element = OxmlElement(f"w:{border}")
                    border_element.set(qn("w:val"), "single")
                    border_element.set(
                        qn("w:sz"), "4"
                    )  # This sets the border size; you can adjust it as needed
                    border_element.set(qn("w:space"), "0")
                    border_element.set(qn("w:color"), "000000")
                    tblBorders.append(border_element)

                tbl.append(tblBorders)

                # Fill the first column with labels
                labels = [
                    "Total number of conflicts:",
                    "- 3 conditions satisfied:",
                    "- 2 conditions satisfied:",
                    "- Name Match's Conflicts:",
                    "- 1 condition satisfied:",
                ]

                # Fill the second column with the conflict numbers
                values = [
                    total_conflicts,
                    len(high_conflicts),
                    len(moderate_conflicts),
                    len(Name_Matchs), 
                    len(low_conflicts),
                ]

                p = document.add_paragraph(" ")
                p.paragraph_format.line_spacing = Pt(18)
                p.paragraph_format.space_after = Pt(0)

                document.add_heading(
                    "Trademark Definitions: ", level=2
                )
                # p = document.add_paragraph(" ")
                # p.paragraph_format.line_spacing = Pt(18)
                p = document.add_paragraph("CONDITION 1: MARK: NAME-BASED SIMILARITY (comprised of Exact Match, Semantically Equivalent, Phonetically Equivalent, Primary position match)")
                p.paragraph_format.line_spacing = Pt(18)
                p.paragraph_format.space_after = Pt(0)
                p = document.add_paragraph("CONDITION 2: CLASS: CLASS OVERLAP")
                p.paragraph_format.line_spacing = Pt(18)
                p.paragraph_format.space_after = Pt(0)
                p = document.add_paragraph("CONDITION 3: GOODS/SERVICES: OVERLAPPING GOODS/SERVICES & TARGET MARKETS")
                p.paragraph_format.line_spacing = Pt(18)
                p.paragraph_format.space_after = Pt(0)
                p = document.add_paragraph("DIRECT HIT: Direct Name hit, regardless of the class")
                p.paragraph_format.line_spacing = Pt(18)
                p.paragraph_format.space_after = Pt(0)
                p = document.add_paragraph(" ")
                p.paragraph_format.line_spacing = Pt(18)
                p.paragraph_format.space_after = Pt(0)


                # Populate the table with the labels and values
                for i in range(5):
                    table.cell(i, 0).text = labels[i]
                    table.cell(i, 1).text = str(values[i])

                    # Set the font size to 10 for both cells
                    for cell in table.row_cells(i):
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                run.font.size = Pt(10)

                if len(high_conflicts) > 0:
                    document.add_heading("Trademarks with 3 conditions satisfied:", level=2)
                    # Create a pandas DataFrame from the JSON list
                    df_high = pd.DataFrame(high_conflicts)
                    df_high = df_high.drop(
                        columns=[
                            "Trademark name",
                            "Trademark class Number",
                            "Trademark registration number",
                            "Trademark serial number",
                            "Trademark design phrase",
                            "conflict_grade",
                            "reasoning",
                        ]
                    )
                    # Create a table in the Word document
                    table_high = document.add_table(
                        df_high.shape[0] + 1, df_high.shape[1]
                    )
                    # Set a predefined table style (with borders)
                    table_high.style = (
                        "TableGrid"  # This is a built-in style that includes borders
                    )
                    # Add the column names to the table
                    for i, column_name in enumerate(df_high.columns):
                        table_high.cell(0, i).text = column_name
                    # Add the data to the table
                    for i, row in df_high.iterrows():
                        for j, value in enumerate(row):
                            cell = table_high.cell(i + 1, j)
                            cell.text = str(value)
                            for paragraph in cell.paragraphs:
                                for run in paragraph.runs:
                                    run.font.size = Pt(10)

                if len(moderate_conflicts) > 0:
                    document.add_heading("Trademarks with 2 conditions satisfied:", level=2)
                    # Create a pandas DataFrame from the JSON list
                    df_moderate = pd.DataFrame(moderate_conflicts)
                    df_moderate = df_moderate.drop(
                        columns=[
                            "Trademark name",
                            "Trademark class Number",
                            "Trademark registration number",
                            "Trademark serial number",
                            "Trademark design phrase",
                            "conflict_grade",
                            "reasoning",
                        ]
                    )
                    # Create a table in the Word document
                    table_moderate = document.add_table(
                        df_moderate.shape[0] + 1, df_moderate.shape[1]
                    )
                    # Set a predefined table style (with borders)
                    table_moderate.style = (
                        "TableGrid"  # This is a built-in style that includes borders
                    )
                    # Add the column names to the table
                    for i, column_name in enumerate(df_moderate.columns):
                        table_moderate.cell(0, i).text = column_name
                    # Add the data to the table
                    for i, row in df_moderate.iterrows():
                        for j, value in enumerate(row):
                            cell = table_moderate.cell(i + 1, j)
                            cell.text = str(value)
                            for paragraph in cell.paragraphs:
                                for run in paragraph.runs:
                                    run.font.size = Pt(10)

                if len(Name_Matchs) > 0:
                    document.add_heading(
                        "Trademarks with Name Match's Conflicts:", level=2
                    )
                    # Create a pandas DataFrame from the JSON list
                    df_Name_Matchs = pd.DataFrame(Name_Matchs)
                    df_Name_Matchs = df_Name_Matchs.drop(
                        columns=[
                            "Trademark name",
                            "Trademark class Number",
                            "Trademark registration number",
                            "Trademark serial number",
                            "Trademark design phrase",
                            "conflict_grade",
                            "reasoning",
                        ]
                    )
                    # Create a table in the Word document
                    table_Name_Matchs = document.add_table(
                        df_Name_Matchs.shape[0] + 1, df_Name_Matchs.shape[1]
                    )
                    # Set a predefined table style (with borders)
                    table_Name_Matchs.style = (
                        "TableGrid"  # This is a built-in style that includes borders
                    )
                    # Add the column names to the table
                    for i, column_name in enumerate(df_Name_Matchs.columns):
                        table_Name_Matchs.cell(0, i).text = column_name
                    # Add the data to the table
                    for i, row in df_Name_Matchs.iterrows():
                        for j, value in enumerate(row):
                            cell = table_Name_Matchs.cell(i + 1, j)
                            cell.text = str(value)
                            for paragraph in cell.paragraphs:
                                for run in paragraph.runs:
                                    run.font.size = Pt(10)

                if len(low_conflicts) > 0:
                    document.add_heading("Trademarks with 1 condition satisfied:", level=2)
                    # Create a pandas DataFrame from the JSON list
                    df_low = pd.DataFrame(low_conflicts)
                    df_low = df_low.drop(
                        columns=[
                            "Trademark name",
                            "Trademark class Number",
                            "Trademark registration number",
                            "Trademark serial number",
                            "Trademark design phrase",
                            "conflict_grade",
                            "reasoning",
                        ]
                    )
                    # Create a table in the Word document
                    table_low = document.add_table(df_low.shape[0] + 1, df_low.shape[1])
                    # Set a predefined table style (with borders)
                    table_low.style = (
                        "TableGrid"  # This is a built-in style that includes borders
                    )
                    # Add the column names to the table
                    for i, column_name in enumerate(df_low.columns):
                        table_low.cell(0, i).text = column_name
                    # Add the data to the table
                    for i, row in df_low.iterrows():
                        for j, value in enumerate(row):
                            cell = table_low.cell(i + 1, j)
                            cell.text = str(value)
                            for paragraph in cell.paragraphs:
                                for run in paragraph.runs:
                                    run.font.size = Pt(10)

                def add_conflict_paragraph(document, conflict):
                    p = document.add_paragraph(
                        f"Trademark Name : {conflict.get('Trademark name', 'N/A')}"
                    )
                    p.paragraph_format.line_spacing = Pt(18)
                    p.paragraph_format.space_after = Pt(0)
                    p = document.add_paragraph(
                        f"Trademark Status : {conflict.get('Trademark Status', 'N/A')}"
                    )
                    p.paragraph_format.line_spacing = Pt(18)
                    p.paragraph_format.space_after = Pt(0)
                    p = document.add_paragraph(
                        f"Trademark Owner : {conflict.get('Trademark Owner', 'N/A')}"
                    )
                    p.paragraph_format.line_spacing = Pt(18)
                    p.paragraph_format.space_after = Pt(0)
                    p = document.add_paragraph(
                        f"Trademark Class Number : {conflict.get('Trademark class Number', 'N/A')}"
                    )
                    p.paragraph_format.line_spacing = Pt(18)
                    p.paragraph_format.space_after = Pt(0)
                    p = document.add_paragraph(
                        f"Trademark serial number : {conflict.get('Trademark serial number', 'N/A')}"
                    )
                    p.paragraph_format.line_spacing = Pt(18)
                    p.paragraph_format.space_after = Pt(0)
                    p = document.add_paragraph(
                        f"Trademark registration number : {conflict.get('Trademark registration number', 'N/A')}"
                    )
                    p.paragraph_format.line_spacing = Pt(18)
                    p.paragraph_format.space_after = Pt(0)
                    p = document.add_paragraph(
                        f"Trademark Design phrase : {conflict.get('Trademark design phrase', 'N/A')}"
                    )
                    p.paragraph_format.line_spacing = Pt(18)
                    p.paragraph_format.space_after = Pt(0)
                    p = document.add_paragraph(" ")
                    p.paragraph_format.line_spacing = Pt(18)
                    p.paragraph_format.space_after = Pt(0)
                    p = document.add_paragraph(f"{conflict.get('reasoning','N/A')}\n")
                    p.paragraph_format.line_spacing = Pt(18)
                    p = document.add_paragraph(" ")
                    p.paragraph_format.line_spacing = Pt(18)

                if len(high_conflicts) > 0:
                    document.add_heading(
                        "Explanation: Trademarks with 3 conditions satisfied:", level=2
                    )
                    p = document.add_paragraph(" ")
                    p.paragraph_format.line_spacing = Pt(18)
                    for conflict in high_conflicts:
                        add_conflict_paragraph(document, conflict)

                if len(moderate_conflicts) > 0:
                    document.add_heading(
                        "Explanation: Trademarks with 2 conditions satisfied:", level=2
                    )
                    p = document.add_paragraph(" ")
                    p.paragraph_format.line_spacing = Pt(18)
                    for conflict in moderate_conflicts:
                        add_conflict_paragraph(document, conflict)

                if len(Name_Matchs) > 0:
                    document.add_heading(
                        "Trademarks with Name Match's Conflicts Reasoning:", level=2
                    )
                    p = document.add_paragraph(" ")
                    p.paragraph_format.line_spacing = Pt(18)
                    for conflict in Name_Matchs:
                        add_conflict_paragraph(document, conflict)

                if len(low_conflicts) > 0:
                    document.add_heading(
                        "Explanation: Trademarks with 1 condition satisfied:", level=2
                    )
                    p = document.add_paragraph(" ")
                    p.paragraph_format.line_spacing = Pt(18)
                    for conflict in low_conflicts:
                        add_conflict_paragraph(document, conflict)



                def add_conflict_paragraph_to_array(conflict):  
                    result = []  
                    result.append(f"Trademark Name : {conflict.get('Trademark name', 'N/A')}")  
                    result.append(f"Trademark Status : {conflict.get('Trademark Status', 'N/A')}")  
                    result.append(f"Trademark Owner : {conflict.get('Trademark Owner', 'N/A')}")  
                    result.append(f"Trademark Class Number : {conflict.get('Trademark class Number', 'N/A')}")  
                    result.append(f"Trademark serial number : {conflict.get('Trademark serial number', 'N/A')}")  
                    result.append(f"Trademark registration number : {conflict.get('Trademark registration number', 'N/A')}")  
                    result.append(f"Trademark Design phrase : {conflict.get('Trademark design phrase', 'N/A')}")  
                    result.append(" ")  # Blank line for spacing  
                    result.append(f"{conflict.get('reasoning', 'N/A')}\n")  
                    result.append(" ")  # Blank line for spacing  
                    return result  
                
                conflicts_array = []  
                
                if len(high_conflicts) > 0:  
                    conflicts_array.append("Explanation: Trademarks with 3 conditions satisfied:")  
                    conflicts_array.append(" ")  # Blank line for spacing  
                    for conflict in high_conflicts:  
                        conflicts_array.extend(add_conflict_paragraph_to_array(conflict))  
                
                if len(moderate_conflicts) > 0:  
                    conflicts_array.append("Explanation: Trademarks with 2 conditions satisfied:")  
                    conflicts_array.append(" ")  # Blank line for spacing  
                    for conflict in moderate_conflicts:  
                        conflicts_array.extend(add_conflict_paragraph_to_array(conflict))  
                
                if len(Name_Matchs) > 0:  
                    conflicts_array.append("Trademarks with Name Match's Conflicts Reasoning:")  
                    conflicts_array.append(" ")  # Blank line for spacing  
                    for conflict in Name_Matchs:  
                        conflicts_array.extend(add_conflict_paragraph_to_array(conflict))  
                
                if len(low_conflicts) > 0:  
                    conflicts_array.append("Explanation: Trademarks with 1 condition satisfied:")  
                    conflicts_array.append(" ")  # Blank line for spacing  
                    for conflict in low_conflicts:  
                        conflicts_array.extend(add_conflict_paragraph_to_array(conflict))  
                    

                # for i in range(70,96):
                #     progress_bar.progress(i)


                progress_bar.progress(100)

                filename = proposed_name
                doc_stream = BytesIO()
                document.save(doc_stream)
                doc_stream.seek(0)
                download_table = f'<a href="data:application/octet-stream;base64,{base64.b64encode(doc_stream.read()).decode()}" download="{filename + " Trademark Conflict Report"}.docx">Download: {filename}</a>'
                st.sidebar.markdown(download_table, unsafe_allow_html=True)
                st.success(
                    f"{proposed_name} Document conflict report successfully completed!"
                )
                
                opinion_output = run_trademark_analysis(proposed_name, proposed_class, proposed_goods_services, conflicts_array)
                # Ensure extracted_data is defined by assigning the result of extract_web_common_law
                extracted_data = extract_web_common_law(full_web_common_law, proposed_name)
                web_common_law_opinion = analyze_web_common_law(extracted_data, proposed_name)
                st.write("------------------------------------------------------------------------------------------------------------------------------")
                st.write(opinion_output)

                # Export to Word
                filename = export_trademark_opinion_to_word(opinion_output, web_common_law_opinion)
                
                # Download button
                with open(filename, "rb") as file:
                    st.sidebar.download_button(
                        label="Download Trademark Opinion",
                        data=file,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                end_time = time.time()
                elapsed_time = end_time - start_time
                elapsed_time = elapsed_time // 60
                st.write(f"Time taken: {elapsed_time} mins")

                st.write(
                    "______________________________________________________________________________________________________________________________"
                )

        progress_bar.progress(100)
        st.success("All documents processed successfully!")

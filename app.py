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
            # Handle multiple classes - check if classes field exists and is a list
            if 'classes' in conflict and isinstance(conflict['classes'], list):
                # For trademarks with multiple classes, we'll consider them relevant
                # if any of their goods/services match
                if is_similar_goods_services(conflict['goods_services'], proposed_goods_services):
                    relevant_conflicts.append(conflict)
                else:
                    excluded_count += 1
            else:
                # Single class trademark - proceed with normal check
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

Component 2: [Second Component]
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
       - "Class Match" (True/False): Whether the mark's class exactly matches the proposed trademark's class or is a coordinated class.
       - "Goods & Services Match" (True/False): Whether the mark's goods/services are similar to the proposed trademark's goods/services.
    10. Follow the specified structure exactly:
        - Section I focuses on overall hits, including One/Two Letter Analysis
        - Section II focuses only on component hits
        - In Section II, perform Crowded Field Analysis focusing on owner diversity
    11. State "None" when no results are found for a particular subsection
    12. Do NOT include recommendations in the summary
    13. Include aggressive enforcement analysis in Section III with details on any owners known for litigious behavior
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
    2. Goods & Services description
    3. Class Match (True/False): Compare the mark's class to the proposed class "{json_data.get('proposed_class', 'N/A')}" and mark True if they exactly match or are coordinated classes.
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
    """Perform Section I: Comprehensive Trademark Hit Analysis."""  
    client = get_azure_client()  
  
    system_prompt = """
    You are a trademark expert attorney specializing in trademark opinion writing.
    
    Analyze the provided trademark conflicts focusing ONLY on Section I: Comprehensive Trademark Hit Analysis.
    
    Your analysis must include:
    
    (a) Identical Marks:
    - List all identical marks or state "No identical marks found."
    - Include registration status, class, owner name, and goods/services for each mark.
    - Only include marks that match the ENTIRE proposed trademark name, not just components.
    - For marks with multiple classes (coordinated classes), include ALL classes in the analysis.
    
    (b) One Letter and Two Letter Analysis:
    - List marks with one or two-letter differences from the proposed mark.
    - Specify whether each mark has a one-letter or two-letter difference.
    - Include only marks with meaningful differences to the ENTIRE name, not components.
    - If none are found, state "None."
    
    (c) Phonetically, Semantically & Functionally Similar Analysis:
    - List marks that are phonetically, semantically, or functionally similar to the ENTIRE proposed mark.
    - If none are found, state "None."
    
    For ALL results, include:
    - Owner name and goods/services details
    - Class Match (True/False): 
        * True if the mark's class exactly matches the proposed class 
        * OR if the mark has multiple classes that include the proposed class
        * OR if the mark's class is a coordinated class with the proposed class
    - Goods & Services Match (True/False): Whether the mark's goods/services are similar to the proposed goods/services
    
    YOUR RESPONSE MUST BE IN JSON FORMAT:
    {
      "identical_marks": [
        {
          "mark": "[TRADEMARK NAME]",
          "owner": "[OWNER NAME]",
          "goods_services": "[GOODS/SERVICES]",
          "status": "[LIVE/DEAD]",
          "class": "[CLASS] or [CLASS1, CLASS2] for multiple classes",
          "class_match": true|false,
          "goods_services_match": true|false
        }
      ],
      "one_letter_marks": [
        {
          "mark": "[TRADEMARK NAME]",
          "owner": "[OWNER NAME]",
          "goods_services": "[GOODS/SERVICES]",
          "status": "[LIVE/DEAD]",
          "class": "[CLASS] or [CLASS1, CLASS2] for multiple classes",
          "difference_type": "One Letter",
          "class_match": true|false,
          "goods_services_match": true|false
        }
      ],
      "two_letter_marks": [
        {
          "mark": "[TRADEMARK NAME]",
          "owner": "[OWNER NAME]",
          "goods_services": "[GOODS/SERVICES]",
          "status": "[LIVE/DEAD]",
          "class": "[CLASS] or [CLASS1, CLASS2] for multiple classes",
          "difference_type": "Two Letter",
          "class_match": true|false,
          "goods_services_match": true|false
        }
      ],
      "similar_marks": [
        {
          "mark": "[TRADEMARK NAME]",
          "owner": "[OWNER NAME]",
          "goods_services": "[GOODS/SERVICES]",
          "status": "[LIVE/DEAD]",
          "class": "[CLASS] or [CLASS1, CLASS2] for multiple classes",
          "similarity_type": "[Phonetic|Semantic|Functional]",
          "class_match": true|false,
          "goods_services_match": true|false
        }
      ],
      "crowded_field": {
        "is_crowded": true|false,
        "percentage": [PERCENTAGE],
        "explanation": "[EXPLANATION]"
      }
    }

    IMPORTANT NOTES ABOUT CLASS MATCHING:
    1. For marks with multiple classes (coordinated classes), class_match should be True if:
       - Any of the classes exactly matches the proposed class
       - Or if any of the classes are coordinated with the proposed class
    2. Common coordinated class pairs include (but are not limited to):
       - Class 9 (electronics) and Class 42 (computer services)
       - Class 25 (clothing) and Class 35 (retail services)
       - Class 5 (pharmaceuticals) and Class 10 (medical devices)
    3. When in doubt about class coordination, err on the side of marking class_match as True
    """ 
  
    user_message = f""" 
    Proposed Trademark: {mark}
    Class: {class_number}
    Goods and Services: {goods_services}
    
    Trademark Conflicts:
    {json.dumps(relevant_conflicts, indent=2)}
    
    Analyze ONLY Section I: Comprehensive Trademark Hit Analysis.
    
    IMPORTANT REMINDERS:
    - Focus on matches to the ENTIRE trademark name, not just components
    - Include owner names and goods/services details for each mark
    - For Class Match (True/False), consider both exact matches and coordinated classes
    - For Goods & Services Match (True/False), compare the mark's goods/services to the proposed goods/services "{goods_services}"
    - Perform crowded field analysis and include percentage of overlaps
    - Pay special attention to marks with multiple classes (coordinated classes)
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


def section_two_analysis(mark, class_number, goods_services, relevant_conflicts):  
    """Perform Section II: Component Analysis."""  
    client = get_azure_client()  
  
    system_prompt = """
    You are a trademark expert attorney specializing in trademark opinion writing.
    
    Analyze the provided trademark conflicts focusing ONLY on Section II: Component Analysis.
    
    Your analysis must include:
    
    (a) Component Formative Marks:
    - Identify all components of the proposed mark (if it's a compound mark)
    - For each component, analyze marks containing that component
    - Do NOT perform One Letter and Two Letter Analysis in this section
    - Include owner names and goods/services details for each mark
    - For marks with multiple classes, include ALL classes in the analysis
    
    (b) Crowded Field Analysis:
    - Calculate the total number of compound mark hits found
    - Determine if more than `50%` of those marks each have different owners
    - If yes, set is_crowded = true and note decreased risk in explanation
    - Calculate the percentage of marks with different owners
    
    For ALL results, include:
    - Class Match (True/False): 
        * True if the mark's class exactly matches the proposed class 
        * OR if the mark has multiple classes that include the proposed class
        * OR if the mark's class is a coordinated class with the proposed class
    - Goods & Services Match (True/False): Whether the mark's goods/services are similar to the proposed goods/services
    
    YOUR RESPONSE MUST BE IN JSON FORMAT:
    {
      "components": [
        {
          "component": "[COMPONENT NAME]",
          "marks": [
            {
              "mark": "[TRADEMARK NAME]",
              "owner": "[OWNER NAME]",
              "goods_services": "[GOODS/SERVICES]",
              "status": "[LIVE/DEAD]",
              "class": "[CLASS] or [CLASS1, CLASS2] for multiple classes",
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
        "explanation": "[DETAILED EXPLANATION OF FINDINGS, INCLUDING REDUCED RISK IF is_crowded=true]"
      }
    }

    IMPORTANT NOTES ABOUT CLASS MATCHING:
    1. For marks with multiple classes (coordinated classes), class_match should be True if:
       - Any of the classes exactly matches the proposed class
       - Or if any of the classes are coordinated with the proposed class
    2. Common coordinated class pairs include (but are not limited to):
       - Class 9 (electronics) and Class 42 (computer services)
       - Class 25 (clothing) and Class 35 (retail services)
       - Class 5 (pharmaceuticals) and Class 10 (medical devices)
    3. When in doubt about class coordination, err on the side of marking class_match as True
    """  
  
    user_message = f"""
    Proposed Trademark: {mark}
    Class: {class_number}
    Goods and Services: {goods_services}
    
    Trademark Conflicts:
    {json.dumps(relevant_conflicts, indent=2)}
    
    Analyze ONLY Section II: Component Analysis.
    
    IMPORTANT REMINDERS:
    - Include exact counts and percentages for all statistics
    - For Crowded Field Analysis:
      1. Show the total number of compound mark hits
      2. Calculate percentage of marks with different owners
      3. If >50% have different owners, set is_crowded=true and mention decreased risk
    - For Class Match (True/False), consider both exact matches and coordinated classes
    - For Goods & Services Match (True/False), compare the mark's goods/services to the proposed goods/services "{goods_services}"
    - Pay special attention to marks with multiple classes (coordinated classes)
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
            "components": [],  
            "crowded_field": {  
                "total_hits": 0,
                "distinct_owner_percentage": 0,
                "is_crowded": False,
                "explanation": "Error occurred during analysis"  
            }  
        }


def section_three_analysis(mark, class_number, goods_services, section_one_results, section_two_results):
    """
    Perform Section III: Risk Assessment and Summary
    
    Args:
        mark: The proposed trademark
        class_number: The class of the proposed trademark
        goods_services: The goods and services of the proposed trademark
        section_one_results: Results from Section I
        section_two_results: Results from Section II
        
    Returns:
        A structured risk assessment and summary
    """
    client = get_azure_client()
    
    system_prompt = """
    You are a trademark expert attorney specializing in trademark opinion writing.
    
    Analyze the provided trademark conflict results and create Section III: Risk Assessment and Summary.
    
    Your analysis must include:
    
    1. Likelihood of Confusion:
    - Analyze the potential for confusion with existing marks
    - Consider the similarity of the marks and the relatedness of goods/services
    
    2. Descriptiveness:
    - Assess whether the mark is descriptive of the goods/services
    - Determine the mark's strength on the distinctiveness spectrum
    
    3. Aggressive Enforcement and Litigious Behavior:
    - Investigate whether owners of similar trademarks have a history of aggressive enforcement
    - Identify specific owners known for litigious behavior or aggressive protection of their trademarks
    - Document any patterns of enforcement behavior, including:
      * Frequent opposition filings
      * Litigation history
      * Cease-and-desist actions
    - Provide a list of such owners and their enforcement patterns
    
    4. Overall Risk Level:
    - Provide a risk assessment on this scale: HIGH, MEDIUM-HIGH, MEDIUM, MEDIUM-LOW, LOW
    - Justify the risk level based on the findings from Sections I and II
    - Focus the explanation on how the crowded field analysis contributed to risk reduction
    - Include the percentage of overlapping marks from the crowded field analysis
    
    YOUR RESPONSE MUST BE IN JSON FORMAT:
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
        "level": "[HIGH|MEDIUM-HIGH|MEDIUM|MEDIUM-LOW|LOW]",
        "explanation": "[EXPLANATION OF RISK LEVEL WITH FOCUS ON CROWDED FIELD]",
        "crowded_field_percentage": [PERCENTAGE]
      }
    }
    """
    
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
    - Focus the risk discussion on crowded field analysis
    - Include the percentage of overlapping marks from crowded field analysis
    - Do NOT include recommendations
    - If the risk is Medium-High and a crowded field is identified, reduce it to Medium-Low
    - For aggressive enforcement analysis, examine the owners of similar marks and identify any known for litigious behavior
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
                            "level": "MEDIUM",
                            "explanation": "Unable to determine precise risk level.",
                            "crowded_field_percentage": 0
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
                        "level": "MEDIUM",
                        "explanation": "Unable to determine precise risk level.",
                        "crowded_field_percentage": 0
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
                    "level": "MEDIUM",
                    "explanation": "Unable to determine precise risk level.",
                    "crowded_field_percentage": 0
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
                "level": "MEDIUM",
                "explanation": "Unable to determine precise risk level.",
                "crowded_field_percentage": 0
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

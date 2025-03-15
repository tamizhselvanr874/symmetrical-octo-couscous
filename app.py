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
            return response.choices[0].message.content
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
            return response.choices[0].message.content
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
    - PRE-FILTER: Before listing any identical trademarks, run them through the validation function.
    - Only list trademarks that are identical to each individual formative component AND cover identical or similar goods/services.
    - DO NOT include or mention any trademarks that were filtered out by the validation function.
    - Example: For "POWERHOLD," analyze "POWER" trademarks and "HOLD" trademarks separately.
    - If no identical marks pass validation for a component, state: "No identical trademarks covering similar goods/services were identified for [COMPONENT]."
    
    Step 8.c: Phonetic and Semantic Equivalents for Each Component
    - PRE-FILTER: Before listing any phonetically or semantically similar trademarks, run them through the validation function.
    - Only list trademarks that are phonetically or semantically similar to each formative component AND cover identical or similar goods/services.
    - DO NOT include or mention any trademarks that were filtered out by the validation function.
    - Example: For "POWER," phonetically similar marks might include "POWR," "POWUR," or "PAWER." For "HOLD," similar marks might include "HOALD," "HOLLD," or "HOWLD."
    - Evaluate whether these similar marks overlap in goods/services and assess the likelihood of confusion.
    
    Step 8.d: Marks with Letter Differences for Each Component
    Step 8.d.1: One-Letter Differences
    - PRE-FILTER: Before listing any trademarks with one-letter differences, run them through the validation function.
    - Only list trademarks that differ by one letter from each formative component AND cover identical or similar goods/services.
    - DO NOT include or mention any trademarks that were filtered out by the validation function.
    - Example: For "POWER," consider marks like "POWIR" or "POSER." For "HOLD," consider "HALD" or "HILD."
    - Assess the impact of these differences on consumer perception and the likelihood of confusion.
    
    Step 8.d.2: Two-Letter Differences
    - PRE-FILTER: Before listing any trademarks with two-letter differences, run them through the validation function.
    - Only list trademarks that differ by two letters from each formative component AND cover identical or similar goods/services.
    - DO NOT include or mention any trademarks that were filtered out by the validation function.
    - Example: For "POWER," consider "POWTR" or "PIWER." For "HOLD," consider "HULD" or "HILD."
    - Evaluate whether these differences create confusion in meaning or pronunciation and overlap with goods/services.
    
    Step 8.e: Component Distinctiveness Analysis
    - For each component, classify its distinctiveness as Generic, Descriptive, Suggestive, Arbitrary, or Fanciful.
    - Consider the component in relation to the specific goods/services.
    - Example: For "POWER" in electrical equipment, it would be descriptive; for food services, it would be arbitrary.
    
    Step 8.f: Component Combination Analysis
    - Analyze how the components work together to create synergy.
    - Example: "POWERHOLD" combines strength and secure grip, potentially competing with marks like "ENERGYSECURE" or "GRIPFORCE."
    - Document risks of confusion or overlap when the components are combined.
    
    Step 8.g: Overall Component Risk Assessment
    - Provide a summary table with findings on each component:
      * Component name
      * Identical marks found
      * Phonetically/semantically similar marks found
      * Marks with letter differences found
      * Distinctiveness rating
      * Component-specific risk level (Low, Low-Medium, Medium, Medium-High, High)
    - Summarize key findings about the risks associated with each individual component.
    
    IMPORTANT: We have already filtered out trademarks with unrelated goods/services. All trademarks in your input ARE relevant to the proposed trademark's goods/services. You do not need to filter them further.
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
            return response.choices[0].message.content
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
    - Integrate all findings from previous steps.
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
    
    Step 11: Summary of Findings
    - Summarize the overall trademark analysis, including:
      * Likelihood of Conflicts
      * Crowded Field Status
      * Enforcement Landscape
      * Distinctiveness Assessment
    - Provide final strategic recommendations for registration or further steps.
    - Include a note about the number of trademarks excluded from analysis due to unrelated goods/services.
    
    IMPORTANT: All irrelevant trademarks have already been filtered out through code. Focus on providing a clear risk assessment without worrying about filtering.
    """
    
    client = get_azure_client()
    
    # Construct a message that includes the pre-filtering information and previous results
    user_message = f"""
    Trademark Details:
    - Proposed Trademark: {proposed_name}
    - Classes Searched: {proposed_class}
    - Goods and Services: {proposed_goods_services}
    
    Previous Analysis Results:
    
    --- Step 7 Results ---
    {step7_results}
    
    --- Step 8 Results ---
    {step8_results}
    
    Please complete the trademark analysis by performing Steps 9-11: Final Validation Check, Overall Risk Assessment, and Summary of Findings.
    
    Note: {excluded_count} trademarks with unrelated goods/services were excluded from this analysis through pre-filtering.
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
            return response.choices[0].message.content
        else:
            return "Error: No response received from the language model."
    except Exception as e:
        return f"Error during final validation and assessment: {str(e)}"

def opinion_response(conflicts_array, proposed_name, proposed_class, proposed_goods_services):
    """
    Generate a comprehensive trademark opinion by breaking down the analysis into separate functions
    with proper validation and error handling.
    """
    try:
        # First, validate and filter conflicts array
        relevant_conflicts, excluded_count = validate_trademark_relevance(conflicts_array, proposed_goods_services)
        
        # Step 1-6: Initial compound mark analysis
        initial_results = initial_mark_analysis(conflicts_array, proposed_name, proposed_class, proposed_goods_services)
        
        # Step 7: Overall Compound Mark Analysis
        step7_results = overall_compound_mark_analysis(conflicts_array, proposed_name, proposed_class, proposed_goods_services)
        
        # Step 8: Component (Formative) Mark Analysis
        step8_results = component_formative_mark_analysis(conflicts_array, proposed_name, proposed_class, proposed_goods_services)
        
        # Steps 9-11: Final Validation, Risk Assessment, and Summary
        final_results = final_validation_and_assessment(
            conflicts_array, 
            proposed_name, 
            proposed_class, 
            proposed_goods_services, 
            step7_results, 
            step8_results, 
            excluded_count
        )
        
        # Combine all results into a comprehensive response
        comprehensive_opinion = f"""
# TRADEMARK OPINION: {proposed_name}

## Class: {proposed_class}
## Goods and Services: {proposed_goods_services}

# Initial Analysis (Steps 1-6)
{initial_results}

# Step 7: Overall Compound Mark Analysis
{step7_results}

# Step 8: Component (Formative) Mark Analysis
{step8_results}

# Final Assessment (Steps 9-11)
{final_results}

---
*Note: {excluded_count} trademarks with unrelated goods/services were excluded from this analysis.*
        """
        
        return comprehensive_opinion

    except Exception as e:
        error_message = f"An error occurred during the trademark analysis process: {str(e)}"
        print(error_message)
        return error_message

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
        opinion = opinion_response(conflicts_data, proposed_name, proposed_class, proposed_goods_services)
        return opinion
        
    except Exception as e:
        return f"Error running trademark analysis: {str(e)}"
